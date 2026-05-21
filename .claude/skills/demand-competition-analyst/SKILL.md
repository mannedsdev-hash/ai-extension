---
name: demand-competition-analyst
description: Measure Amazon demand and competitive saturation for a niche using Keepa — BSR trend, sales velocity, price history, offer/seller counts, review counts. Used by product-research-agent in Stage 1.
---

# demand-competition-analyst

Quantify how much a niche sells and how crowded it is.

## Tools
- Primary: the Keepa MCP (server `keepa`). Use its product / best-sellers /
  search tools.
- Discover exact tool names from the connected server at runtime.
- If the server is not connected, STOP and report the missing server. Do not
  estimate sales figures without data.

## Procedure
1. Resolve the niche to a category and a set of candidate ASINs (Keepa
   best-sellers / search). Cap at `run_limits.max_asins_per_run`.
2. For each ASIN pull from Keepa:
   - current Best Sellers Rank and its trend over `demand.trend_lookback_days`
   - estimated monthly sales / sales velocity (if Keepa provides it)
   - price history (min / max / current)
   - number of offers and distinct sellers
   - total review count
3. Classify per niche:
   - demand trend: `growing` / `flat` / `declining` (from BSR direction)
   - saturation: count listings with reviews >= `saturation.entrenched_review_count`.
     More than `saturation.max_entrenched_sellers` such listings, or total
     offers above `saturation.crowded_total_offers`, means crowded.
4. Flag a niche `avoid` when demand is declining or saturation is high with
   no demand growth.

## Output
Update `data/competitors.json` (a JSON array). One object per ASIN:

```json
{
  "asin": "string",
  "niche": "string",
  "title": "string",
  "bsr": 0,
  "bsr_trend": "growing|flat|declining",
  "est_monthly_sales": null,
  "price": { "current": 0, "min": 0, "max": 0 },
  "offers": 0,
  "sellers": 0,
  "review_count": 0,
  "pulled_at": "ISO-8601",
  "source": "keepa"
}
```

Return a niche-level summary: demand trend, saturation verdict, and the
entrenched-seller count, each with the numbers behind it.

## Guardrails
- Use `null` for any metric Keepa does not return — never fill a gap with a
  guess.
- Cache pulls per ASIN under `data/cache/`; never pull the same ASIN twice in
  one run.
