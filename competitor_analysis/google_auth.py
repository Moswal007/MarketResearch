"""OAuth2 access tokens for Google Places API (New), via the service account key
file at config.GOOGLE_SERVICE_ACCOUNT_FILE. A plain API key is Maps Platform's
more common auth method, but Places API (New) also accepts a service account's
OAuth2 token via the cloud-platform scope - the path used here, since a service
account is what's actually available.
"""

from google.auth.exceptions import DefaultCredentialsError, RefreshError
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from . import config

_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
_credentials: service_account.Credentials | None = None


class GoogleAuthError(Exception):
    """The service account file is missing, unreadable, or invalid - a setup
    problem, not "Google has no data for this query." Callers should surface
    this distinctly rather than treating it as an empty result."""


def _load_credentials() -> service_account.Credentials:
    global _credentials
    if _credentials is not None:
        return _credentials
    if not config.GOOGLE_SERVICE_ACCOUNT_FILE:
        raise GoogleAuthError("GOOGLE_SERVICE_ACCOUNT_FILE is not set in .env")
    try:
        _credentials = service_account.Credentials.from_service_account_file(
            config.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=_SCOPES
        )
    except FileNotFoundError:
        raise GoogleAuthError(f"Service account file not found: {config.GOOGLE_SERVICE_ACCOUNT_FILE}")
    except (ValueError, DefaultCredentialsError) as e:
        raise GoogleAuthError(f"Service account file is invalid: {e}")
    return _credentials


def get_access_token() -> str:
    """Returns a valid OAuth2 access token, refreshing it if expired or unset."""
    creds = _load_credentials()
    if not creds.valid:
        try:
            creds.refresh(Request())
        except RefreshError as e:
            raise GoogleAuthError(f"Failed to refresh the service account token: {e}")
    return creds.token
