import random

import httpx

from ..models import CompetitorListing
from .base import PlatformSource


class MockSource(PlatformSource):
    """Deterministic sample data (seeded by platform + term + region), for demos
    and offline testing. Enable with USE_MOCK_DATA=true in .env."""

    def __init__(self, platform: str):
        self.platform = platform

    async def search(self, client: httpx.AsyncClient, search_term: str, region: str) -> list[CompetitorListing]:
        rng = random.Random(f"{self.platform}|{search_term.lower()}|{region.lower()}")
        count = rng.randint(1, 4)
        results = []
        for i in range(count):
            name = f"{search_term.title()} Co {i + 1}"
            slug = name.lower().replace(" ", "")
            website = f"https://{slug}.example.com"
            product_count = rng.randint(4, 120)
            price_low = rng.choice([9, 12, 15, 19, 25])
            price_high = price_low + rng.randint(10, 80)

            if self.platform == "instagram":
                results.append(
                    CompetitorListing(
                        platform=self.platform,
                        name=name,
                        url=f"https://instagram.com/{slug}",
                        followers=rng.randint(500, 300_000),
                        website=website,
                        product_count=product_count,
                        price_min=float(price_low),
                        price_max=float(price_high),
                        note="Instagram has no public star-rating system; followers shown instead",
                    )
                )
            elif self.platform == "facebook":
                results.append(
                    CompetitorListing(
                        platform=self.platform,
                        name=name,
                        url=f"https://facebook.com/{slug}",
                        rating=round(rng.uniform(3.4, 5.0), 1),
                        rating_count=rng.randint(20, 8000),
                        followers=rng.randint(500, 300_000),
                        profile_image=f"https://picsum.photos/seed/{slug}/80",
                        description=f"Sample {search_term} seller in {region} - online orders and local delivery.",
                        website=website,
                        product_count=product_count,
                        price_min=float(price_low),
                        price_max=float(price_high),
                    )
                )
            else:
                results.append(
                    CompetitorListing(
                        platform=self.platform,
                        name=name,
                        url=f"https://{self.platform}.com/{slug}",
                        rating=round(rng.uniform(3.4, 5.0), 1),
                        rating_count=rng.randint(20, 8000),
                        website=website,
                        product_count=product_count,
                        price_min=float(price_low),
                        price_max=float(price_high),
                    )
                )
        return results
