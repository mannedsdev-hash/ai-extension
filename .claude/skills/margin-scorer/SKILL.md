---
name: margin-scorer
description: Compute Amazon FBA unit economics for a target product — net margin, breakeven price, recommended sell price — using a config-driven fee schedule. Pure calculation, no external tools. Used by product-research-agent in Stage 1.
---

# margin-scorer

Work out whether a product can actually make money. Pure calculation — no
network, no MCP. The fee schedule lives in `config/amazon-fees.json` and the
thresholds in `config/thresholds.json`, both editable.

## Cost model

```
landed_cost            COGS + inbound shipping + duties (per unit)
+ amazon_referral_fee  category % of sell price (min fee floor applied)
+ fba_fulfillment_fee  by size/weight tier
+ est_ad_cost          target ACoS x sell price
+ overhead             storage + returns allowance, % of sell price
= total_cost_per_unit
net_margin = (sell_price - total_cost_per_unit) / sell_price
```

## How to run

Run the bundled calculator with the Bash tool:

```
python3 .claude/skills/margin-scorer/calc.py \
  --sell-price 24.99 --landed-cost 6.50 \
  --category kitchen --fba-tier large_standard_8to12oz
```

- `--sell-price` — from `pricing-competitor-analyst` (the niche entry price).
- `--landed-cost` — supplier quote, or a stated assumption (flag it as an
  assumption to the user if no real quote exists).
- `--category` — referral-fee key; see `referral_fee_rate.by_category` in
  `config/amazon-fees.json`. Defaults to 15% if omitted.
- `--fba-tier` — size-tier id; see `fba_fulfillment_fee.tiers`. Defaults to
  `large_standard_8to12oz` if omitted.
- `--target-acos`, `--overhead-rate` — optional; default from `thresholds.json`.

The script prints a JSON object with `inputs`, `costs`, and `result`
(`net_margin_pct`, `breakeven_price`, `recommended_sell_price`,
`below_threshold`).

## Output

Capture the JSON and merge a `margin` block into the candidate in
`data/products.json`. `below_threshold` is true when net margin is under
`margin.minimum_net_margin` (default 25%).

## Guardrails
- Never hardcode fees in prose — they come only from the config files.
- If landed cost is an assumption rather than a real supplier quote, label it
  as such in the report; landed cost dominates the result.
- If a product needs an unrealistic sell price to clear the margin threshold,
  say so plainly.
