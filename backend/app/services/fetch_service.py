import asyncio
import httpx
from typing import List, Dict
from app.services.extractor import extract_main_text

async def fetch_pages(urls: List[str], max_concurrent: int = 3, timeout: int = 10) -> Dict[str, str]:
    """Fetch multiple URLs and extract readable main text.
    Returns: Mapping of URL -> Extracted Text
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    results = {}
    
    async def fetch(url: str):
        # Basic SSRF prevention: filter internal IPs
        if any(ip in url for ip in ['localhost', '127.0.0.1', '192.168.', '10.', '172.16.', 'file://']):
            return url, ""
            
        async with semaphore:
            headers = {"User-Agent": "Mozilla/5.0 (PiStation Bot; local AI context builder)"}
            try:
                # Follow redirects, strict timeout
                async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=timeout) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    
                    # Ensure it's HTML/text
                    ctype = resp.headers.get("Content-Type", "").lower()
                    if "text/html" not in ctype and "text/plain" not in ctype:
                        return url, ""
                        
                    content = extract_main_text(resp.text)
                    return url, content
                    
            except Exception as e:
                print(f"[Fetch] Failed to fetch {url}: {e}")
                return url, ""

    tasks = [fetch(u) for u in urls]
    for task_res in await asyncio.gather(*tasks):
        url, text = task_res
        if text.strip():
            results[url] = text
            
    return results
