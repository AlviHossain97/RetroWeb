"""Search service — queries web search providers (Tavily → SearxNG → DDG)."""

import httpx
from typing import List, Dict
from app.config import get_settings


async def search_web(query: str, top_k: int = 5) -> List[Dict]:
    """Search the web using the best available provider.

    Provider priority:
        1. Tavily (if TAVILY_API_KEY is set)
        2. SearxNG (if SEARXNG_URL is set)
        3. DuckDuckGo lite HTML fallback

    Returns list of {"title", "url", "snippet"}.
    """
    settings = get_settings()

    # 1. Tavily — most reliable, gives clean snippets
    if settings.tavily_api_key:
        try:
            results = await _tavily_search(query, settings.tavily_api_key, top_k)
            if results:
                print(f"[GROUND] search: Tavily returned {len(results)} results")
                return results
        except Exception as e:
            print(f"[GROUND] search: Tavily failed: {e}")

    # 2. SearxNG
    if settings.searxng_url:
        try:
            results = await _searxng_search(query, settings.searxng_url, top_k)
            if results:
                print(f"[GROUND] search: SearxNG returned {len(results)} results")
                return results
        except Exception as e:
            print(f"[GROUND] search: SearxNG failed: {e}")

    # 3. DuckDuckGo lite
    try:
        results = await _ddg_lite_search(query, top_k)
        if results:
            print(f"[GROUND] search: DDG returned {len(results)} results")
            return results
    except Exception as e:
        print(f"[GROUND] search: DDG failed: {e}")

    return []


async def _tavily_search(query: str, api_key: str, limit: int) -> List[Dict]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": limit,
                "include_answer": False,
                "include_raw_content": False,
            },
        )
        res.raise_for_status()
        data = res.json()
        return [
            {
                "title": d.get("title", ""),
                "url": d.get("url", ""),
                "snippet": d.get("content", ""),
            }
            for d in data.get("results", [])
        ]


async def _searxng_search(query: str, url: str, limit: int) -> List[Dict]:
    endpoint = f"{url.rstrip('/')}/search"
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(endpoint, params={"q": query, "format": "json"})
        res.raise_for_status()
        data = res.json()
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),
            }
            for r in data.get("results", [])[:limit]
        ]


async def _ddg_lite_search(query: str, limit: int) -> List[Dict]:
    from bs4 import BeautifulSoup

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120"
        )
    }
    async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
        res = await client.post(
            "https://lite.duckduckgo.com/lite/", data={"q": query}
        )
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        results: list[dict] = []
        # DDG lite uses table rows for results
        for a_tag in soup.find_all("a", class_="result-link"):
            url = a_tag.get("href", "")
            title = a_tag.get_text(strip=True)
            # Find the next snippet
            snippet_td = a_tag.find_parent("tr")
            snippet = ""
            if snippet_td:
                next_tr = snippet_td.find_next_sibling("tr")
                if next_tr:
                    snippet_cell = next_tr.find("td", class_="result-snippet")
                    if snippet_cell:
                        snippet = snippet_cell.get_text(strip=True)
            results.append({"title": title, "url": url, "snippet": snippet})
            if len(results) >= limit:
                break

        return results
