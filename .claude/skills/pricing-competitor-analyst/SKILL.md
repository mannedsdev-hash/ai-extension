---
name: pricing-competitor-analyst
description: Map the competitive price landscape for a niche — price band, Buy Box / Featured Offer price, coupon and discount patterns, and who holds the Buy Box. Uses Keepa and Apify. Used by product-research-agent in Stage 1.
---

# pricing-competitor-analyst

Understand the price a new product would have to compete at.

## Tools
- Keepa MCP (server `keepa`) — price history, Buy Box history.
- Apify MCP (server `apify`) — storefront / search actor for live listing
  price, coupons, and Buy Box ownership.
- Discover exact tool/actor names from the connected servers at runtime.
- If a required server is missing, STOP and report it.

## Procedure
1. Use the competitor ASINs already in `data/competitors.json`.
2. From Keepa: per-ASIN price history and Buy Box price history. Derive the
   niche price band (low / median / high) and Buy Box price band.
3. From Apify storefront/search: current listed price, active coupons and
   percent-off badges, and which seller currently holds the Buy Box /
   Featured Offer.
4. Note pricing patterns: heavy couponing, price wars, a dominant Buy Box
   holder, or stable pricing.

## Output
Merge a `pricing` block per niche into `data/products.json` (or a staging
file the orchestrator reads):

```json
{
  "niche": "string",
  "price_band": { "low": 0, "median": 0, "high": 0 },
  "buy_box_band": { "low": 0, "high": 0 },
  "coupon_pattern": "string",
  "buy_box_holders": [{ "asin": "string", "seller": "string", "price": 0 }],
  "notes": "string",
  "pulled_at": "ISO-8601"
}
```

Return the price band and the entry-price implication to the orchestrator —
this feeds the `sell_price` used by margin-scorer.

## Guardrails
- Report only prices/coupons returned by a tool. Use `null` for anything not
  observed.
- Cache pulls under `data/cache/` keyed by ASIN.
