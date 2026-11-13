"""Facebook Pages via Meta's own Graph API - the official, terms-compliant source
of public Page data for Pages the app doesn't own. Needs an access token from an
app approved for the "Page Public Metadata Access" feature (business verification
+ app review); with it, Meta returns each Page's follower count, category and its
own "about"/description - what it sells - straight from Facebook rather than from
a search engine's possibly stale copy. Used when META_ACCESS_TOKEN is set, ahead
of the Google Custom Search (facebook_cse.py) and scraping (facebook.py) sources.

Two calls per search term: the Pages Search endpoint finds candidate Pages, then
one batched ?ids= lookup reads their public fields.
"""

import httpx

from .. import config
from ..models import CompetitorListing
from ..websearch import SearchBlocked
from .base import PlatformSource

SEARCH_FIELDS = "id,name,location"
PAGE_FIELDS = "name,link,followers_count,fan_count,category,about,description,website,picture.type(large){url}"
MAX_PAGES = 10

# Graph API error codes meaning "this token/app can't make this call at all" or
# "throttled" - a setup or quota problem, never an empty market.
AUTH_ERROR_CODES = {10, 102, 190, 200, 368}
RATE_LIMIT_ERROR_CODES = {4, 17, 32, 613, 80001}


def _check(resp: httpx.Response) -> dict:
    data = resp.json() if resp.content else {}
    error = data.get("error") if isinstance(data, dict) else None
    if error:
        code = error.get("code")
        message = f"Meta Graph API error {code}: {error.get('message', '')[:200]}"
        if code in AUTH_ERROR_CODES or code in RATE_LIMIT_ERROR_CODES or resp.status_code in (401, 403, 429):
            raise SearchBlocked(message)
        raise RuntimeError(message)
    resp.raise_for_status()
    return data


def _in_region(page: dict, region: str) -> bool:
    # Pages Search has no country filter; drop Pages whose declared country is
    # clearly elsewhere, but keep those with no location (most online sellers).
    country = (page.get("location") or {}).get("country")
    return not country or not region or country.lower() == region.lower()


class FacebookGraphSource(PlatformSource):
    platform = "facebook"

    async def search(self, client: httpx.AsyncClient, search_term: str, region: str) -> list[CompetitorListing]:
        base = f"https://graph.facebook.com/{config.META_GRAPH_VERSION}"
        auth = {"access_token": config.META_ACCESS_TOKEN}

        found = _check(
            await client.get(
                f"{base}/pages/search",
                params={**auth, "q": search_term, "fields": SEARCH_FIELDS, "limit": 25},
                timeout=15,
            )
        )
        page_ids = [p["id"] for p in found.get("data", []) if p.get("id") and _in_region(p, region)][:MAX_PAGES]
        if not page_ids:
            return []

        pages = _check(
            await client.get(
                f"{base}/",
                params={**auth, "ids": ",".join(page_ids), "fields": PAGE_FIELDS},
                timeout=15,
            )
        )

        results = []
        for page_id in page_ids:  # keep Pages Search's relevance order
            page = pages.get(page_id)
            if not page or not page.get("name"):
                continue
            followers, note = page.get("followers_count"), None
            if followers is None and page.get("fan_count") is not None:
                followers = page["fan_count"]
                note = "Follower count not returned by Meta; Page likes shown instead"
            offering = page.get("about") or page.get("description")
            description = " · ".join(part for part in (page.get("category"), offering) if part) or None
            results.append(
                CompetitorListing(
                    platform=self.platform,
                    name=page["name"],
                    url=page.get("link") or f"https://www.facebook.com/{page_id}",
                    followers=followers,
                    profile_image=((page.get("picture") or {}).get("data") or {}).get("url"),
                    description=description,
                    website=next(iter((page.get("website") or "").split()), None),  # may list several, space-separated
                    note=note,
                )
            )
        return results
