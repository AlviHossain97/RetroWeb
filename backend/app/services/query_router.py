import re
import json
import httpx
from pydantic import BaseModel
from typing import Tuple
from app.config import get_settings

class RoutingResult(BaseModel):
    needs_search: bool
    search_query: str

async def route_query(user_prompt: str, chat_history: list) -> RoutingResult:
    """Decide if a query needs web search, and formulate the best search query."""
    settings = get_settings()
    mode = settings.web_search_mode.lower()
    
    if mode == "always":
        return RoutingResult(needs_search=True, search_query=user_prompt)
    if mode == "never":
        return RoutingResult(needs_search=False, search_query="")

    # Try fast heuristics for obvious exclusions
    lower_prompt = user_prompt.lower().strip()
    if lower_prompt in ["hi", "hello", "hey", "thanks", "ok", "bye", "cool"]:
        return RoutingResult(needs_search=False, search_query="")

    # Ask the LLM to classify and generate the search query
    prompt = f"""You are a query routing engine. Your job is to decide if the user's latest query needs web searching to provide an accurate, factual answer.
Search the web for: Current events, factual lookups, product specs, releases, "latest", prices, comparisons.
DO NOT search the web for: Casual chat, creative writing, summarizing provided text, generic programming help that doesn't rely on current versions.

User Query: "{user_prompt}"

Return ONLY a valid JSON object with:
"needs_search": true if web search is needed, false otherwise.
"search_query": the optimal concise search engine query (3-6 words) if search is needed, otherwise empty string.

Example output:
{{"needs_search": true, "search_query": "latest ollama version release notes"}}
"""
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0.0}
                }
            )
            resp.raise_for_status()
            data = resp.json()
            result = json.loads(data.get("response", "{}"))
            return RoutingResult(
                needs_search=bool(result.get("needs_search", False)),
                search_query=str(result.get("search_query", ""))
            )
    except Exception as e:
        print(f"[Router] Fast-routing failed: {e}. Falling back to keyword heuristics.")
        
    # Fallback to heuristics if LLM fails
    keywords = ["latest", "best", "current", "today", "recent", "news", "how much", "who is", "when did", "price", "release date", "comparison"]
    if any(k in lower_prompt for k in keywords) or "?" in lower_prompt:
        return RoutingResult(needs_search=True, search_query=user_prompt)
        
    return RoutingResult(needs_search=False, search_query="")
