"""
Image generation service — Mistral prompt refinement + ImageRouter.

Pipeline:
  User prompt → Mistral refines → validate → ImageRouter generates image → return base64
"""

import json
import time
import httpx

from app.config import get_settings

MISTRAL_MODEL = "mistralai/mistral-large-3-675b-instruct-2512"
NVIDIA_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"
IMAGEROUTER_ENDPOINT = "https://ir-api.myqa.cc/v1/openai/images/generations"

MAX_PROMPT_LENGTH = 1000


# ── Mistral prompt refinement ──

REFINE_SYSTEM = """You are an expert image-prompt writer for AI image generation models.

Given a user's request (and optionally a game title, system, or style preset), produce a concise,
visually descriptive image prompt optimized for generation quality.

Rules:
- Preserve the user's core intent
- Keep it under 200 words
- Be visually specific: mention composition, lighting, color palette, mood
- If a style preset is given, lean into that aesthetic
- If a game title is given, incorporate it naturally
- Do NOT include negative prompts, technical parameters, or safety disclaimers
- Output valid JSON only

Output format:
{"final_prompt": "...", "style_preset": "...", "title": "..."}"""


async def refine_prompt(
    user_prompt: str,
    game_context: str | None = None,
    style_preset: str | None = None,
) -> dict:
    """Call Mistral via NVIDIA API to refine a user prompt into a strong image brief."""
    settings = get_settings()

    if not settings.nvidia_api_key:
        print("[IMAGE] NVIDIA API key missing — skipping refinement")
        return _fallback_refinement(user_prompt, style_preset)

    parts = [f"User request: {user_prompt}"]
    if game_context:
        parts.append(f"Game context: {game_context}")
    if style_preset:
        parts.append(f"Style preset: {style_preset}")
    user_msg = "\n".join(parts)

    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                NVIDIA_ENDPOINT,
                headers={"Authorization": f"Bearer {settings.nvidia_api_key}"},
                json={
                    "model": MISTRAL_MODEL,
                    "messages": [
                        {"role": "system", "content": REFINE_SYSTEM},
                        {"role": "user", "content": user_msg},
                    ],
                    "max_tokens": 512,
                    "temperature": 0.7,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            raw = data["choices"][0]["message"]["content"].strip()
        dt = time.time() - t0
        print(f"[IMAGE] Mistral refinement completed in {dt:.1f}s, output length={len(raw)}")

        return _parse_refinement(raw, user_prompt, style_preset)

    except Exception as e:
        print(f"[IMAGE] Mistral refinement failed: {e}")
        return _fallback_refinement(user_prompt, style_preset)


def _parse_refinement(raw: str, original: str, style_preset: str | None) -> dict:
    """Parse Mistral's JSON output, with fallback."""
    # Strip markdown code fences if present
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        print(f"[IMAGE] Refinement JSON parse failed, falling back")
        return _fallback_refinement(original, style_preset)

    final_prompt = obj.get("final_prompt", "")
    if not isinstance(final_prompt, str) or len(final_prompt.strip()) < 5:
        return _fallback_refinement(original, style_preset)

    return {
        "final_prompt": final_prompt.strip()[:MAX_PROMPT_LENGTH],
        "style_preset": str(obj.get("style_preset", style_preset or ""))[:50],
        "title": str(obj.get("title", ""))[:100],
    }


def _fallback_refinement(original: str, style_preset: str | None) -> dict:
    """Lightweight fallback when Mistral refinement is unavailable."""
    style_suffix = f", {style_preset} style" if style_preset else ""
    return {
        "final_prompt": f"{original.strip()}{style_suffix}, high quality, detailed, vivid colors"[:MAX_PROMPT_LENGTH],
        "style_preset": style_preset or "",
        "title": original.strip()[:60],
    }


# ── ImageRouter image generation ──

async def generate_image(refined_prompt: str) -> dict:
    """Call ImageRouter to generate an image from a refined prompt.

    Returns: {"image_base64": str, "mime_type": str} or raises.
    """
    settings = get_settings()
    api_key = settings.imagerouter_api_key
    model = settings.imagerouter_image_model

    if not api_key:
        raise ValueError("IMAGEROUTER_API_KEY not configured")

    # Free-tier models cap at 512x512; paid versions support larger sizes.
    FREE_MODEL_MAX_SIZE = {
        "google/nano-banana-2:free": "512x512",
    }
    size = FREE_MODEL_MAX_SIZE.get(model, "1024x1024")
    if model in FREE_MODEL_MAX_SIZE:
        print(f"[IMAGE] Free model {model} — forcing size={size}")

    payload = {
        "model": model,
        "prompt": refined_prompt,
        "n": 1,
        "size": size,
        "response_format": "b64_json",
    }

    print(f"[IMAGE] Calling ImageRouter: endpoint={IMAGEROUTER_ENDPOINT}, model={model}, "
          f"size={payload.get('size')}, format={payload.get('response_format')}, "
          f"auth={'present' if api_key else 'MISSING'}")

    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                IMAGEROUTER_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        dt = time.time() - t0
        print(f"[IMAGE] ImageRouter generation completed in {dt:.1f}s (model={model})")

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        detail = e.response.text[:200] if e.response.text else ""
        print(f"[IMAGE] ImageRouter API error: status={status}, body={detail}")
        if status == 404:
            raise ValueError(f"Image provider 404: wrong endpoint, model, or request format (model={model})")
        if "size" in detail.lower() and ("only supports" in detail.lower() or "not supported" in detail.lower()):
            raise ValueError(f"Image size not supported by {model}. Try a different model or size.")
        raise ValueError(f"Image provider returned {status}: {detail}")
    except httpx.TimeoutException:
        print("[IMAGE] ImageRouter request timed out")
        raise ValueError("Image generation timed out")
    except Exception as e:
        print(f"[IMAGE] ImageRouter request failed: {e}")
        raise ValueError("Image generation request failed")

    # Parse OpenAI-compatible response
    images = data.get("data", [])
    if not images:
        print("[IMAGE] ImageRouter returned no image data")
        raise ValueError("The image provider returned no image")

    entry = images[0]
    b64 = entry.get("b64_json", "")
    if not b64:
        print("[IMAGE] ImageRouter response had no b64_json in first entry")
        raise ValueError("The image provider returned no image")

    print(f"[IMAGE] Got image: base64_length={len(b64)}")
    return {
        "image_base64": b64,
        "mime_type": "image/png",
    }


# ── Full pipeline ──

async def generate_game_art(
    user_prompt: str,
    game_context: str | None = None,
    style_preset: str | None = None,
) -> dict:
    """End-to-end pipeline: refine prompt → generate image → return result."""
    settings = get_settings()
    model = settings.imagerouter_image_model
    print(f"[IMAGE] Pipeline start: prompt={user_prompt!r}, context={game_context!r}, style={style_preset!r}, model={model}")

    # Step 1: Refine
    refined = await refine_prompt(user_prompt, game_context, style_preset)
    print(f"[IMAGE] Refined prompt ({len(refined['final_prompt'])} chars): {refined['final_prompt'][:80]}...")

    # Step 2: Generate via ImageRouter
    image_data = await generate_image(refined["final_prompt"])

    return {
        "imageBase64": image_data["image_base64"],
        "mimeType": image_data["mime_type"],
        "finalPrompt": refined["final_prompt"],
        "title": refined.get("title", ""),
        "stylePreset": refined.get("style_preset", ""),
    }
