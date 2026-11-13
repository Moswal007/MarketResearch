import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

LLM_API_BASE_URL = os.getenv("API_BASE_URL", "")
LLM_API_KEY = os.getenv("API_KEY", "")
LLM_MODEL = os.getenv("MODEL", "")

USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "false").strip().lower() == "true"

# Path to a Google Cloud service account JSON key file with the Places API
# enabled on its project. Used for OAuth2 auth to Places API (New) - the actual
# source of Google ratings/rating counts (organic web search carries no rating
# data). Leave unset to fall back to a best-effort, frequently-blocked scrape
# of google.com/search instead.
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()

# Google Custom Search JSON API key + Programmable Search Engine ID (cx). When
# both are set, Facebook Pages are found through Google's index - with each
# Page's profile picture, description and follower count - instead of a
# DuckDuckGo scrape that Facebook mostly blocks.
GOOGLE_CSE_API_KEY = os.getenv("GOOGLE_CSE_API_KEY", "").strip()
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "").strip()

# Meta Graph API access token (e.g. an app token "APP_ID|APP_SECRET") for an app
# approved for the "Page Public Metadata Access" feature. When set, Facebook
# Pages - followers, category, what they sell - come straight from Meta, ahead
# of the Google Custom Search and scraping fallbacks.
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "").strip()
META_GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v23.0").strip()

CACHE_TTL_HOURS = float(os.getenv("CACHE_TTL_HOURS", "24"))
CACHE_DIR = PROJECT_ROOT / ".cache" / "competitor_analysis"
