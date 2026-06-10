---
name: title-and-bullets
description: Write an Amazon listing title, five benefit-led bullets, and backend search terms for a chosen product — every claim traced to the user-confirmed product spec or a Stage 1 finding. Used by listing-agent in Stage 2.
---

# title-and-bullets

Turn a validated product opportunity into compliant, evidence-backed listing
copy: title, five bullets, backend search terms.

## Inputs
- `data/listings/<slug>/spec.json` — user-confirmed product spec (**required**)
- `data/reports/<niche>-<date>.json` — the chosen candidate's Stage 1 entry
- `data/products.json` — review-gap themes and improvement angles
- `data/painpoints.json` — Reddit pain language, if Stage 1 captured any
- `data/competitors.json` — competitor titles and attributes
- `config/listing-rules.json` — style limits and prohibited claims

## Procedure
1. **Spec gate.** If `spec.json` is missing or lacks a field a claim needs,
   STOP and report what's missing. Copy may only claim what the spec states.
2. **Keyword pool.** Build it from evidence on hand: terms recurring across
   competitor titles in `data/competitors.json`, plus the vocabulary buyers
   use in review themes and pain points. The free stack has **no
   search-volume tool** — never attach volume numbers to keywords.
3. **Title** per `listing-rules.json -> title`: brand + product type + key
   spec attributes + the top differentiator, inside the char limit.
4. **Five bullets** per `-> bullets`: each leads with a benefit, is backed by
   a concrete spec feature, and — where one exists — answers a named review
   complaint theme or Reddit pain point.
5. **Backend search terms** from the remaining keyword pool, inside the byte
   cap and its rules (no words already used, no brands, no both-forms).
6. **Compliance pass.** Check every line against `prohibited_claims` and the
   style rules. Anything that fails is flagged and rewritten or dropped —
   `needs_proof_on_file` claims stay only if the user confirms proof exists.
7. **Evidence map.** For the title's differentiator and each bullet, record
   the spec field or Stage 1 finding it traces to.

## Output
Write into `data/listings/<slug>/listing.json` under `"copy"`:

```json
{
  "title": "string",
  "title_char_count": 0,
  "bullets": [
    {
      "text": "string",
      "benefit": "string",
      "evidence": "spec.<field> | review_gap:<theme> | painpoint:<url>"
    }
  ],
  "backend_search_terms": "string",
  "backend_byte_count": 0,
  "keyword_pool": [
    { "term": "string", "source": "competitor_titles | review_language | painpoints" }
  ],
  "compliance": { "passed": true, "flags": ["string"] },
  "generated_at": "ISO-8601"
}
```

Return the title and bullets to the orchestrator for the assembled report.

## Guardrails
- Every claim traces to `spec.json` or a Stage 1 finding — no invented
  materials, measurements, certifications, counts, or outcomes.
- No keyword search volumes, ever — the free stack has no source for them.
- Compliance flags are surfaced to the user, never silently dropped.
- This is draft copy for human review — not publish-ready until the user
  signs off.
