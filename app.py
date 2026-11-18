"""Vercel entrypoint - Vercel looks for a FastAPI `app` at the project root."""

from competitor_analysis.main import app  # noqa: F401
