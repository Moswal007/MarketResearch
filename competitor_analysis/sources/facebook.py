"""No public search of its own for logged-out users, so pages are found via
DuckDuckGo (site:facebook.com) and then read directly for a name and, where
present, a rating. See PRD: Data Sources & Collection Method."""

import html
import re
from urllib.parse import unquote, urlparse

import httpx

from ..models import CompetitorListing
from ..websearch import SearchBlocked, duckduckgo_search, fetch
from .base import PlatformSource

PAGE_URL_RE = re.compile(
    r"^https?://(?:www\.|m\.|mbasic\.)?facebook\.com/"
    r"(?!marketplace|groups|watch|events|help|login|policy|legal|ads|business|hashtag|search|sharer|plugins|photo)"
    r"(profile\.php\?id=\d+|pages/[^/?#]+/\d+|[A-Za-z0-9.\-_]+)/?(?:[?#].*)?$"
)
NAME_RE = re.compile(r'<meta property="og:title" content="([^"]+)"')
RATING_PATTERNS = [
    re.compile(r'"ratingValue"\s*:\s*"?([\d.]+)"?[^}]{0,200}?"ratingCount"\s*:\s*"?(\d+)"?', re.S),
    re.compile(
        r'"(?:overall_star_rating|star_rating)"\s*:\s*\{?[^}]*?"?(?:average_rating|value)"?\s*:\s*([\d.]+)'
        r"[^}]{0,200}?(?:rating_count|review_count)\"?\s*:\s*(\d+)",
        re.S,
    ),
    re.compile(r"([\d.]+)\s*out of 5[^\d]{0,20}([\d,]+)\s*(?:ratings|reviews|people)", re.I),
]
# Facebook routes a Page's declared "Website" link (and most other outbound links)
# through this redirector - the first one found is a reasonable, not certain, guess
# at the Page's own site.
OUTBOUND_LINK_RE = re.compile(r'facebook\.com/l\.php\?u=([^"&]+)')


def _extract_website(page_html: str) -> str | None:
    match = OUTBOUND_LINK_RE.search(page_html)
    if not match:
        return None
    candidate = unquote(match.group(1))
    host = urlparse(candidate).netloc.lower()
    if not host or "facebook.com" in host or "fbcdn.net" in host:
        return None
    return candidate


def _normalize_page_url(url: str) -> str | None:
    match = PAGE_URL_RE.match(url.split("#")[0])
    if not match:
        return None
    return f"https://www.facebook.com/{match.group(1)}"


def _parse_rating(page_html: str) -> tuple[float | None, int | None]:
    for pattern in RATING_PATTERNS:
        match = pattern.search(page_html)
        if not match:
            continue
        try:
            return float(match.group(1)), int(match.group(2).replace(",", ""))
        except ValueError:
            continue
    return None, None


class FacebookSource(PlatformSource):
    platform = "facebook"

    async def search(self, client: httpx.AsyncClient, search_term: str, region: str) -> list[CompetitorListing]:
        urls = await duckduckgo_search(client, f"site:facebook.com {search_term} {region}".strip())

        results = []
        seen: set[str] = set()
        for url in urls:
            normalized = _normalize_page_url(url)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            try:
                page_html = await fetch(client, normalized)
            except SearchBlocked:
                raise
            except Exception:
                continue

            name_match = NAME_RE.search(page_html)
            name = html.unescape(name_match.group(1)) if name_match else normalized.rstrip("/").rsplit("/", 1)[-1]
            rating, rating_count = _parse_rating(page_html)
            website = _extract_website(page_html)
            results.append(
                CompetitorListing(
                    platform=self.platform, name=name, url=normalized, rating=rating, rating_count=rating_count, website=website
                )
            )
        return results
