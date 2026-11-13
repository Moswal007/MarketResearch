"""Expands common region abbreviations to a full name for a cleaner search query.
Unrecognized input is passed through as typed — there's no API call to validate
against here, so an unknown region just becomes part of the search text."""

REGION_ALIASES = {
    "us": "United States", "usa": "United States", "u.s.": "United States",
    "uk": "United Kingdom", "u.k.": "United Kingdom", "britain": "United Kingdom",
    "uae": "United Arab Emirates",
    "aus": "Australia",
}


def normalize_region(region: str) -> str:
    key = region.strip().lower()
    return REGION_ALIASES.get(key, region.strip())
