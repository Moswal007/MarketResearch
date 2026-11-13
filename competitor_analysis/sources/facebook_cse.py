"""Facebook Pages found via Google's Custom Search JSON API (Programmable Search
Engine) instead of a DuckDuckGo scrape + direct page fetch. Facebook walls off
its own pages for logged-out automated requests, but Google has already indexed
them: each result carries the Page's profile picture (pagemap cse_image /
og:image), its og:description ("Acme, Singapore. 12K followers · ... Handmade
soaps for sensitive skin") and the snippet - which together give the Page's
face, a summary of what it sells, and its follower count without ever touching
facebook.com. Used when GOOGLE_CSE_API_KEY and GOOGLE_CSE_ID are set; the
scraping-based FacebookSource in facebook.py is the fallback when they aren't.
"""

import html
import re

import httpx

from .. import config
from ..models import CompetitorListing
from ..websearch import SearchBlocked
from .base import PlatformSource
from .facebook import _normalize_page_url

SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

TITLE_SUFFIX_RE = re.compile(r"\s*[|\-–]\s*Facebook\s*$", re.I)
COUNT = r"([\d.,]+\s*[KMB]?)"
FOLLOWERS_RE = re.compile(COUNT + r"\s+followers", re.I)
LIKES_RE = re.compile(COUNT + r"\s+likes", re.I)
# The stat phrases Facebook packs into og:description - stripped so what's left
# reads as a description of the business, not a list of counters.
STATS_RE = re.compile(
    COUNT + r"\s+(?:likes?|followers?|following|talking about this|were here|check-ins?)\s*[·.]?\s*", re.I
)


def _parse_count(raw: str) -> int | None:
    raw = raw.upper().replace(",", "").replace(" ", "")
    multiplier = 1
    if raw[-1:] in ("K", "M", "B"):
        multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[raw[-1]]
        raw = raw[:-1]
    try:
        return int(float(raw) * multiplier)
    except ValueError:
        return None


def _first(pagemap: dict, key: str) -> dict:
    items = pagemap.get(key) or []
    return items[0] if items else {}


def _clean_description(text: str, name: str) -> str | None:
    text = STATS_RE.sub("", html.unescape(text)).strip(" ·.")
    # og:description opens with "<Page name>[, <city>]." - drop that echo of the name
    if text.lower().startswith(name.lower()):
        text = text[len(name):].lstrip()
        if text.startswith(","):
            text = text.split(".", 1)[1] if "." in text else ""
        text = text.lstrip(" .·")
    return text.strip() or None


class FacebookCSESource(PlatformSource):
    platform = "facebook"

    async def search(self, client: httpx.AsyncClient, search_term: str, region: str) -> list[CompetitorListing]:
        resp = await client.get(
            SEARCH_URL,
            params={
                "key": config.GOOGLE_CSE_API_KEY,
                "cx": config.GOOGLE_CSE_ID,
                "q": f"{search_term} {region}".strip(),
                "siteSearch": "facebook.com",
                "siteSearchFilter": "i",
                "num": 10,
            },
            timeout=15,
        )
        if resp.status_code in (400, 401, 403, 429):
            # bad key / API not enabled / daily quota spent - a setup problem, not an empty market
            raise SearchBlocked(f"Google Custom Search rejected the request ({resp.status_code}): {resp.text[:200]}")
        resp.raise_for_status()

        results = []
        seen: set[str] = set()
        for item in resp.json().get("items", []):
            url = _normalize_page_url(item.get("link", ""))
            if not url or url in seen:
                continue
            seen.add(url)

            pagemap = item.get("pagemap") or {}
            meta = _first(pagemap, "metatags")
            name = TITLE_SUFFIX_RE.sub("", html.unescape(meta.get("og:title") or item.get("title") or "")).strip()
            name = name or url.rstrip("/").rsplit("/", 1)[-1]
            profile_image = (
                meta.get("og:image") or _first(pagemap, "cse_image").get("src") or _first(pagemap, "cse_thumbnail").get("src")
            )

            og_description = meta.get("og:description") or ""
            snippet = (item.get("snippet") or "").replace("\n", " ")
            stats_text = f"{og_description} {snippet}"

            followers, note = None, None
            if match := FOLLOWERS_RE.search(stats_text):
                followers = _parse_count(match.group(1))
            elif match := LIKES_RE.search(stats_text):
                followers = _parse_count(match.group(1))
                note = "Follower count not in Google's index; Page likes shown instead"

            results.append(
                CompetitorListing(
                    platform=self.platform,
                    name=name,
                    url=url,
                    followers=followers,
                    profile_image=profile_image,
                    description=_clean_description(og_description or snippet, name),
                    note=note,
                )
            )
        return results
