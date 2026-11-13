"""Best-effort product-catalog discovery on a company's own website (not the
platform listing) - PRD extension: "number of products" and "price range" per
competitor. There is no universal way to read an arbitrary e-commerce site's
catalog, so this tries the one common structural shortcut that actually works
(Shopify's public /products.json) and otherwise falls back to a rough price
scan of the homepage/shop page. It degrades to "couldn't determine" rather than
guessing, same as every other source in this agent.
"""

import asyncio
import re
from urllib.parse import urljoin

import httpx

from .models import CompetitorListing
from .websearch import BROWSER_HEADERS, SearchBlocked, fetch

PRICE_RE = re.compile(r"[$£€]\s?(\d{1,5}(?:[.,]\d{2})?)")
SHOP_LINK_RE = re.compile(
    r'<a[^>]+href="([^"]+)"[^>]*>[^<]{0,40}(?:shop|store|products|collections)[^<]{0,20}</a>', re.I
)
MAX_CONCURRENT_SITES = 5


async def _shopify_catalog(client: httpx.AsyncClient, base_url: str) -> tuple[int, float | None, float | None] | None:
    """Shopify stores expose a public, unauthenticated /products.json - the most
    reliable source, when a site happens to run on Shopify."""
    try:
        resp = await client.get(
            urljoin(base_url, "/products.json"), params={"limit": 250}, headers=BROWSER_HEADERS, timeout=12
        )
    except Exception:
        return None
    if resp.status_code != 200:
        return None
    try:
        products = resp.json().get("products")
    except ValueError:
        return None
    if not products:
        return None

    prices = []
    for product in products:
        for variant in product.get("variants", []):
            price = variant.get("price")
            if price is None:
                continue
            try:
                prices.append(float(price))
            except (TypeError, ValueError):
                continue

    return (len(products), min(prices), max(prices)) if prices else (len(products), None, None)


async def _generic_price_scan(client: httpx.AsyncClient, base_url: str) -> tuple[int, float | None, float | None] | None:
    """Fallback for non-Shopify sites: read the homepage, follow an obvious
    shop/products link if there is one, and count distinct price-looking tokens
    on that page as a rough proxy for product count. Fragile by nature - most
    custom-built sites won't parse cleanly this way, and this undercounts any
    catalog spread across multiple pages."""
    try:
        home_html = await fetch(client, base_url)
    except SearchBlocked:
        raise
    except Exception:
        return None

    target_html = home_html
    shop_match = SHOP_LINK_RE.search(home_html)
    if shop_match:
        try:
            target_html = await fetch(client, urljoin(base_url, shop_match.group(1)))
        except Exception:
            target_html = home_html

    prices = sorted({float(m.replace(",", "")) for m in PRICE_RE.findall(target_html)})
    if not prices:
        return None
    return len(prices), prices[0], prices[-1]


async def _read_catalog(client: httpx.AsyncClient, website: str) -> tuple[int, float | None, float | None] | None:
    result = await _shopify_catalog(client, website)
    if result is not None:
        return result
    return await _generic_price_scan(client, website)


async def enrich_with_catalogs(listings: list[CompetitorListing]) -> None:
    """Mutates each listing in place with product_count/price_min/price_max
    (or catalog_note explaining why not), for listings that have a website.
    Bounded concurrency so N company sites don't serialize the whole request."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SITES)

    async def enrich_one(listing: CompetitorListing) -> None:
        if not listing.website:
            return  # no site found for this listing - nothing to scrape, no note needed
        async with semaphore:
            async with httpx.AsyncClient(headers=BROWSER_HEADERS, follow_redirects=True) as client:
                try:
                    result = await _read_catalog(client, listing.website)
                except SearchBlocked:
                    listing.catalog_note = "The company website blocked this automated request"
                    return
                except Exception:
                    listing.catalog_note = "Couldn't read the company website"
                    return
        if result is None:
            listing.catalog_note = "Couldn't determine a product catalog on this website"
            return
        listing.product_count, listing.price_min, listing.price_max = result

    await asyncio.gather(*(enrich_one(listing) for listing in listings))
