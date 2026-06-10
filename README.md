# E-commerce Research & Ops Agent System

An AI + data driven system for the full Amazon seller flow. Two layers:

- **Deterministic engine** (`engine/`) — data pulls, math, scoring, ledger.
  Reproducible, budget-capped, testable. AI never does arithmetic.
- **AI seams + skills** (`.claude/`) — judgment steps (concept expansion,
  whitespace synthesis, compliance triage, rationale, copywriting) done by
  Claude through named, ledgered seams. Data never gets invented.

[PHASES.md](PHASES.md) is the master spec: all 8 phases (research → keywords
→ sourcing → import → listing → launch → PPC → operations) at module-level
granularity. [PLAN.md](PLAN.md) is the original Stage 1-5 brief it grew from.

**Status:** Stage 1 (`product-research-agent`) and Stage 2 (`listing-agent`)
are built. Stage 1 runs on the **free stack** (Apify only); Stage 2 needs no
external server at all. Stages 3-5 are mapped in PLAN.md but not yet built.

## Free-stack setup (current build)

The brief specified three data sources — Reddit, Keepa, Apify. Keepa has no
free API tier, so this build runs on the **free stack**:

| Source | Cost | Status | Powers |
|---|---|---|---|
| **Apify** | free credits | ✅ connected | review-gap, demand-competition, pricing-competitor |
| Reddit | free | ⏳ skipped — set up later | reddit-pain-miner |
| Keepa | paid only | ❌ skipped | (would add historical price/rank trends) |

The two skills that originally used Keepa (`demand-competition-analyst`,
`pricing-competitor-analyst`) were **re-pointed to Apify**. Tradeoff: you get
*current* price/rank/review data, not *historical trends*.

## Phase 1 engine (works now, no keys)

```sh
python3 run_engine.py --demo                       # mock connector, reproducible
python3 run_engine.py --demo --connector apify     # REAL Amazon data (needs APIFY_TOKEN)
python3 run_engine.py --seeds "spice rack" --categories kitchen \
    --persona whitespace_scout --ai claude_session  # queue AI seams for Claude
```

**Real data:** put `APIFY_TOKEN=...` in `.env` (gitignored) and use
`--connector apify` (or the Data-source dropdown in the dashboard). Each
search is one Apify actor run — slow and credit-metered, so the apify
connector gets a tighter call cap (`config/discovery.json -> apify`) and a
24h file cache (`data/cache/engine/`). Fields an actor doesn't return show
up as `no_bsr_data` / `no_weight_data` marks — never invented numbers. Add
`REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` to `.env` (free script app at
reddit.com/prefs/apps) and SocialScout's reddit feed turns real too. On
Claude Code web, the environment's network policy must allow
`api.apify.com`, `completion.amazon.com`, `www.reddit.com`, `oauth.reddit.com`.

Scouts (custom/proven/social) → SearchResolver fan-out → rough_filter →
economics → persona-weighted fusion → 🟢/🟡/🔵 lanes → `data/runs/shortlist.json`
plus a full decision ledger (`data/runs/<run id>.jsonl`). Every paid call is
budget-governed; every drop has a ledgered reason. Personas and thresholds
live in `config/personas.json` / `config/discovery.json`. The mock connector
is deterministic fake data — wire Apify for real pulls (PHASES.md, Phase 1).

### Dashboard (the Phase 1 frontend)

```sh
python3 serve.py        # -> http://localhost:8013
```

Stdlib server + vanilla JS, no build step. Run the engine from the browser
(seeds, categories, persona, price band, proven mode, AI backend), then
explore: guardrail cards G1-G5 with live budget bars, lane filters, the
ranked table, and a per-candidate drawer (sub-score bars, fee-by-fee
economics, market snapshot, provenance — which query found it). The Ledger
tab shows every drop with its reason and every AI seam call with the backend
that answered it. API: `GET /api/config · /api/shortlist · /api/ledger`,
`POST /api/run`.

## Layout

```
PHASES.md                  8-phase master spec (module-level granularity)
engine/                    Phase 1 Discover engine (stdlib-only Python)
  models.py · scouts.py · discovery.py · filters.py · economics.py ·
  fusion.py · budget.py · ledger.py · ai.py · connectors/ (mock built)
run_engine.py              Phase 1 CLI
.claude/
  agents/product-research-agent.md   Stage 1 subagent
  agents/listing-agent.md            Stage 2 subagent
  skills/                            Stage 1 + Stage 2 skills
    reddit-pain-miner/        (idle until Reddit is added)
    demand-competition-analyst/   uses Apify
    review-gap-analyst/           uses Apify
    pricing-competitor-analyst/   uses Apify
    margin-scorer/        SKILL.md + calc.py (works offline, no keys)
    opportunity-scorer/
    title-and-bullets/    Stage 2 — listing copy (offline, no keys)
    aplus-copy/           Stage 2 — A+ content plan (offline, no keys)
    image-brief/          Stage 2 — photo/design brief (offline, no keys)
config/
  amazon-fees.json         editable Amazon/FBA fee schedule
  scoring-rubric.json      opportunity-scorer weights + verdict thresholds
  thresholds.json          margin threshold, saturation rules, run/spend caps
  listing-rules.json       Amazon listing style limits + prohibited claims
data/
  products.json / competitors.json / painpoints.json   shared data store
  reports/                 generated opportunity reports
  listings/                Stage 2 listing packages, one folder per product
  runs/                    engine ledgers + shortlist.json (gitignored — your flywheel)
  cache/                   raw tool output (gitignored)
.mcp.json.example          MCP server config template (committed)
.mcp.json                  live MCP config — holds the Apify token (gitignored)
.env                       API keys (gitignored)
```

## How the Apify key is wired

- `.env` holds `APIFY_TOKEN` (gitignored — never committed).
- `.mcp.json` holds the live Apify MCP server config with the token inline
  (also gitignored — never committed).
- `.mcp.json.example` is the committed template, with a `${APIFY_TOKEN}`
  placeholder instead of the real value.

**To activate Apify:** MCP servers load when a Claude Code session starts, so
start a **new session** (or restart) after `.mcp.json` is in place, then run
`/mcp` to confirm `apify` shows as connected. Outbound access to
`mcp.apify.com` must be allowed by the environment's network policy.

## Running Stage 1

Once `apify` is connected, ask Claude Code:

> Use the product-research-agent on the niche: `<your niche>`

It runs the available skills in order and writes a ranked opportunity report
to `data/reports/`. `reddit-pain-miner` is skipped until Reddit is added.

## Running Stage 2 (works now, no keys)

Stage 2 turns ONE validated opportunity into a full listing package and runs
fully offline. Once a Stage 1 report exists in `data/reports/`, ask:

> Use the listing-agent on `<product>` from the latest report

It first collects a product spec from you — copy may only claim what the spec
states — then writes the title + bullets + backend search terms, an A+
content plan, and a photographer/designer image brief to
`data/listings/<product>/` (`spec.json`, `listing.json`, `listing.md`).

## Margin scorer (works now, no keys)

The margin calculator is pure math and needs no MCP server:

```sh
python3 .claude/skills/margin-scorer/calc.py \
  --sell-price 24.99 --landed-cost 6.50 \
  --category kitchen --fba-tier large_standard_8to12oz
```

Category keys and FBA size-tier ids are listed in `config/amazon-fees.json`.

## Web preview page (`docs/index.html`)

A single self-contained page with five tabs: Research, Marketing, Create,
Margin Calculator, and Landing Page. No build step, no backend, no
dependencies.

- The **Margin Calculator** is fully functional (the same math as `calc.py`).
- Research, Marketing, and Landing tabs show **sample data**, clearly labelled
  — live generation runs through the Claude Code agent, not a static page.

Open it locally by opening `docs/index.html` in a browser, or deploy it free
on **GitHub Pages**:

1. On GitHub, open the repo → **Settings** → **Pages**.
2. Under **Build and deployment**, Source = **Deploy from a branch**.
3. Branch = `claude/confident-euler-cg3XG`, folder = **`/docs`**. Save.
4. Wait ~1 minute, refresh — the live URL appears at the top of the Pages
   settings (`https://<user>.github.io/ai-extension/`).

## Adding the skipped sources later

- **Reddit (free):** create a `script` app at `reddit.com/prefs/apps`, then
  wire a Reddit MCP server into `.mcp.json`. Re-enables `reddit-pain-miner`.
- **Keepa (paid):** subscribe at `keepa.com/#!api`, add `KEEPA_API_KEY`, wire
  a Keepa MCP server, and the two analyst skills can be switched back to Keepa
  for historical trend data.

## Known gaps

- **No live test pull verified yet** — do a small (~10-row) Apify pull after
  the session restarts, before a full run.
- **Scoring not yet validated** against known-good/known-bad products
  (PLAN.md §5 step 4) — tune `config/scoring-rubric.json` after first runs.
- With Reddit skipped, `opportunity-scorer`'s `differentiation_potential`
  sub-score leans on review gaps alone; confidence is lower for that dimension.
- The brief's §3.6 references an "existing `market-brainstorm` skill" — no such
  skill exists in this repo. Its evidence-first synthesis is built into
  `opportunity-scorer`.
- **Stages 3-5 are not built** — only mapped in PLAN.md.
- Fee numbers in `config/amazon-fees.json` are approximate and dated; verify
  against Amazon's current schedule before any money decision.
- Listing limits in `config/listing-rules.json` are likewise approximate;
  verify your category's current style guide in Seller Central before
  publishing a listing.
