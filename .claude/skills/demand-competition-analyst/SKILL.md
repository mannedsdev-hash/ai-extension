---
name: demand-competition-analyst
description: Measure Amazon demand and competitive saturation for a niche using Apify — current sales rank (BSR), price, offer/seller counts, review counts. Used by product-research-agent in Stage 1.
---

# demand-competition-analyst

Quantify how much a niche sells and how crowded it is, from current Amazon data.

> **Free-stack note:** this skill uses Apify, not Keepa. Apify returns a
> *current snapshot* — today's rank, price, review counts. It does **not**
> provide historical trends. Trend fields are reported as `unavailable`
> unless a Keepa key is added later.

## Tools
- Apify MCP (server `apify`). Run the `amazon-bestsellers-scraper` actor for
  category rankings and the `amazon-scraper` actor (product-detail mode) for
  individual ASINs.
- Discover exact actor/tool names from the connected server at runtime — do
  not assume them.
- If the server is not connected, STOP and report it. Never estimate figures
  without data.

## Procedure
1. Resolve the niche to a category and candidate ASINs via
   `amazon-bestsellers-scraper`. Cap at `run_limits.max_asins_per_run` in
   `config/thresholds.json`.
2. For each ASIN pull from `amazon-scraper`:
   - current Best Sellers Rank (if shown on the product page)
   - current price
   - number of offers / distinct sellers (if shown)
   - total review count and average rating
3. `bsr_trend` and `est_monthly_sales` are not available on the free stack —
   record them as `"unavailable"` / `null`. Use current BSR as a rough demand
   proxy and label it as a snapshot.
4. Classify saturation: count listings with review count >=
   `saturation.entrenched_review_count`. More than
   `saturation.max_entrenched_sellers` such listings, or total offers above
   `saturation.crowded_total_offers`, means crowded.
5. Flag a niche `avoid` when saturation is high.

## Output
Update `data/competitors.json` (a JSON array). One object per ASIN:

```json
{
  "asin": "string",
  "niche": "string",
  "title": "string",
  "bsr": 0,
  "bsr_trend": "unavailable",
  "est_monthly_sales": null,
  "price": { "current": 0 },
  "offers": 0,
  "sellers": 0,
  "review_count": 0,
  "rating": 0,
  "pulled_at": "ISO-8601",
  "source": "apify"
}
```

Return a niche-level summary: saturation verdict and the entrenched-seller
count, with the numbers behind it. State explicitly that demand trend is
unavailable on the free stack.

## Guardrails
- Use `null` for any metric Apify does not return — never fill a gap with a
  guess.
- Cache pulls per ASIN under `data/cache/`; never pull the same ASIN twice in
  one run. Apify is pay-per-result and the free credits are limited — respect
  `run_limits`.
