# E-commerce Research & Ops Agent System

A multi-agent system for the Amazon e-commerce pipeline. See [PLAN.md](PLAN.md)
for the original full build brief.

**Status:** Stage 1 (`product-research-agent`) is built, on the **free stack**
(Apify only). Stages 2-5 are mapped in PLAN.md but not yet built.

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

## Layout

```
.claude/
  agents/product-research-agent.md   Stage 1 subagent
  skills/                            the six Stage 1 skills
    reddit-pain-miner/        (idle until Reddit is added)
    demand-competition-analyst/   uses Apify
    review-gap-analyst/           uses Apify
    pricing-competitor-analyst/   uses Apify
    margin-scorer/        SKILL.md + calc.py (works offline, no keys)
    opportunity-scorer/
config/
  amazon-fees.json         editable Amazon/FBA fee schedule
  scoring-rubric.json      opportunity-scorer weights + verdict thresholds
  thresholds.json          margin threshold, saturation rules, run/spend caps
data/
  products.json / competitors.json / painpoints.json   shared data store
  reports/                 generated opportunity reports
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
- **Stages 2-5 are not built** — only mapped in PLAN.md.
- Fee numbers in `config/amazon-fees.json` are approximate and dated; verify
  against Amazon's current schedule before any money decision.
