---
name: pricing-competitor-analyst
description: Map the current competitive price landscape for a niche — price band, Buy Box / Featured Offer price, coupon and discount patterns, and who holds the Buy Box. Uses Apify. Used by product-research-agent in Stage 1.
---

# pricing-competitor-analyst

Understand the price a new product would have to compete at.

> **Free-stack note:** this skill uses Apify, not Keepa. You get *current*
> prices and Buy Box info — not price history. Historical price bands and
> price-war detection need a Keepa key, added later.

## Tools
- Apify MCP (server `apify`) — `amazon-scraper` (product-detail mode) and the
  search / storefront actor for live price, coupons, and Buy Box ownership.
- Discover exact actor/tool names from the connected server at runtime.
- If the server is not connected, STOP and report it.

## Procedure
1. Use the competitor ASINs already in `data/competitors.json`.
2. From Apify product-detail pulls collect, per ASIN: current listed price,
   active coupons / percent-off badges, Buy Box price, and which seller holds
   the Buy Box / Featured Offer.
3. Derive the niche price band from current prices: low / median / high.
4. Note pricing patterns: heavy couponing, a dominant Buy Box holder, or
   stable pricing. Historical price-war detection is not possible without
   Keepa — say so rather than guessing.

## Output
Merge a `pricing` block per niche into `data/products.json` (or a staging
file the orchestrator reads):

```json
{
  "niche": "string",
  "price_band": { "low": 0, "median": 0, "high": 0 },
  "buy_box_price": 0,
  "coupon_pattern": "string",
  "buy_box_holders": [{ "asin": "string", "seller": "string", "price": 0 }],
  "notes": "string",
  "pulled_at": "ISO-8601",
  "source": "apify"
}
```

Return the price band and the entry-price implication to the orchestrator —
this feeds the `sell_price` used by margin-scorer.

## Guardrails
- Report only prices/coupons returned by a tool. Use `null` for anything not
  observed.
- Cache pulls under `data/cache/` keyed by ASIN. Apify costs per result —
  respect `run_limits`.
