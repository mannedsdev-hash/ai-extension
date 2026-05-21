---
name: opportunity-scorer
description: Combine the Stage 1 analyses into a single 0-100 opportunity score with a go/watch/no-go verdict and a cited rationale. Used by product-research-agent in Stage 1.
---

# opportunity-scorer

Synthesize demand, competition, margin, differentiation, and operational
analyses into one ranked verdict per product opportunity.

> Note: the build brief refers to an "existing `market-brainstorm` skill" for
> the synthesis layer. No such skill exists in this repo. Its intent —
> evidence-first, data-backed reasoning with no fabrication — is built into
> the rules below.

## Inputs
- `data/painpoints.json` — Reddit pain points
- `data/competitors.json` — Keepa demand & competition data
- `data/products.json` staging — review gaps, pricing, margin blocks
- `config/scoring-rubric.json` — weights and verdict thresholds

## Procedure
1. For each candidate product, score five sub-scores 0-100 using the guidance
   in `scoring-rubric.json` -> `sub_score_guidance`:
   - **demand_and_trend** — from BSR level and trend
   - **competition_saturation_inverted** — high when NOT saturated
   - **margin_health** — from margin-scorer net margin (>=40% near 100, at the
     minimum threshold near 50, below threshold near 0)
   - **differentiation_potential** — from review gaps + Reddit pains
   - **operational_simplicity** — size, weight, fragility, regulatory load
2. Final score = weighted average using `weights` from the rubric.
3. Verdict from `verdict_thresholds`: `>= go` -> **go**, `>= watch` ->
   **watch**, else **no-go**.
4. Write a rationale: one or two sentences per sub-score, each citing the
   specific data point behind it (a Reddit URL, an ASIN's BSR, the net margin
   number). No sub-score may be asserted without a source.

## Reasoning rules (evidence-first synthesis)
- Every sub-score cites the tool-derived data behind it. A score with no data
  is not a score — mark that dimension `insufficient data` and lower
  confidence rather than guessing.
- Do not let one strong signal mask a fatal flaw: a sub-score at or near 0
  (e.g. negative margin) caps the verdict at **no-go** regardless of total.
- State confidence (`high` / `medium` / `low`) based on how much of the data
  was actually retrieved vs. missing.

## Output
Write the final report to `data/reports/`:
- `data/reports/<niche>-<date>.json` — structured, one entry per candidate
- `data/reports/<niche>-<date>.md` — human-readable ranked report

JSON entry shape:

```json
{
  "product": "string",
  "niche": "string",
  "score": 0,
  "verdict": "go|watch|no-go",
  "confidence": "high|medium|low",
  "sub_scores": {
    "demand_and_trend": 0,
    "competition_saturation_inverted": 0,
    "margin_health": 0,
    "differentiation_potential": 0,
    "operational_simplicity": 0
  },
  "rationale": { "demand_and_trend": "string with citation", "...": "..." },
  "generated_at": "ISO-8601"
}
```

## Guardrails
- No fabricated numbers, scores, or citations. Trace every claim to a tool
  call in the data store.
- Rank candidates by score; show the rubric weights so the score is auditable.
- This is research output only — recommend human review before any sourcing
  or spend decision.
