---
name: aplus-copy
description: Plan and write Amazon A+ content modules — brand story, feature modules, comparison chart, FAQ — with copy and image directions, claims limited to those already cleared for the listing. Used by listing-agent in Stage 2.
---

# aplus-copy

Design the A+ (Enhanced Brand Content) section: a module-by-module plan with
final copy and image directions for each.

## Inputs
- `data/listings/<slug>/spec.json` — user-confirmed product spec (**required**)
- `data/listings/<slug>/listing.json` -> `copy` — the cleared title/bullets
  (run `title-and-bullets` first; its claims are the ceiling for A+ claims)
- `data/products.json` — review-gap themes (what standard products get wrong)
- `data/painpoints.json` — buyer pain language, if present
- `config/listing-rules.json` -> `aplus` — module rules and limits

## Procedure
1. **Spec + copy gate.** If `spec.json` or a cleared `copy` block is missing,
   STOP and report it. A+ may not introduce claims the bullets didn't clear.
2. **Module plan.** Pick modules from
   `listing-rules.json -> aplus.recommended_module_sequence`, capped at
   `max_modules`. Drop any module the evidence can't fill — fewer strong
   modules beat padded ones.
3. **Brand story banner.** One short paragraph: who the product is for and
   the single biggest pain it solves, in the buyers' own vocabulary (cite the
   review theme or pain point it comes from).
4. **Feature modules.** One per differentiator, reusing bullet evidence:
   headline, 2-3 sentence body, and an image direction for the designer.
5. **Comparison chart.** Rows = the top review-gap themes; columns = this
   product vs an unbranded "standard" alternative. Check-marks only where the
   spec backs the cell. Never name a competitor brand.
6. **Specs / FAQ module.** Specs straight from `spec.json`; FAQ answers the
   confusions found in review themes (sizing, instructions, compatibility).
7. **Compliance pass** per `aplus.rules` and the same `prohibited_claims`
   gate as the bullets. Provide alt text for every image's overlay text.

## Output
Write into `data/listings/<slug>/listing.json` under `"aplus"`:

```json
{
  "modules": [
    {
      "type": "brand_story_banner | feature_trio | comparison_chart | lifestyle_banner | specs_or_faq",
      "headline": "string",
      "body_copy": "string",
      "image_direction": "string for the designer",
      "image_alt_text": "string",
      "evidence": "spec.<field> | review_gap:<theme> | painpoint:<url>"
    }
  ],
  "comparison_chart": {
    "columns": ["This product", "Standard alternative"],
    "rows": [
      { "criterion": "string (from a review-gap theme)", "this_product": true, "standard": false, "evidence": "string" }
    ]
  },
  "compliance": { "passed": true, "flags": ["string"] },
  "generated_at": "ISO-8601"
}
```

Return the module list to the orchestrator for the assembled report.

## Guardrails
- A+ claims are a subset of cleared bullet claims — nothing new gets asserted
  here, and every cell/headline carries its evidence reference.
- No competitor names or disparagement; comparison is against an unbranded
  standard alternative only.
- No pricing, promotion, shipping, or guarantee language in any module.
- Draft for human review — the user approves before anything is uploaded.
