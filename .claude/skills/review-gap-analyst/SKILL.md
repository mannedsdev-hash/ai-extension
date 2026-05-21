---
name: review-gap-analyst
description: Pull low-star Amazon reviews for competitor ASINs via Apify, cluster recurring complaints, and turn them into concrete product improvement angles. Used by product-research-agent in Stage 1.
---

# review-gap-analyst

Find what competitors' products get wrong — so a new product can do it better.

## Tools
- Primary: the Apify MCP (server `apify`). Run the `amazon-reviews-extractor`
  actor (fall back to `amazon-scraper` review mode if needed).
- Discover the exact actor/tool names from the connected server at runtime.
- If the server is not connected, STOP and report it. Do not invent reviews.

## Procedure
1. Take the top 5-10 competitor ASINs from `data/competitors.json` (cap at
   `run_limits.max_competitor_asins`).
2. For each ASIN pull 1-3 star reviews via Apify, up to
   `run_limits.max_reviews_per_asin`.
3. Cluster complaints into recurring themes (durability, sizing, missing
   feature, instructions, packaging, etc.).
4. For each theme compute its share: percent of pulled negative reviews that
   mention it. Round to whole percent.
5. Convert each significant theme into a concrete, buildable improvement
   angle — e.g. "17% of complaints mention the lid cracking -> use a
   thicker hinge / different polymer".

## Output
Write a `review_gaps` block keyed by niche, merged into `data/products.json`
under the relevant candidate (or a staging file the orchestrator reads):

```json
{
  "niche": "string",
  "asins_analyzed": ["string"],
  "reviews_pulled": 0,
  "themes": [
    {
      "theme": "string",
      "share_pct": 0,
      "example_quotes": ["verbatim string"],
      "improvement_angle": "string"
    }
  ],
  "pulled_at": "ISO-8601"
}
```

Return the top improvement angles to the orchestrator.

## Guardrails
- Quotes are copied verbatim from tool output — never paraphrased or invented.
- Percentages are computed from the actual count pulled; state the
  denominator. If only 12 reviews were pulled, say "of 12".
- Cache raw review pulls under `data/cache/` keyed by ASIN.
