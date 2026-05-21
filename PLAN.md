# E-commerce Research & Ops Agent System — Build Brief

**Goal:** A multi-agent system that runs the full Amazon e-commerce pipeline —
from finding a product to retaining the buyer — leveraging existing open-source
MCP servers and skills instead of writing scrapers from scratch.

---

## 0. How to use this document

Build this as a set of **Claude Code subagents + skills**, each wired to **real
MCP servers** (§2). Build **Stage 1 first** and prove it works on one real
niche before expanding. Stages 2-5 plug into the same orchestrator later.

**Operating principles (non-negotiable):**
- Prefer **official APIs** (Keepa, Reddit API) for reliable structured data.
  Use **Apify MCP** for breadth and as a fallback.
- **Never fabricate data.** Every claim in a report traces to a tool call. If
  a tool returns nothing, say so.
- **Public data only.** Respect each platform's Terms of Service. No
  login-walled scraping.
- **Cache aggressively** to limit API tokens / Apify credits. Don't re-pull
  the same ASIN twice in a run.
- **Human-in-the-loop** before any money decision (sourcing, ad spend,
  purchase).

---

## 1. Architecture

```
Orchestrator (root Claude Code agent)
│
├── Stage 1: product-research-agent      <- BUILD FIRST
├── Stage 2: listing-agent
├── Stage 3: promote-agent
├── Stage 4: sell-ops-agent
└── Stage 5: retain-agent

Shared local data store: /data
  - products.json        candidate products + scores
  - competitors.json     competitor ASINs + pulled data
  - painpoints.json      Reddit findings with citations
  - reports/             generated opportunity reports
```

Each stage is a **subagent** with its own system prompt and a small set of
**skills**. Subagents pass structured data through the shared store, never
through prose.

---

## 2. Tool / MCP layer — connect these first

| Need | Tool / Repo | Connect via | Key / cost |
|---|---|---|---|
| Reddit pain-point mining | `king-of-the-grackles/reddit-research-mcp` (semantic, cited) | hosted MCP | free / low |
| Reddit (official API, read-only) | `GeLi2001/reddit-mcp` | clone + run | Reddit app client id/secret (free) |
| Amazon price / BSR / sales-rank history | Keepa — `cosjef/keepa_MCP` or `BWB03/keepa-adapter` (.mcpb) | MCP / .mcpb | `KEEPA_API_KEY` (paid Keepa sub) |
| Amazon search, reviews, bestsellers, storefronts | Apify MCP `https://mcp.apify.com` (actors: `amazon-scraper`, `amazon-reviews-extractor`, `amazon-bestsellers-scraper`, storefront, `multi-scraper-mcp`) | hosted MCP | `APIFY_TOKEN` (free credits, then ~$0.75/1K) |
| All-in-one Amazon bundle (optional) | `ignitabull/amazon-research-mcp` | clone + run | multiple API keys |
| Margin / fee math | none — pure calc skill (§3.5) | local | none |
| General web | Claude Code built-in web search, or Apify web-search actor | built-in / MCP | — |

**Recommended minimal stack to start:** Reddit research MCP + Keepa MCP +
Apify MCP. That covers demand, competition, pricing, reviews, and pain points.

**Verify before relying:** check each repo's last commit date and that its
tool schema still matches before wiring it in. Pin versions where possible.

---

## 3. Stage 1 — Product & Market Research (FULL SPEC)

**Subagent:** `product-research-agent`
**Input:** a niche, category, or seed keyword.
**Output:** a ranked list of product opportunities, each with a 0-100 score and
a go/no-go call, written to `/data/reports/` as markdown and JSON.

Six skills:

### 3.1 `reddit-pain-miner`
Uses the Reddit MCP. Searches relevant subreddits for complaints, "I wish there
was", "why is there no", recommendation threads, frustration language. Output:
ranked pain points with frequency, sentiment, and **citation URLs**. No
invented quotes.

### 3.2 `demand-competition-analyst`
Uses Keepa. For the niche and top ASINs: BSR and trend, estimated monthly
sales, price history, offers/sellers count, review counts. Flags **demand
trend** and **saturation**.

### 3.3 `review-gap-analyst`
Uses Apify reviews actor on top 5-10 competitor ASINs. Pulls 1-3 star reviews.
Clusters recurring complaints into concrete **product improvement angles**.

### 3.4 `pricing-competitor-analyst`
Uses Keepa + Apify storefront actor. Competitor price band, Buy Box price,
discount/coupon patterns, who holds the Buy Box and why.

### 3.5 `margin-scorer` (pure calculation — no external tool)
Computes unit economics: landed cost + referral fee + FBA fee + ad cost +
overhead = total cost; net margin = (price - total cost) / price. Outputs net
margin %, breakeven price, recommended sell price, and a below-threshold flag
(default 25%). Fee schedule lives in editable config.

### 3.6 `opportunity-scorer`
Combines the five analyses into a single **0-100 score**. Rubric: demand &
trend 25, competition (inverted) 20, margin 20, differentiation 20, operational
simplicity 15. Outputs score, go/watch/no-go verdict, and a cited rationale.

---

## 4. Stages 2-5 (mapped — build after Stage 1 is proven)

- **Stage 2 — `listing-agent`:** `title-and-bullets`, `aplus-copy`, `image-brief`.
- **Stage 3 — `promote-agent`:** `ppc-plan`, `repricing-rules`, `ugc-video-brief`.
- **Stage 4 — `sell-ops-agent`:** `inventory-forecast`, `fba-shipment-checklist`, `buyer-message-responder`.
- **Stage 5 — `retain-agent`:** `review-monitor`, `insert-card-designer`, `retention-email-writer`, `ltv-cac-tracker`.

---

## 5. Build sequence

1. Scaffold the repo, the shared `/data` store, and `config/` for fee schedules
   and thresholds.
2. Connect MCPs: Reddit research, Keepa, Apify. Confirm each with a 10-row test
   pull.
3. Build Stage 1: the `product-research-agent` subagent + six skills. Test
   end-to-end on ONE real niche.
4. Validate scoring against a known-good and a known-bad product.
5. Build Stages 2-5 subagents.
6. Build the orchestrator that runs a chosen product through all five stages.

---

## 6. Keys & accounts

- **Keepa API** — paid subscription, gives `KEEPA_API_KEY`.
- **Reddit API app** — free, gives client id/secret (or use the hosted MCP).
- **Apify token** — `APIFY_TOKEN`. Free monthly credits, then pay-per-result.
- **(Stage 3, later)** HeyGen / Arcads for AI-avatar video — separate keys.

---

## Guardrails (carry into every stage)

- Public data only; respect platform ToS; prefer official APIs.
- No fabricated numbers, quotes, or citations — ever.
- Cache results; cap spend per run; log every external call.
- Human review before sourcing, ad spend, or buying inventory.
- Keep the fee schedule and scoring rubric in editable config, not hardcoded.
