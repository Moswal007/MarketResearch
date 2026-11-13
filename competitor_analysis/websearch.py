"""Shared no-API-key web search + fetch helpers, used by every platform source
under sources/. Nothing platform-specific lives here.
"""

import re
from urllib.parse import parse_qs, unquote, urlparse

import httpx

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

RESULT_LINK_RE = re.compile(r'class="result__a"[^>]*href="([^"]+)"')

BLOCK_MARKERS = (
    "anomaly-modal", "unusual traffic", "captcha", "verify you are human",
    "api-services-support", "enablejs", "recaptcha", "/sorry/index",
    "bm-verify", "http-equiv=\"refresh\"",
)


class SearchBlocked(Exception):
    """The site or search engine refused the query outright (bot challenge, JS
    wall, rate limit) - distinct from "the query ran and found nothing," since a
    market-research tool must never report a block as an empty market."""


def looks_like_bot_block(status_code: int, body: str) -> bool:
    if status_code in (202, 403, 429, 503):
        return True
    if len(body) < 400:  # a real result/profile page is far longer than a stub
        return True
    lowered = body.lower()
    return any(marker in lowered for marker in BLOCK_MARKERS)


def extract_ddg_result_urls(page_html: str) -> list[str]:
    urls = []
    for href in RESULT_LINK_RE.findall(page_html):
        href = href.replace("&amp;", "&")
        if href.startswith("//duckduckgo.com/l/"):
            target = parse_qs(urlparse("https:" + href).query).get("uddg", [None])[0]
            if target:
                urls.append(unquote(target))
        elif href.startswith("http"):
            urls.append(href)
    return urls


async def duckduckgo_search(client: httpx.AsyncClient, query: str, max_results: int = 8) -> list[str]:
    """Raw result URLs for a query via DuckDuckGo's HTML frontend - used by
    platforms (Facebook, Instagram) that have no public search of their own.
    Raises SearchBlocked if DuckDuckGo serves a bot challenge."""
    resp = await client.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        headers=BROWSER_HEADERS,
        timeout=15,
        follow_redirects=True,
    )
    if looks_like_bot_block(resp.status_code, resp.text):
        raise SearchBlocked(f"DuckDuckGo blocked the query: {query!r}")
    resp.raise_for_status()
    return extract_ddg_result_urls(resp.text)[:max_results]


async def fetch(client: httpx.AsyncClient, url: str, params: dict | None = None) -> str:
    """Fetches a URL directly (a platform's own search or a profile/product page).
    Raises SearchBlocked if the response looks like a bot challenge or JS-only
    shell; raises the underlying httpx error for a plain network/HTTP failure."""
    resp = await client.get(url, params=params, headers=BROWSER_HEADERS, timeout=15, follow_redirects=True)
    if looks_like_bot_block(resp.status_code, resp.text):
        raise SearchBlocked(f"{url} returned a bot challenge or a JS-only page")
    resp.raise_for_status()
    return resp.text
