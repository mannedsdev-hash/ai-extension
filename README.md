# E-commerce Research & Ops Agent System

A multi-agent system for the Amazon e-commerce pipeline. See [PLAN.md](PLAN.md)
for the full build brief.

**Status:** Stage 1 (`product-research-agent`) is built and scaffolded.
Stages 2-5 are mapped in PLAN.md but not yet built.

## Layout

```
.claude/
  agents/product-research-agent.md   Stage 1 subagent
  skills/                            the six Stage 1 skills
    reddit-pain-miner/
    demand-competition-analyst/
    review-gap-analyst/
    pricing-competitor-analyst/
    margin-scorer/        SKILL.md + calc.py (works offline)
    opportunity-scorer/
config/
  amazon-fees.json         editable Amazon/FBA fee schedule
  scoring-rubric.json      opportunity-scorer weights + verdict thresholds
  thresholds.json          margin threshold, saturation rules, run/spend caps
data/
  products.json            candidate products + scores
  competitors.json         competitor ASINs + pulled data
  painpoints.json          Reddit findings with citations
  reports/                 generated opportunity reports
  cache/                   raw tool output (gitignored)
.mcp.json.example          MCP server config template
```

## Setup — required before running the research agent

The research skills depend on three MCP servers. They are **not** auto-connected;
you must configure them with your own API keys.

### 1. Get keys / accounts
- **Keepa** — paid subscription -> `KEEPA_API_KEY`
- **Apify** — free account -> `APIFY_TOKEN` (free monthly credits, then pay-per-result)
- **Reddit research MCP** — use the hosted `king-of-the-grackles/reddit-research-mcp`
  and note its endpoint URL, or self-host it.

### 2. Set environment variables
```sh
export KEEPA_API_KEY="..."
export APIFY_TOKEN="..."
export REDDIT_RESEARCH_MCP_URL="https://..."   # endpoint of the reddit-research MCP
```

### 3. Create the MCP config
```sh
cp .mcp.json.example .mcp.json
```
`.mcp.json` is gitignored (it is local setup). Adjust the `keepa` entry to match
whichever Keepa MCP you chose:
- `cosjef/keepa_MCP` — clone it and set `command`/`args` to its documented start command.
- `BWB03/keepa-adapter` — install the `.mcpb` and reference it instead.

### 4. Verify the servers
Restart Claude Code, run `/mcp`, and confirm `reddit-research`, `keepa`, and
`apify` are connected. Do one small (~10-row) test pull per server before a
full run — per PLAN.md §5 step 2.

## Running Stage 1

Once the MCP servers are connected, ask Claude Code:

> Use the product-research-agent on the niche: `<your niche>`

It runs the six skills in order and writes a ranked opportunity report to
`data/reports/`.

## Margin scorer (works offline, no keys)

The margin calculator is pure math and runs without any MCP:

```sh
python3 .claude/skills/margin-scorer/calc.py \
  --sell-price 24.99 --landed-cost 6.50 \
  --category kitchen --fba-tier large_standard_8to12oz
```

Category keys and FBA size-tier ids are listed in `config/amazon-fees.json`.

## Known gaps / what still needs you

- **MCP servers are not connected** in this repo — they need your keys
  (step 1-3 above). Until then, `reddit-pain-miner`, `demand-competition-analyst`,
  `review-gap-analyst`, and `pricing-competitor-analyst` cannot pull live data.
- **No live test pull has been verified** (PLAN.md §5 step 2) — do this after
  setup. Only `margin-scorer` has been verified, since it needs no network.
- **Scoring not yet validated** against known-good/known-bad products
  (PLAN.md §5 step 4) — tune `config/scoring-rubric.json` after the first runs.
- The brief's §3.6 references an "existing `market-brainstorm` skill"; no such
  skill exists in this repo. Its evidence-first synthesis intent is built into
  `opportunity-scorer` instead.
- **Stages 2-5 are not built** — only mapped in PLAN.md.
- Fee numbers in `config/amazon-fees.json` are approximate and dated; verify
  against Amazon's current schedule before any money decision.
