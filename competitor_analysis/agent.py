"""The CompetitorAnalysis subagent.

Given a product and a region, searches Google, Instagram, Facebook, and Amazon
for listings of the same or a similar product in that region, and returns each
listing's name, rating, and rating count where the platform has one, plus a
narrative summary - the contract the orchestrator and the report-writer agent
rely on (PRD: System Architecture, as extended to four platforms). No API keys
anywhere: every platform is read via a public search or its own public HTML.
"""

import asyncio
from datetime import datetime, timezone

import httpx

from . import cache, llm, region_codes
from .aggregator import dedupe_and_merge
from .company_site import enrich_with_catalogs
from .config import USE_MOCK_DATA
from .models import AnalyzeRequest, AnalyzeResult, CompetitorListing
from .sources import get_sources
from .websearch import BROWSER_HEADERS, SearchBlocked


class CompetitorAnalysisAgent:
    def __init__(self):
        self.sources = get_sources(USE_MOCK_DATA)
        self.data_source = "mock_sample_data" if USE_MOCK_DATA else "live_search"

    async def run(self, request: AnalyzeRequest) -> AnalyzeResult:
        key = cache.make_key(request.product, request.region)
        cached = cache.get(key)
        # Never serve sample data as live results (or vice versa) - both modes share one cache dir
        if cached and cached.get("data_source") == self.data_source:
            cached["cached"] = True
            return AnalyzeResult(**cached)

        region = region_codes.normalize_region(request.region)
        search_terms = await llm.expand_search_terms(request.product)

        platforms_blocked: list[str] = []

        async def run_platform(name: str, source) -> list[CompetitorListing]:
            async with httpx.AsyncClient(headers=BROWSER_HEADERS) as client:
                for term in search_terms:
                    try:
                        return await source.search(client, term, region)
                    except SearchBlocked:
                        platforms_blocked.append(name)
                        return []
                    except Exception:
                        continue  # this term failed for this platform - try the next term
                return []

        platform_results = await asyncio.gather(*(run_platform(name, src) for name, src in self.sources.items()))

        all_results: list[CompetitorListing] = [item for results in platform_results for item in results]
        listings = dedupe_and_merge(all_results)
        if not USE_MOCK_DATA:
            await enrich_with_catalogs(listings)  # mutates listings in place with each site's product catalog
        unique_count = len(listings)
        summary = await llm.write_summary(request.product, region, listings, unique_count, platforms_blocked)

        result = AnalyzeResult(
            product=request.product,
            region=request.region,
            search_terms_used=search_terms,
            unique_listing_count=unique_count,
            listings=listings,
            platforms_blocked=sorted(set(platforms_blocked)),
            summary=summary,
            data_source=self.data_source,
            cached=False,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        # Don't cache sample data, or a total wipeout - it should retry next time
        if not USE_MOCK_DATA and not (unique_count == 0 and platforms_blocked):
            cache.set(key, result.model_dump())
        return result
