"""Instagram has no public search for logged-out users and, more fundamentally,
no public star-rating/review-count feature at all - unlike Facebook, Google
Business, or Amazon. Profiles are found via DuckDuckGo (site:instagram.com) and
read for a display name and follower count instead; rating fields stay None with
a note explaining why, rather than being guessed.
"""

import html
import re

import httpx

from ..models import CompetitorListing
from ..websearch import SearchBlocked, duckduckgo_search, fetch
from .base import PlatformSource

PROFILE_URL_RE = re.compile(r"^https?://(?:www\.)?instagram\.com/([A-Za-z0-9_.]+)/?(?:[?#].*)?$")
EXCLUDED_SLUGS = {"p", "reel", "reels", "explore", "accounts", "stories", "direct", "about", "developer", "web"}

NAME_RE = re.compile(r'<meta property="og:title" content="([^"]+)"')
FOLLOWERS_RE = re.compile(r'([\d.,]+[KMB]?)\s*Followers', re.I)
EXTERNAL_URL_RE = re.compile(r'"external_url"\s*:\s*"(https?://[^"]+)"')

NO_RATING_NOTE = "Instagram has no public star-rating system"


def _normalize_profile_url(url: str) -> tuple[str, str] | None:
    match = PROFILE_URL_RE.match(url.split("#")[0])
    if not match:
        return None
    handle = match.group(1)
    if handle.lower() in EXCLUDED_SLUGS:
        return None
    return handle, f"https://www.instagram.com/{handle}/"


def _parse_followers(text: str) -> int | None:
    match = FOLLOWERS_RE.search(text)
    if not match:
        return None
    raw = match.group(1).upper().replace(",", "")
    multiplier = 1
    if raw.endswith("K"):
        multiplier, raw = 1_000, raw[:-1]
    elif raw.endswith("M"):
        multiplier, raw = 1_000_000, raw[:-1]
    elif raw.endswith("B"):
        multiplier, raw = 1_000_000_000, raw[:-1]
    try:
        return int(float(raw) * multiplier)
    except ValueError:
        return None


def _parse_bio_website(text: str) -> str | None:
    match = EXTERNAL_URL_RE.search(text)
    return match.group(1).encode().decode("unicode_escape") if match else None


class InstagramSource(PlatformSource):
    platform = "instagram"

    async def search(self, client: httpx.AsyncClient, search_term: str, region: str) -> list[CompetitorListing]:
        urls = await duckduckgo_search(client, f"site:instagram.com {search_term} {region}".strip())

        results = []
        seen: set[str] = set()
        for url in urls:
            normalized = _normalize_profile_url(url)
            if not normalized:
                continue
            handle, profile_url = normalized
            if profile_url in seen:
                continue
            seen.add(profile_url)

            try:
                page_html = await fetch(client, profile_url)
            except SearchBlocked:
                raise
            except Exception:
                # couldn't read the profile - still worth listing that it exists
                results.append(CompetitorListing(platform=self.platform, name=handle, url=profile_url, note=NO_RATING_NOTE))
                continue

            name_match = NAME_RE.search(page_html)
            name = html.unescape(name_match.group(1)) if name_match else handle
            followers = _parse_followers(page_html)
            website = _parse_bio_website(page_html)
            note = f"{NO_RATING_NOTE}; followers shown instead" if followers is not None else NO_RATING_NOTE
            results.append(
                CompetitorListing(
                    platform=self.platform, name=name, url=profile_url, followers=followers, website=website, note=note
                )
            )
        return results
