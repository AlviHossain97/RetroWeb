import os
import httpx
from typing import List, Dict
from app.config import get_settings

async def search_web(query: str, top_k: int = 5) -> List[Dict]:
    """Search the web using configured providers.
    Returns: List of {"title": "...", "url": "...", "snippet": "..."}
    """
    settings = get_settings()
    
    # Try SearxNG if configured
    if settings.searxng_url:
        try:
            return await _searxng_search(query, settings.searxng_url, top_k)
        except Exception as e:
            print(f"[Search] SearxNG failed: {e}")
            
    # Try Tavily if configured
    if settings.tavily_api_key:
        try:
            return await _tavily_search(query, settings.tavily_api_key, top_k)
        except Exception as e:
            print(f"[Search] Tavily failed: {e}")
            
    # Fallback to duckduckgo lite html search
    print("[Search] Falling back to duckduckgo lite...")
    return await _ddg_lite_search(query, top_k)

async def _tavily_search(query: str, api_key: str, limit: int) -> List[Dict]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post("https://api.tavily.com/search", json={
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": limit,
            "include_answer": False,
            "include_raw_content": False
        })
        res.raise_for_status()
        data = res.json()
        results = []
        for d in data.get("results", []):
            results.append({
                "title": d.get("title", ""),
                "url": d.get("url", ""),
                "snippet": d.get("content", "")
            })
        return results

async def _searxng_search(query: str, url: str, limit: int) -> List[Dict]:
    endpoint = f"{url.rstrip('/')}/search"
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(endpoint, params={"q": query, "format": "json"})
        res.raise_for_status()
        data = res.json()
        results = []
        for r in data.get("results", [])[:limit]:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", "")
            })
        return results

async def _ddg_lite_search(query: str, limit: int) -> List[Dict]:
    # Very basic DDG HTML parsing to get results without relying on unmaintained APIs
    from bs4 import BeautifulSoup
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
        res = await client.post("https://lite.duckduckgo.com/lite/", data={"q": query})
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        
        results = []
        for row in soup.find_all("tr"):
            link_tag = row.find("a", class_="result-url")
            if link_tag:
                url = link_tag.get("href", "")
                title_tag = row.find_previous_sibling("tr")
                if title_tag:
                    title_a = title_tag.find("a", class_="result-snippet")
                    title = title_a.text.strip() if title_a else url
                    snippet_div = row.find("td", class_="result-snippet")
                    snippet = snippet_div.text.strip() if snippet_div else ""
                    
                    # Deduplicate or clean
                    results.append({"title": title, "url": url, "snippet": snippet})
                    if len(results) >= limit:
                        break
        return results
