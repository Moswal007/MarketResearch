from .models import CompetitorListing


def dedupe_and_merge(all_results: list[CompetitorListing]) -> list[CompetitorListing]:
    """Collapses results from multiple search terms into one row per real listing,
    keyed by (platform, url or name) - dedupe happens within a platform only,
    since the same business legitimately shows up once per platform it's on."""
    by_key: dict[tuple[str, str], CompetitorListing] = {}
    for item in all_results:
        key = (item.platform, (item.url or item.name).lower())
        if key not in by_key:
            by_key[key] = item
            continue
        existing = by_key[key]
        if existing.rating is None and item.rating is not None:
            existing.rating = item.rating
            existing.rating_count = item.rating_count
        if existing.followers is None and item.followers is not None:
            existing.followers = item.followers
        existing.profile_image = existing.profile_image or item.profile_image
        existing.description = existing.description or item.description

    return sorted(by_key.values(), key=lambda a: (a.platform, -(a.rating_count or a.followers or 0)))
