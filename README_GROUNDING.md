# PiStation Web Grounding Documentation

The PiStation AI assistant now supports verifiable web-grounded answering using a multi-provider search-fetch-extract pipeline.

## How it Works
1. **Query Routing**: The system classifies if the user's query requires current or factual knowledge.
2. **Search**: It queries Tavily (primary), falling back to SearxNG or DuckDuckGo.
3. **Fetch & Extract**: The top 3 URLs are asynchronously fetched. HTML is stripped of layout boilerplate (nav, ads, footer) using BeautifulSoup to distill core article text.
4. **Evidence Injection**: The extracted text is injected into the LLM's system prompt as verified evidence.
5. **Grounded Answer**: The LLM is strictly instructed (via a specialized prompt) to answer **ONLY** from the provided evidence and cite sources with `[n]`.

## Modes
- **🌐 Web: Never**: The assistant uses its internal knowledge only. No search is performed.
- **🌐 Web: Auto**: The router asks the local model if grounding is needed. Recommended for general chat.
- **🌐 Web: Always**: **STRICT MODE**. Grounding is mandatory.
  - If the search fails or returns zero results, the assistant will show an error: *"⚠️ Web verification is currently unavailable..."*
  - This prevents hallucinations on sensitive factual queries.

## Configuration
Edit `backend/app/config.py` or set environment variables:
- `WEB_SEARCH_MODE`: `auto`, `always`, or `never` (server default).
- `TAVILY_API_KEY`: Required for high-quality structured snippets.
- `SEARXNG_URL`: Optional self-hosted search fallback.
- `SEARCH_TOP_K`: Number of results to consider (default: 5).
- `FETCH_TOP_K`: Number of pages to deep-scrape (default: 3).

## API Integration
The frontend calls `POST /api/pistation/ai/ground` which returns:
```json
{
  "grounded": true,
  "sources": [
    { "id": 1, "title": "...", "url": "...", "snippet": "..." }
  ],
  "system_append": "... evidence text and citation instructions ...",
  "mode": "always"
}
```

## Local Testing
You can test the pipeline directly using the script:
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/backend
python3 backend/tests/test_grounding.py
```
*(Tests include search connectivity, fetch extraction, and prompt generation)*.
