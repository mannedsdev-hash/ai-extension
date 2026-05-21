---
name: reddit-pain-miner
description: Mine Reddit for buyer pain points, unmet needs, and frustration language in a given niche, with citation URLs. Used by product-research-agent in Stage 1 of the e-commerce pipeline.
---

# reddit-pain-miner

Find what buyers in a niche complain about, wish existed, or ask for — with
sources. Every finding traces to a real Reddit URL returned by a tool call.

## Tools
- Primary: the Reddit research MCP (server `reddit-research`). Use its
  search / thread-fetch tools.
- Discover the exact tool names from the connected server at runtime — do not
  assume them.
- If the server is not connected, STOP and report the missing server to the
  orchestrator. Do not substitute web search or guess.

## Procedure
1. From the niche, derive 6-10 search angles: the niche term itself plus
   complaint patterns — "I wish there was", "why is there no", "frustrated
   with", "what do you recommend", "stopped working", "broke after",
   "any alternative to".
2. Identify 3-8 subreddits relevant to the niche.
3. Run the searches. Pull threads and their top comments. Respect
   `run_limits.max_reddit_threads` in `config/thresholds.json`.
4. Cluster results into distinct pain points. For each pain point record:
   - the pain stated in one sentence
   - frequency — count of distinct threads/comments expressing it
   - sentiment — `negative`, `mixed`, or `request`
   - 1-5 citation URLs (real, copied from tool output)
   - 1-2 representative quotes, copied verbatim from tool output
5. Rank pain points by frequency, breaking ties by intensity.

## Output
Update `data/painpoints.json` (a JSON array). Append one object per pain point:

```json
{
  "niche": "string",
  "pain": "string",
  "frequency": 0,
  "sentiment": "negative|mixed|request",
  "citations": ["https://reddit.com/..."],
  "quotes": ["verbatim string"],
  "subreddits": ["r/..."],
  "pulled_at": "ISO-8601"
}
```

Return to the orchestrator the top pain points and the path written.

## Guardrails
- Never invent quotes, URLs, subreddits, or counts. If a search returns
  nothing, record an empty result and say so explicitly.
- Public posts only — no logged-in, private, or quarantined content.
- Cache raw tool output under `data/cache/` keyed by query; reuse within the
  `cache.ttl_hours` window instead of re-fetching.
