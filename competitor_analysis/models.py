from typing import List, Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    product: str = Field(..., min_length=1)
    region: str = Field(..., min_length=1)


class CompetitorListing(BaseModel):
    platform: str  # "facebook" | "google" | "instagram" | "amazon"
    name: str
    url: Optional[str] = None
    rating: Optional[float] = None        # current aggregate out of 5, where the platform has one
    rating_count: Optional[int] = None    # how many people rated it
    followers: Optional[int] = None       # bonus metric, mainly for Instagram (no public rating system)
    note: Optional[str] = None            # e.g. why this listing has no rating
    profile_image: Optional[str] = None   # the page/profile's picture (Facebook via Google Custom Search)
    description: Optional[str] = None     # what the business says it sells - its page's own summary

    website: Optional[str] = None         # the company's own site, if found - not the platform listing URL
    product_count: Optional[int] = None   # products found on that site's catalog
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    catalog_note: Optional[str] = None    # e.g. why the catalog couldn't be read, when a website was found


class AnalyzeResult(BaseModel):
    product: str
    region: str
    search_terms_used: List[str]
    unique_listing_count: int
    listings: List[CompetitorListing]
    platforms_blocked: List[str] = []  # platforms whose search was refused outright - not a "0 results" signal
    summary: str
    data_source: str
    cached: bool = False
    generated_at: str
