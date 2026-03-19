import asyncio
from typing import Dict, Any, List
from app.config import get_settings
from app.services.query_router import route_query
from app.services.search_service import search_web
from app.services.fetch_service import fetch_pages

async def prepare_grounded_context(question: str, history: list) -> Dict[str, Any]:
    """Decides if search is needed, fetches data, builds grounded prompt."""
    settings = get_settings()
    
    # 1. Route query
    route_result = await route_query(question, history)
    if not route_result.needs_search:
        return {"grounded": False, "sources": [], "system_append": ""}
        
    search_query = route_result.search_query or question
    print(f"[Grounding] Search triggered. Query: '{search_query}'")
    
    # 2. Search web
    try:
        results = await search_web(search_query, top_k=settings.search_top_k)
    except Exception as e:
        print(f"[Grounding] Search failed completely: {e}")
        return {"grounded": False, "sources": [], "system_append": "Note: Web search failed, answer from memory."}
        
    if not results:
        return {"grounded": False, "sources": [], "system_append": "Note: Attempted web search but found no relevant results. Answer from memory."}
        
    # 3. Fetch top pages
    urls_to_fetch = [r["url"] for r in results[:settings.fetch_top_k]]
    fetched_data = await fetch_pages(urls_to_fetch, timeout=settings.request_timeout_seconds)
    
    # 4. Build grounding info
    sources_ui = []
    context_blocks = []
    
    for idx, r in enumerate(results):
        url = r["url"]
        content = fetched_data.get(url, r.get("snippet", "No extra content extracted."))
        
        # Strip super short content
        if len(content) < 50: 
            content = r.get("snippet", "")
            
        context_blocks.append(f"--- Source [{idx + 1}] ---\nTitle: {r['title']}\nURL: {url}\nContent: {content}\n")
        sources_ui.append({"id": idx + 1, "title": r["title"], "url": url, "snippet": r["snippet"]})
        
    all_context = "\n".join(context_blocks)
    
    # Build strict prompt appendage
    system_append = f"""
=================
WEB SEARCH CONTEXT:
The user's query prompted an automatic web search. Below are the top verified sources.

{all_context}
=================
INSTRUCTIONS FOR ANSWERING:
1. You are now a source-grounded assistant. You MUST rely ONLY on the provided web evidence for factual claims.
2. If the sources are incomplete, conflicting, or do not contain the answer, explicitly state that the evidence is insufficient.
3. DO NOT invent facts or use unstated background knowledge for factual topics.
4. Cite the claims inline using numbered references like [1], [2].
"""
    
    return {
        "grounded": True,
        "sources": sources_ui,
        "system_append": system_append
    }
