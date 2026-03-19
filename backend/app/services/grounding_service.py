"""Web grounding orchestrator — search, fetch, build evidence bundle."""

import asyncio
from typing import Dict, Any, List
from app.config import get_settings
from app.services.query_router import route_query
from app.services.search_service import search_web
from app.services.fetch_service import fetch_pages


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
        context_blocks.append(
            f"--- Source [{idx + 1}] ---\n"
            f"Title: {r['title']}\n"
            f"URL: {url}\n"
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
        "WEB SEARCH CONTEXT:\n"
        "The user's query prompted an automatic web search. "
        "Below are the top verified sources.\n\n"
        f"{all_context}"
        "=================\n"
        "INSTRUCTIONS FOR ANSWERING:\n"
        "1. You are now a source-grounded assistant. You MUST rely ONLY on the "
        "provided web evidence for factual claims.\n"
        "2. If the sources are incomplete, conflicting, or do not contain the "
        "answer, explicitly state that the evidence is insufficient.\n"
        "3. DO NOT invent facts or use unstated background knowledge.\n"
        "4. Cite claims inline using numbered references like [1], [2].\n"
        "5. End your answer with a 'Sources:' section listing each reference.\n"
    )

    print(f"[GROUND] success — {len(sources_ui)} sources, "
          f"{sum(len(b) for b in context_blocks)} chars of evidence")

    return {
        "grounded": True,
        "sources": sources_ui,
        "system_append": system_append,
        "mode": mode,
    }
