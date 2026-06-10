---
name: image-brief
description: Produce a photographer/designer brief for the Amazon image stack — shot list with purpose, composition, overlay text, and the Stage 1 evidence each shot answers. Used by listing-agent in Stage 2.
---

# image-brief

Write the brief a photographer or designer can shoot from: one entry per
image slot, each tied to a reason it earns its place.

## Inputs
- `data/listings/<slug>/spec.json` — user-confirmed product spec (**required**)
- `data/listings/<slug>/listing.json` -> `copy` — cleared title/bullets
  (overlay text may only restate cleared claims)
- `data/products.json` — review-gap themes worth answering visually
- `data/painpoints.json` — buyer pain language, if present
- `config/listing-rules.json` -> `images` — slot count, main-image rules,
  resolution floor, recommended shot types

## Procedure
1. **Spec + copy gate.** If `spec.json` or cleared `copy` is missing, STOP
   and report it. Overlay text cannot introduce uncleared claims.
2. **Main image** first, exactly per `images.main_image_rules` — white
   background, >=85% frame fill, no text or props, only what's in the box.
3. **Allocate remaining slots** from `recommended_shot_types`, prioritized by
   evidence: the top review-gap themes and pain points get answered first
   (e.g. a durability complaint -> a feature_closeup of the reinforced part;
   a sizing complaint -> a scale_or_dimensions shot with real measurements
   from the spec).
4. **Per shot, specify:** purpose, composition notes, props/setting, overlay
   text (verbatim, reusing cleared copy), and the evidence reference it
   answers. Mark which shots need photography vs graphic design.
5. **Technical footer:** resolution floor, file format, color profile, and a
   reminder that measurements shown must match `spec.json` exactly.

## Output
Write into `data/listings/<slug>/listing.json` under `"image_brief"`:

```json
{
  "shots": [
    {
      "slot": 1,
      "type": "main_white | benefit_callout_infographic | lifestyle_in_use | scale_or_dimensions | feature_closeup | how_to_or_comparison | packaging_or_whats_in_box",
      "purpose": "string",
      "composition": "string for the photographer/designer",
      "overlay_text": "string or null (verbatim from cleared copy)",
      "production": "photo | design | photo+design",
      "evidence": "spec.<field> | review_gap:<theme> | painpoint:<url> | amazon_rule"
    }
  ],
  "technical": { "min_resolution_px": 1600, "format": "JPEG/PNG", "color": "sRGB" },
  "compliance": { "passed": true, "flags": ["string"] },
  "generated_at": "ISO-8601"
}
```

Return the shot list summary to the orchestrator for the assembled report.

## Guardrails
- Overlay text and any depicted measurements come verbatim from cleared copy
  and `spec.json` — the brief never asks the designer to depict an uncleared
  claim or a feature the product doesn't have.
- Main-image rules are non-negotiable Amazon requirements; flag any user
  request that conflicts with them instead of writing it into the brief.
- Lifestyle shots show plausible real use of the actual product — no
  depictions implying outcomes the copy couldn't claim.
- Draft for human review before any production spend.
