"""Google Places API (New) - the actual source of a business's rating and
rating count on Google, unlike organic web search which carries no rating data
at all. Used when GOOGLE_SERVICE_ACCOUNT_FILE is set (see google_auth.py); the
scraping-based GoogleSource in google.py is the fallback when it isn't.
"""

import httpx

from ..google_auth import GoogleAuthError, get_access_token
from ..models import CompetitorListing
from ..websearch import SearchBlocked
from .base import PlatformSource

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = "places.displayName,places.rating,places.userRatingCount,places.googleMapsUri,places.websiteUri"


class GooglePlacesSource(PlatformSource):
    platform = "google"

    async def search(self, client: httpx.AsyncClient, search_term: str, region: str) -> list[CompetitorListing]:
        try:
            token = get_access_token()
        except GoogleAuthError as e:
            # a setup/auth problem, not "no listings" - must not be reported as an empty market
            raise SearchBlocked(f"Google Places auth failed: {e}")

        resp = await client.post(
            SEARCH_URL,
            json={"textQuery": f"{search_term} {region}"},
            headers={
                "Authorization": f"Bearer {token}",
                "X-Goog-FieldMask": FIELD_MASK,
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        if resp.status_code in (401, 403):
            raise SearchBlocked(f"Google Places rejected the request ({resp.status_code}): {resp.text[:200]}")
        resp.raise_for_status()
        data = resp.json()

        results = []
        for place in data.get("places", []):
            name = (place.get("displayName") or {}).get("text")
            if not name:
                continue
            results.append(
                CompetitorListing(
                    platform=self.platform,
                    name=name,
                    url=place.get("googleMapsUri"),
                    rating=place.get("rating"),
                    rating_count=place.get("userRatingCount"),
                    website=place.get("websiteUri"),
                )
            )
        return results
