"""Web grounding orchestrator — search, fetch, build evidence bundle."""

import asyncio
import time
from typing import Dict, Any, List
from app.config import get_settings
from app.services.query_router import route_query
from app.services.search_service import search_web
from app.services.fetch_service import fetch_pages

# Simple in-memory cache for search results to speed up repeated identical queries
_GROUNDING_CACHE: Dict[str, Dict[str, Any]] = {}

def _get_cached(query: str, ttl_seconds: int = 300) -> Dict | None:
    if query in _GROUNDING_CACHE:
        entry = _GROUNDING_CACHE[query]
        if time.time() - entry["time"] < ttl_seconds:
            return entry["data"]
        del _GROUNDING_CACHE[query]
    return None

def _set_cached(query: str, data: Dict):
    _GROUNDING_CACHE[query] = {"time": time.time(), "data": data}


async def prepare_grounded_context(
    question: str,
    history: list,
    mode_override: str | None = None,
) -> Dict[str, Any]:
    """Decides if search is needed, fetches data, builds grounded prompt.

    Args:
        question: The user's query text.
        history: Recent chat history (list of {role, content}).
        mode_override: If provided, overrides the server-side web_search_mode
                       setting. Accepted values: "auto", "always", "never".
    """
    settings = get_settings()
    mode = (mode_override or settings.web_search_mode).lower()
    print(f"[GROUND] mode={mode}")

    # ── never ──
    if mode == "never":
        print("[GROUND] mode=never, skipping grounding")
        return {"grounded": False, "sources": [], "system_append": "", "mode": mode}

    # ── auto or always — run query router ──
    route_result = await route_query(question, history, mode)
    if not route_result.needs_search:
        print("[GROUND] router says no search needed")
        return {"grounded": False, "sources": [], "system_append": "", "mode": mode}

    search_query = route_result.search_query or question
    
    # ── Check Cache ──
    cached = _get_cached(search_query)
    if cached:
        print(f"[GROUND] cache hit for '{search_query}'")
        return cached

    print(f"[GROUND] searching: '{search_query}'")

    # ── Search ──
    try:
        results = await search_web(search_query, top_k=settings.search_top_k)
        print(f"[GROUND] got {len(results)} search results")
    except Exception as e:
        print(f"[GROUND] search failed: {e}")
        if mode == "always":
            return {
                "grounded": False,
                "sources": [],
                "system_append": "",
                "mode": mode,
                "error": "Web search failed. Cannot provide a verified answer.",
            }
        return {"grounded": False, "sources": [], "system_append": "", "mode": mode}

    if not results:
        print("[GROUND] no results returned")
        if mode == "always":
            return {
                "grounded": False,
                "sources": [],
                "system_append": "",
                "mode": mode,
                "error": "Web search returned no results. Cannot provide a verified answer.",
            }
        return {"grounded": False, "sources": [], "system_append": "", "mode": mode}

    # ── Fetch top pages ──
    urls_to_fetch = [r["url"] for r in results[: settings.fetch_top_k]]
    print(f"[GROUND] fetching {len(urls_to_fetch)} pages …")
    fetched_data = await fetch_pages(urls_to_fetch, timeout=settings.request_timeout_seconds)
    print(f"[GROUND] fetched {len(fetched_data)}/{len(urls_to_fetch)} pages successfully")

    # ── Build grounding context ──
    sources_ui: list[dict] = []
    context_blocks: list[str] = []

    for idx, r in enumerate(results):
        url = r["url"]
        content = fetched_data.get(url, r.get("snippet", ""))
        if len(content) < 50:
            content = r.get("snippet", "")
            
        # Truncate content to keep prompt size small and fast
        if len(content) > 2000:
            content = content[:2000] + "... [truncated]"
            
        context_blocks.append(
            f"--- Source [{idx + 1}] ---\n"
            f"Title: {r['title']}\n"
            f"Content: {content}\n"
        )
        sources_ui.append({
            "id": idx + 1,
            "title": r["title"],
            "url": url,
            "snippet": r.get("snippet", ""),
        })

    all_context = "\n".join(context_blocks)

    system_append = (
        "\n=================\n"
        "WEB SEARCH EVIDENCE:\n"
        f"{all_context}"
        "=================\n"
        "INSTRUCTIONS FOR ANSWERING:\n"
        "1. You are a polished, consumer-facing assistant. Write clean, natural chat responses.\n"
        "2. Answer directly and concisely first, then briefly explain. Do not use robotic filler like 'Based on the provided data...'\n"
        "3. DO NOT use markdown formatting like bold (**text**) or bullet lists unless explicitly asked for them. Use plain conversational prose.\n"
        "4. Rely ONLY on the provided evidence for factual claims. Do not invent facts.\n"
        "5. Use minimal inline citations like [1] or [2] to reference the source number. Put the citation at the end of the claim.\n"
        "6. DO NOT include a 'Sources:' list at the end of your text, the UI handles source display automatically.\n"
        "7. If the evidence is insufficient, explicitly state that you couldn't find a verified answer.\n"
    )

    print(f"[GROUND] success — {len(sources_ui)} sources, "
          f"{sum(len(b) for b in context_blocks)} chars of evidence")

    final_result = {
        "grounded": True,
        "sources": sources_ui,
        "system_append": system_append,
        "mode": mode,
    }
    
    _set_cached(search_query, final_result)
    return final_result
