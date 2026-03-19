"""Query router — decides whether a user prompt needs web grounding."""

import json
import httpx
from pydantic import BaseModel
from app.config import get_settings


class RoutingResult(BaseModel):
    needs_search: bool
    search_query: str


async def route_query(
    user_prompt: str,
    chat_history: list,
    mode: str = "auto",
) -> RoutingResult:
    """Decide if a query needs web search, and formulate the best search query.

    Args:
        user_prompt: The user's latest message.
        chat_history: Recent conversation turns.
        mode: One of "auto", "always", "never".
    """
    settings = get_settings()

    if mode == "always":
        print("[GROUND] router: mode=always → force search")
        return RoutingResult(needs_search=True, search_query=user_prompt)

    if mode == "never":
        return RoutingResult(needs_search=False, search_query="")

    # ── Auto mode: use LLM classifier with keyword fallback ──
    lower = user_prompt.lower().strip()

    # Skip trivially casual messages
    if lower in {"hi", "hello", "hey", "thanks", "ok", "bye", "cool", "yes", "no", "lol"}:
        return RoutingResult(needs_search=False, search_query="")

    # Try LLM-based classification
    prompt = (
        "You are a query routing engine. Decide if the user's query needs a web "
        "search for an accurate, factual answer.\n\n"
        "Search the web for: current events, factual lookups, product specs, "
        "releases, prices, comparisons, game data, versioning, compatibility.\n"
        "DO NOT search for: casual chat, creative writing, summarizing user text, "
        "generic coding help.\n\n"
        f'User Query: "{user_prompt}"\n\n'
        "Return ONLY a valid JSON object:\n"
        '{"needs_search": true/false, "search_query": "concise 3-6 word query or empty"}\n'
    )

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0.0},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("response", "{}")
            result = json.loads(raw)
            needs = bool(result.get("needs_search", False))
            query = str(result.get("search_query", ""))
            print(f"[GROUND] router LLM → needs_search={needs}, query='{query}'")
            return RoutingResult(needs_search=needs, search_query=query)
    except Exception as e:
        print(f"[GROUND] router LLM failed ({e}), falling back to heuristics")

    # ── Keyword heuristic fallback ──
    SEARCH_KEYWORDS = [
        "latest", "best", "current", "today", "recent", "news",
        "how much", "who is", "when did", "price", "release date",
        "comparison", "version", "starter", "what is", "does",
        "compare", "review", "recommend",
    ]
    if any(k in lower for k in SEARCH_KEYWORDS) or "?" in lower:
        print(f"[GROUND] router heuristic → search triggered")
        return RoutingResult(needs_search=True, search_query=user_prompt)

    return RoutingResult(needs_search=False, search_query="")
