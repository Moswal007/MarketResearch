"""Thin client for the OpenAI-compatible LLM gateway configured in .env.

Used for two things the PRD calls for: expanding a product into a handful of
close-synonym search terms, and writing the narrative summary. Both degrade to a
plain fallback if the gateway is unreachable or unconfigured, so the rest of the
pipeline keeps working without an LLM.
"""

import httpx

from . import config


async def _chat(messages: list[dict], max_tokens: int = 200, temperature: float = 0.3) -> str | None:
    if not config.LLM_API_KEY or not config.LLM_API_BASE_URL:
        return None
    url = config.LLM_API_BASE_URL.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {config.LLM_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": config.LLM_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


async def expand_search_terms(product: str, max_terms: int = 4) -> list[str]:
    prompt = (
        f"List up to {max_terms} short search phrases a shopper would use on Facebook "
        f'for the same or a very similar product to: "{product}". '
        "One per line, no numbering, no explanation."
    )
    content = await _chat([{"role": "user", "content": prompt}], max_tokens=80)

    terms = [product]
    if content:
        for line in content.splitlines():
            term = line.strip("-*\t ").strip()
            if term and term.lower() != product.lower():
                terms.append(term)

    seen: set[str] = set()
    unique_terms = []
    for term in terms:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            unique_terms.append(term)
    return unique_terms[:max_terms] or [product]


async def write_summary(
    product: str, region: str, listings: list, unique_count: int, platforms_blocked: list[str] | None = None
) -> str:
    platforms_blocked = sorted(set(platforms_blocked or []))

    if unique_count == 0 and platforms_blocked:
        blocked_str = ", ".join(p.title() for p in platforms_blocked)
        return (
            f'{blocked_str} blocked this automated search for "{product}" in {region}. '
            "This is not a market signal — no competitor data could be collected from those platforms. "
            "Try again later, from a different network, or set USE_MOCK_DATA=true in .env to demo the pipeline."
        )
    if unique_count == 0:
        return f'No listings found for "{product}" in {region} across the searched platforms.'

    by_platform: dict[str, list] = {}
    for item in listings:
        by_platform.setdefault(item.platform, []).append(item)

    parts = []
    for platform, items in by_platform.items():
        ratings = [i.rating for i in items if i.rating is not None]
        if ratings:
            parts.append(f"{platform}: {len(items)} listing(s), rating {min(ratings):.1f}-{max(ratings):.1f}")
        else:
            parts.append(f"{platform}: {len(items)} listing(s), no public rating")
    stats_line = "; ".join(parts)

    blocked_note = f" ({', '.join(p.title() for p in platforms_blocked)} blocked and excluded)" if platforms_blocked else ""
    fallback = f'{unique_count} listing(s) found for "{product}" in {region} across {", ".join(by_platform)}{blocked_note}. {stats_line}.'

    prompt = (
        f"Write a 2-3 sentence competitive summary for a seller. Product: {product}. Region: {region}. "
        f"Findings by platform: {stats_line}. "
        + (f"Platforms blocked and excluded from this run: {', '.join(platforms_blocked)}. " if platforms_blocked else "")
        + "Be concrete and plain, no fluff, no markdown. Note that ratings are each listing's current total, "
        "not a year-by-year history, since none of these platforms publish that."
    )
    content = await _chat([{"role": "user", "content": prompt}], max_tokens=200)
    return content or fallback
