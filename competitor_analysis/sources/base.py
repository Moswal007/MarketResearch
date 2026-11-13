from abc import ABC, abstractmethod

import httpx

from ..models import CompetitorListing


class PlatformSource(ABC):
    platform: str

    @abstractmethod
    async def search(self, client: httpx.AsyncClient, search_term: str, region: str) -> list[CompetitorListing]:
        """Returns listings found for one search term. Raise websearch.SearchBlocked
        if the platform/search engine refused the query outright; let it propagate
        rather than swallowing it into an empty list."""
        ...
