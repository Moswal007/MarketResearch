from .. import config
from .amazon import AmazonSource
from .base import PlatformSource
from .facebook import FacebookSource
from .facebook_cse import FacebookCSESource
from .facebook_graph import FacebookGraphSource
from .google import GoogleSource
from .google_places import GooglePlacesSource
from .instagram import InstagramSource
from .mock import MockSource

PLATFORM_CLASSES = {
    "facebook": FacebookSource,
    "google": GoogleSource,
    "instagram": InstagramSource,
    "amazon": AmazonSource,
}


def get_sources(use_mock: bool) -> dict[str, PlatformSource]:
    if use_mock:
        return {name: MockSource(name) for name in PLATFORM_CLASSES}

    sources = {name: cls() for name, cls in PLATFORM_CLASSES.items()}
    if config.GOOGLE_SERVICE_ACCOUNT_FILE or config.GOOGLE_SERVICE_ACCOUNT_JSON:
        sources["google"] = GooglePlacesSource()  # official API over the fragile scrape, when configured
    if config.GOOGLE_CSE_API_KEY and config.GOOGLE_CSE_ID:
        sources["facebook"] = FacebookCSESource()  # Google's index of Facebook over the blocked direct scrape
    if config.META_ACCESS_TOKEN:
        sources["facebook"] = FacebookGraphSource()  # Meta's own API over any third-party copy
    return sources
