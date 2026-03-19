"""Fetch service — downloads and extracts readable content from URLs."""

import asyncio
import httpx
from typing import Dict, List
from app.services.extractor import extract_main_text

# Block private/internal networks (SSRF prevention)
_BLOCKED = [
    "localhost", "127.0.0.1", "0.0.0.0",
    "192.168.", "10.", "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
    "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
    "file://", "ftp://",
]


def _is_blocked(url: str) -> bool:
    lower = url.lower()
    return any(b in lower for b in _BLOCKED)


async def fetch_pages(
    urls: List[str],
    max_concurrent: int = 3,
    timeout: int = 10,
) -> Dict[str, str]:
    """Fetch URLs concurrently and return {url: extracted_text}."""
    semaphore = asyncio.Semaphore(max_concurrent)
    results: Dict[str, str] = {}

    async def _fetch_one(url: str) -> tuple[str, str]:
        if _is_blocked(url):
            print(f"[GROUND] fetch: blocked private URL {url}")
            return url, ""

        async with semaphore:
            headers = {
                "User-Agent": "Mozilla/5.0 (PiStation Bot; AI context builder)"
            }
            try:
                async with httpx.AsyncClient(
                    headers=headers, follow_redirects=True, timeout=timeout
                ) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()

                    ctype = resp.headers.get("Content-Type", "").lower()
                    if "text/html" not in ctype and "text/plain" not in ctype:
                        return url, ""

                    text = extract_main_text(resp.text)
                    return url, text

            except Exception as e:
                print(f"[GROUND] fetch failed for {url}: {e}")
                return url, ""

    tasks = [_fetch_one(u) for u in urls]
    for coro in asyncio.as_completed(tasks):
        url, text = await coro
        if text.strip():
            results[url] = text

    return results
