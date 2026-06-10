# The 8-Phase Amazon Seller System — Granular Build Spec

Canon: the 8-stage seller flow (Product Research → Keyword Research →
Sourcing → Import → Listing → Launch → PPC → Operations). This document
specifies every phase at **module level** — files, data contracts, AI seams,
budget guards, human gates, ledger events, exit criteria. The granularity bar
is the Phase 1 engine diagram; no phase gets specced shallower than that.

## Doctrine (applies to every phase)

| Rule | Meaning |
|---|---|
| **Hybrid core** | Deterministic Python engine does data + math (cheap, reproducible, testable). AI does *judgment* only, at named seams. Never the reverse. |
| **AI seams via `AIGate`** | Every AI call goes through `engine/ai.py`. Three backends: `heuristic` (deterministic fallback — engine never blocks), `claude_session` (Claude Code session does the judgment), `anthropic_api` (optional key). Seam outputs are JSON, validated, ledgered. |
| **BudgetGovernor** | Every paid call (API, Apify, LLM tokens) passes through `engine/budget.py`. Denials are ledgered, not silent. |
| **Ledger = the moat** | Every candidate decision (keep/drop/flag, score, seam output, budget denial) appends to `data/runs/<ts>.jsonl`. Later phases and re-runs learn from it. |
| **Automation ceiling** | Amazon BSA (Mar 2026) bans browser bots on Seller Central. Connectors use **official APIs only** (SP-API, Ads API) or third-party data APIs (Apify, Keepa). 🟢 = mostly automatable, 🟡 = AI drafts / human approves, 🔴 = stays human, AI prepares the paperwork. |
| **Human gates** | 🔴 phases (3, 4, 6) and every money decision end in an explicit `HumanGate` artifact: a decision doc the human signs (recorded in the ledger) before the pipeline proceeds. |
| **Compliance = MARK, not drop** | Filters never silently discard; they tag (`gated_category`, `cert_needed`, `meltable`…) and let scoring + humans decide. |

Connector reality per stack tier: `mock` (built, deterministic, seeded) →
`apify` (free credits) → `sp-api`/`keepa`/`helium10` (paid, later). The engine
is connector-agnostic; tiers swap in `config/discovery.json`.

---

## Phase 1 — Product Research (Discover) 🟢 — **BUILT: `engine/`**

Improved version of the reference diagram. Same skeleton, three upgrades:
AI seams, provenance on every record, config-not-code thresholds.

```
INPUT — RunContext (engine/models.py)
  seeds · categories · asin_seeds · exclude_terms · persona · price band · budget caps
        │
        ├──────────────── WAVE 1 — SCOUTS (engine/scouts.py) ── 💰 BudgetGovernor (engine/budget.py)
        ▼                          ▼                          ▼
  📝 CustomScout            📊 ProvenScout              📱 SocialScout
  seller's own ideas →      on-Amazon movers:           off-Amazon signal, 3 feeds;
  concepts; 🤖 AI SEAM      peak | growing | both       agreement = strength;
  concept_expand            (BSR trend off connector)   🤖 AI SEAM whitespace_synth
        │                          │                          │
        │            🔌 SearchResolver fan-out (engine/discovery.py)
        │            term × category → ASINs via Connector protocol
        │            (search · best_sellers · find · autocomplete)
        │            dedupe by parent_asin · provenance: which query found what
        │                          ▼
        │            🧹 rough_filter (engine/filters.py)
        │            price band / category / oversize; compliance = MARK not drop
        │            🤖 AI SEAM compliance_triage on marked items
        │            RawProduct → Candidate
        └──────────────┬───────────┴────────────┐
                       ▼ merge by asin           ▼
        💵 economics.estimate_all (engine/economics.py)
        BSR→units/mo (per-category curve) · revenue/mo · FBA fees from
        config/amazon-fees.json · margin% · fba_ready ✓/✗
                       ▼
        🧠 fusion.rank (engine/fusion.py)
        persona weights (config/personas.json) → sub-scores: velocity · buzz ·
        idea_affinity · low_competition · agreement · supply_gap
        → lane 🟢 Safe · 🟡 Early · 🔵 Whitespace   🤖 AI SEAM rank_rationale
                       ▼
        📒 Ledger (engine/ledger.py) — EVERY decision → data/runs/<ts>.jsonl
                       ▼
        CLI run_engine.py: shortlist + guardrail report (G1 budget · G2 data
        freshness · G3 compliance marks · G4 margin floor · G5 saturation)
                       ▼
        ➡️ Phase 2 input: data/runs/shortlist.json
```

**AI seams (4):** `concept_expand` (seed ideas → adjacent concepts),
`whitespace_synth` (social signals w/o Amazon match → concept candidates),
`compliance_triage` (marked candidate → risk level + what cert), `rank_rationale`
(top-N → one cited paragraph each). All optional; heuristic fallback ships.

**Exit criteria:** shortlist of ≤ `run_limits.shortlist_size` candidates, each
with economics, lane, score breakdown, provenance, and zero unexplained drops
in the ledger.

---

## Phase 2 — Keyword Research & Screen 🟢

Deep-dive each Phase 1 shortlist candidate. Kills or promotes.

```
INPUT: data/runs/shortlist.json  +  RunContext
        ▼
  🔑 ReverseASIN (engine/keywords/reverse.py)
  candidate ASIN + top-10 competitor ASINs → ranked keyword pull via
  connector (mock | apify actor | helium10-cerebro later)
        ▼
  🧮 KeywordLab (engine/keywords/lab.py)
  normalize → cluster by intent (🤖 AI SEAM kw_cluster: head/mid/long ·
  buyer-intent vs research) → master keyword list w/ per-cluster demand proxy
        ▼
  📐 DemandModel (engine/keywords/demand.py)
  search-volume proxies + BSR cross-check → demand_score; flags: seasonal
  (12-mo shape), trend slope, brand-dominated SERP %
        ▼
  ⚔️ CompetitionDepth (engine/keywords/depth.py)
  for top keywords: review-count distribution of page-1, share of page-1 with
  <100 reviews (entry gap), PPC bid proxy → competition_score
        ▼
  🧾 ReviewMiner (engine/keywords/reviews.py)
  1-3★ reviews of top competitors → 🤖 AI SEAM complaint_cluster →
  improvement angles w/ % share + verbatim quotes (feeds Phases 3 & 5)
        ▼
  🧠 screen.verdict (engine/screen.py)
  weighted: demand · competition · margin (Phase 1 economics) · differentiation
  → PURSUE / WATCH / KILL + rationale  → 📒 ledger
        ▼
  OUTPUT: data/runs/screened.json — survivors w/ master keyword list,
  improvement angles, verdict doc  ➡️ Phase 3
```

**Budget:** keyword pulls are the spend hog — `max_kw_pulls_per_candidate`,
cache by ASIN 7 days. **Human gate:** none (research only). **Exit:** every
verdict cites numbers; KILLs stay in ledger with reasons (flywheel).

---

## Phase 3 — Sourcing & Validate 🔴 (AI prepares, human negotiates/decides)

```
INPUT: data/runs/screened.json (PURSUE only) + improvement angles
        ▼
  📋 SpecSynth (engine/sourcing/spec.py)
  🤖 AI SEAM spec_draft: improvement angles + category norms → engineering-ish
  spec sheet (materials, dimensions, tolerances, packaging, cert list)
  → HUMAN edits/approves spec  ⛔ HumanGate#1
        ▼
  🔍 SupplierScout (engine/sourcing/scout.py)
  Alibaba/1688 data via API/export (no scraping logged-in pages): candidate
  suppliers → scorecard: years · response rate · verified · trade assurance ·
  MOQ · unit $ at 3 qty tiers
        ▼
  ✉️ RFQFactory (engine/sourcing/rfq.py)
  🤖 AI SEAM rfq_draft: spec + scorecard → personalized RFQ per supplier +
  follow-up ladder; HUMAN sends from own account  ⛔ (BSA-safe: we draft, not bot)
        ▼
  🧪 SampleMatrix (engine/sourcing/samples.py)
  quote table → landed-sample cost; sample eval checklist generated from spec
  + Phase 2 complaint clusters (test exactly what competitors fail at)
        ▼
  💵 TrueMargin (engine/sourcing/margin.py)
  quoted FOB + freight est + duty (HTS code 🤖 AI SEAM hts_suggest, human
  verifies w/ broker) + FBA fees → real margin vs Phase 1 estimate; drift > X% → re-screen
        ▼
  ⛔ HumanGate#2: GO/NO-GO sourcing doc (supplier, qty, $, margin, risks) — signed → ledger
  OUTPUT: data/sourcing/<slug>/ (spec.json · quotes.json · decision.md) ➡️ Phase 4
```

---

## Phase 4 — Import & Logistics 🔴 (AI tracks paperwork, human owns freight)

```
INPUT: signed sourcing decision
  📦 ShipmentPlanner (engine/logistics/plan.py)
  carton math from spec → FBA-compliant carton/pallet plan; FCL/LCL/air
  tradeoff table at current rate cards (config, human-updated)
  🛃 CustomsPack (engine/logistics/customs.py)
  doc checklist per HTS + origin: CI, PL, BL, cert docs; 🤖 AI SEAM doc_check
  reads supplier-sent PDFs → flags mismatches (qty, value, HTS) for human
  🚚 FreightTracker (engine/logistics/track.py)
  milestone state machine: booked→sailed→arrived→cleared→checked-in;
  human/forwarder emails parsed by 🤖 AI SEAM milestone_extract; ETA drift alerts
  🏷️ FBAInbound (engine/logistics/inbound.py)
  SP-API (official) shipment creation + label data; discrepancy reconciler
  ⛔ HumanGate#3: book freight + pay duties (human). OUTPUT: inventory live in FBA ➡️ Phases 5/6
```

---

## Phase 5 — Listing Creation 🟡 (AI drafts, human edits/approves) — *skills built; engine glue pending*

Already built as Claude-side skills: `title-and-bullets`, `aplus-copy`,
`image-brief` + `listing-agent` (claims gate via `spec.json`). Engine upgrades
to reach the bar: `engine/listing/bridge.py` feeds Phase 2 **master keyword
list** (real keywords, not vocab guesses) + Phase 3 **final spec** into those
skills; `keyword_coverage.py` scores title/bullets/backend coverage of top
clusters; `seo_lint.py` enforces `config/listing-rules.json` mechanically
(char/byte caps, banned chars/claims). ⛔ HumanGate#4: human approves copy +
images before upload (SP-API listings call or manual). 📒 listing version →
ledger (Phase 7 reads which copy ran during which ad period).

---

## Phase 6 — Launch 🔴 (stays human; AI runs the checklist and watches)

```
  🚀 LaunchPlan (engine/launch/plan.py): 30-day day-by-day plan from config
  template × category: price intro curve, Vine enrollment (30 units), coupon
  schedule, external traffic slots; 🤖 AI SEAM plan_adapt tunes to velocity
  📈 RankWatch (engine/launch/watch.py): daily keyword-rank + BSR snapshot
  (connector) vs plan; honeymoon-window alerts
  ⭐ VineTracker (engine/launch/vine.py): units enrolled / reviews landed /
  review velocity; ToS-safe only — no incentivized-review tooling, ever
  ⛔ HumanGate#5: human owns pricing changes + spend; AI proposes, never executes
  EXIT: ranking on N target keywords or plan-fail → 🤖 AI SEAM launch_postmortem → ledger
```

---

## Phase 7 — PPC / Ads 🟢 (most automatable money loop — official Ads API only)

```
  🏗️ CampaignFactory (engine/ppc/factory.py): master keyword list → auto/exact/
  phrase/broad + ASIN-targeting campaign tree; negatives pre-seeded from
  Phase 2 irrelevant clusters
  📊 SearchTermMiner (engine/ppc/miner.py): search-term reports → harvest
  winners (auto→exact), kill bleeders (spend>X, sales=0 → negative)
  🎚️ BidGovernor (engine/ppc/bids.py): rule-based bid steps toward target
  ACOS/TACOS; per-day change caps; every change ledgered + reversible
  🤖 AI SEAM ppc_review (weekly): anomaly narrative + restructure proposals —
  proposals only; BidGovernor executes rules, human approves structure changes
  ⛔ HumanGate#6: budget ceiling changes are human-only
```

---

## Phase 8 — Operations 🟢 (forecast · profit · reviews · reorder flywheel)

```
  📦 InventoryForecast (engine/ops/forecast.py): velocity (7/30/90d weighted)
  + seasonality → days-of-cover; reorder point = lead time + safety stock;
  fires REORDER event → loops to Phase 3 (qty via EOQ-ish calc)
  💰 ProfitLedger (engine/ops/profit.py): SP-API settlement reports → true
  per-SKU P&L (fees, ads from Phase 7, refunds, storage); margin drift alerts
  ⭐ ReviewOps (engine/ops/reviews.py): official Request-a-Review API timing;
  new 1-3★ → 🤖 AI SEAM review_triage: product defect (→ Phase 3 spec rev) vs
  fluke vs listing-expectation mismatch (→ Phase 5 copy fix)
  🩺 AccountHealth (engine/ops/health.py): policy/IP-complaint dashboards →
  alert; responses drafted by 🤖 AI SEAM, filed by human
  ⛔ HumanGate#7: reorder POs signed by human → re-enter Phase 3 with ledger history
```

---

## Build order & status

| # | Phase | Status | Next concrete step |
|---|---|---|---|
| 1 | Discover engine | ✅ **built** (`engine/`, mock connector) | wire `apify` connector |
| 2 | Keyword & Screen | ⬜ next up | `engine/keywords/` + screen.py |
| 5 | Listing | 🟡 skills built | bridge + keyword_coverage + seo_lint |
| 3 | Sourcing | ⬜ | SpecSynth + scorecard + RFQFactory |
| 4 | Logistics | ⬜ | ShipmentPlanner + milestone tracker |
| 6 | Launch | ⬜ | LaunchPlan + RankWatch |
| 7 | PPC | ⬜ | needs live Ads API creds to be real |
| 8 | Operations | ⬜ | forecast + profit ledger first |

Order rationale: 1→2→5 is buildable today with mock/Apify data (no seller
account needed). 3/4/6 are human-gated paperwork engines — high value, low
API risk. 7/8 need a live seller account + official API creds to be more
than scaffolding.
