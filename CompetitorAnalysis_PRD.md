# CompetitorAnalysis Agent PRD

2026-09-27

## Overview

CompetitorAnalysis answers one question for a seller: who is already advertising this product on Facebook in this region, and how strong is the competition? Given a product name and a region, the agent finds Facebook pages and ad campaigns for the same or a similar product, then returns a competitive snapshot: the count of unique advertisers, each page's follower count, and the prices they're selling at, rolled into a short written summary.

It is one subagent inside the larger multiagent market-research system: the orchestrator hands it a product and region, and it hands back structured competitor data for the report-writer agent to fold into a broader research report.

## Goals & Success Metrics

A seller gets a reliable read on Facebook competition for a product/region pair in under 2 minutes, built only from advertisers who are actually selling that product.

| Metric | Target |
| --- | --- |
| Query-to-result latency | ≤ 2 minutes, p95 |
| Advertiser relevance (listed pages actually sell this product) | ≥ 80% precision, sampled review |
| Price field fill rate (advertisers with a price found) | ≥ 60% |
| Region coverage at launch | US, UK, India, Australia |

## Users & Use Cases

- A seller or brand owner deciding whether to launch a product in a region checks who's already advertising it on Facebook and at what price.
- A market researcher runs it as one input the orchestrator folds into a larger report, alongside other subagents.

Example: a user enters "stainless steel water bottle" and "United Kingdom" and gets back a list of active Facebook advertisers, their follower counts, and observed prices, plus a short summary of how crowded and price-competitive the space is.

## Scope

In scope for v1:
- Single product + single region per query.
- Facebook only (Pages + Ads Library) as the data source.
- Fields returned: unique advertiser count, follower count per advertiser, price(s) observed per advertiser, and a narrative summary.

Out of scope for v1:
- Platforms other than Facebook (Instagram, TikTok, Google Ads).
- Multi-region or multi-product batch queries.
- Historical trend tracking — this is a point-in-time snapshot, not ongoing monitoring.

## Functional Requirements

**Input**

| Field | Required | Notes |
| --- | --- | --- |
| Product | Yes | Free-text product description, e.g. "stainless steel water bottle" |
| Region | Yes | Country or metro area; mapped to the Ads Library's country filter |

**Output**

| Field | Description |
| --- | --- |
| Unique advertiser count | Distinct Facebook pages running ads for the same/similar product in the region |
| Followers per advertiser | Facebook page follower count for each advertiser found |
| Price(s) sold | Price(s) extracted from the ad creative, landing page, or page shop, per advertiser |
| Summary | Advertiser count, follower range, price range, and how crowded/competitive the space looks |

**Edge cases**
- No advertisers found → return zero counts and a plain "no active Facebook advertisers found for this product/region" message, not an error.
- Price not extractable for an advertiser → omit that advertiser's price rather than guessing.
- Ambiguous product terms (e.g. "bottle") → surface the search terms actually used, so the user can tell what was matched.

## Data Sources & Collection Method

Primary source: Meta's Facebook Ads Library (ads by keyword, filterable by country), cross-referenced with each advertiser's Facebook Page for follower counts.

Collection steps:
1. Expand the product text into a small set of search terms (the product itself plus close synonyms).
2. Query the Ads Library for each term, scoped to the given region, and collect the distinct advertiser Pages returned.
3. For each advertiser Page, pull the follower count and, where visible, price from the ad creative or the Page's shop/catalog.
4. De-duplicate advertisers across search terms before counting.

The Ads Library is the intended source specifically because it's built for this — public ad transparency data, queryable by country. Scraping Pages for anything beyond public follower counts is out of scope: the agent operates within Meta's platform terms rather than around them.

## System Architecture

The orchestrator or the web UI calls CompetitorAnalysis with `{product, region}`; the agent queries Facebook's Ads Library for that product/region, pulls follower counts and prices from the matching Pages, and hands a structured result back for the Report Writer agent to fold into the final report.

```
User / Orchestrator ──▶ Competitor Analysis ──▶ Report Writer Agent
                              │        ▲
                   query:     │        │  pages + ad data
                   product +  ▼        │
                   region  Facebook Ads Library
                            + Pages: followers, prices
```

## UI/UX

A single-page web form: two inputs, Product and Region, and a Search button. On submit, a loading state shows while the agent queries Facebook. The results page opens with a one-line summary, then a table of advertisers — page name, followers, price, link to the Page — sorted by follower count descending.

This is also the interface other agents use: the same product/region inputs and structured result are exposed as an API the orchestrator can call directly, with the web form as the human-facing wrapper around it.

## Non-Functional Requirements

| Requirement | Target |
| --- | --- |
| Latency | ≤ 2 min per query, p95 |
| Facebook API rate limits | Respect Ads Library API limits; queue/backoff rather than hard-fail |
| Caching | Cache results per product/region for 24 hours to avoid re-querying Facebook on repeat lookups |
| Compliance | Use only Meta's public Ads Library API and public Page data; no login-walled scraping |
| Availability | Degrade gracefully — partial results + a note — rather than fail the whole query if one advertiser's data can't be fetched |

## Risks, Assumptions & Open Questions

- Facebook may rate-limit or change Ads Library API access, which would directly break this agent's core data source.
- "Similar product" matching is fuzzy: overly broad search terms pull in unrelated advertisers, overly narrow terms undercount real competitors.
- Price isn't always visible in an ad; extracting it from a linked landing page or shop adds a scraping dependency Facebook doesn't control.
- Assumes the Ads Library covers the target regions at launch (US, UK, India, Australia) with usable data.

Open questions:
- [ ] How should "similar product" be defined — exact keyword match, or LLM-driven synonym expansion?
- [ ] Should advertisers with very low ad spend be flagged as noise, or included in every match?

## Milestones / Rollout Plan

| Phase | Scope |
| --- | --- |
| 1 — MVP | One region, keyword-based product matching, advertiser count + followers from the Ads Library (no price extraction) |
| 2 — Pricing | Add price extraction from ad creative and landing pages |
| 3 — Scale | Multi-region support, 24-hour result caching, orchestrator-callable API |
| 4 — Launch | All four target regions (US, UK, India, Australia) live behind the web form and the API |

---
Source of truth / live editable version: https://claude.ai/code/artifact/d881cc96-ae16-4cd3-ae8f-48414ae74944
