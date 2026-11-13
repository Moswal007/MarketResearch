"""24-hour file cache keyed by product+region (PRD: Non-Functional Requirements —
avoid re-querying Facebook on repeat lookups)."""

import json
import time

from . import config


def _cache_path(key: str):
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = key.replace("/", "_")
    return config.CACHE_DIR / f"{safe}.json"


def make_key(product: str, region: str) -> str:
    return f"{product.strip().lower()}|{region.strip().lower()}"


def get(key: str) -> dict | None:
    path = _cache_path(key)
    if not path.exists():
        return None
    age_hours = (time.time() - path.stat().st_mtime) / 3600
    if age_hours > config.CACHE_TTL_HOURS:
        return None
    return json.loads(path.read_text())


def set(key: str, value: dict) -> None:
    _cache_path(key).write_text(json.dumps(value))
