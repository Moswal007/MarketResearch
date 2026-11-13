"""Google has its own search, queried directly - no external engine involved.
Google's local business ratings (the "4.5 stars (230)" shown for a shop) are
rendered by JavaScript for a normal visitor, so a plain HTTP fetch only picks up
a rating when Google's response happens to include the underlying schema.org
LocalBusiness/aggregateRating JSON-LD. When it doesn't, this returns nothing
rather than guessing at a rating from unstructured text.
"""

import html
import re

import httpx

from ..models import CompetitorListing
from ..websearch import SearchBlocked, fetch
from .base import PlatformSource

NAME_RATING_RE = re.compile(
    r'"name"\s*:\s*"([^"]{2,80})"[^{}]{0,400}?"aggregateRating"\s*:\s*\{[^{}]*?'
    r'"ratingValue"\s*:\s*"?([\d.]+)"?[^{}]*?"reviewCount"\s*:\s*"?(\d+)"?',
    re.S,
)


class GoogleSource(PlatformSource):
    platform = "google"

    async def search(self, client: httpx.AsyncClient, search_term: str, region: str) -> list[CompetitorListing]:
        try:
            page_html = await fetch(
                client, "https://www.google.com/search", params={"q": f"{search_term} {region}", "num": 10}
            )
        except SearchBlocked:
            raise
        except Exception:
            return []

        results = []
        seen: set[str] = set()
        for match in NAME_RATING_RE.finditer(page_html):
            name = html.unescape(match.group(1)).strip()
            if name.lower() in seen:
                continue
            seen.add(name.lower())
            results.append(
                CompetitorListing(platform=self.platform, name=name, rating=float(match.group(2)), rating_count=int(match.group(3)))
            )
        return results
