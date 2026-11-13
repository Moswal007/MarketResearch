"""Amazon has its own public search and, unlike the other three platforms, a
first-class rating + rating-count on every listing - the best structural fit for
what this agent reports. Searched directly against the region's Amazon domain,
no external search engine involved. Amazon's result markup changes over time and
is not officially documented for scraping, so this parsing is best-effort and may
need updating if Amazon changes its page structure.
"""

import html
import re

import httpx

from ..models import CompetitorListing
from ..websearch import SearchBlocked, fetch
from .base import PlatformSource

AMAZON_DOMAINS = {
    "united states": "amazon.com",
    "united kingdom": "amazon.co.uk",
    "india": "amazon.in",
    "australia": "amazon.com.au",
    "canada": "amazon.ca",
    "germany": "amazon.de",
    "france": "amazon.fr",
    "japan": "amazon.co.jp",
}

TITLE_RE = re.compile(r'<span[^>]*class="[^"]*a-size-(?:medium|base-plus)[^"]*"[^>]*>([^<]{3,150})</span>')
RATING_RE = re.compile(r"([\d.]+) out of 5 stars")
COUNT_RE = re.compile(r'aria-label="([\d,]+)"[^>]*class="[^"]*s-underline-text')


def _amazon_domain(region: str) -> str:
    return AMAZON_DOMAINS.get(region.strip().lower(), "amazon.com")


def _parse_listings(page_html: str, platform: str, max_results: int = 8) -> list[CompetitorListing]:
    blocks = page_html.split('data-component-type="s-search-result"')[1 : max_results + 1]
    results = []
    for block in blocks:
        title_match = TITLE_RE.search(block)
        if not title_match:
            continue
        name = html.unescape(title_match.group(1)).strip()

        rating_match = RATING_RE.search(block)
        rating = float(rating_match.group(1)) if rating_match else None

        count_match = COUNT_RE.search(block)
        rating_count = None
        if count_match:
            try:
                rating_count = int(count_match.group(1).replace(",", ""))
            except ValueError:
                rating_count = None

        results.append(CompetitorListing(platform=platform, name=name, rating=rating, rating_count=rating_count))
    return results


class AmazonSource(PlatformSource):
    platform = "amazon"

    async def search(self, client: httpx.AsyncClient, search_term: str, region: str) -> list[CompetitorListing]:
        domain = _amazon_domain(region)
        try:
            page_html = await fetch(client, f"https://www.{domain}/s", params={"k": search_term})
        except SearchBlocked:
            raise
        except Exception:
            return []
        return _parse_listings(page_html, self.platform)
