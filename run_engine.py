#!/usr/bin/env python3
"""Phase 1 — Discover engine CLI.

  python3 run_engine.py --demo
  python3 run_engine.py --seeds "spice rack,cable organizer" \
      --categories kitchen,office_products --persona whitespace_scout \
      --ai claude_session

Outputs: ranked shortlist to stdout, data/runs/shortlist.json for Phase 2,
full decision ledger at data/runs/<run_id>.jsonl. With --ai claude_session,
AI seam requests are queued under data/runs/ai_requests/ for the Claude Code
session to answer (heuristic answers hold their place until then).

For the web dashboard: python3 serve.py
"""
from __future__ import annotations

import argparse

from engine.models import LANE_EMOJI, RunContext
from engine.pipeline import load_configs, run_discover


def _csv(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Phase 1 Discover engine")
    ap.add_argument("--seeds", type=_csv, default=[])
    ap.add_argument("--categories", type=_csv, default=[])
    ap.add_argument("--asin-seeds", type=_csv, default=[])
    ap.add_argument("--exclude", type=_csv, default=[])
    ap.add_argument("--persona", default="default")
    ap.add_argument("--price-min", type=float, default=10.0)
    ap.add_argument("--price-max", type=float, default=60.0)
    ap.add_argument("--proven-mode", choices=["peak", "growing", "both"], default="both")
    ap.add_argument("--ai", choices=["heuristic", "claude_session", "anthropic_api"],
                    default="heuristic")
    ap.add_argument("--shortlist", type=int, default=None)
    ap.add_argument("--demo", action="store_true",
                    help="run with demo seeds/categories on the mock connector")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    _, personas = load_configs()
    if args.persona not in personas:
        print(f"Unknown persona '{args.persona}'. Options: "
              f"{', '.join(k for k in personas if k != 'meta')}")
        return 2

    ctx = RunContext(
        seeds=args.seeds or (["spice rack", "cable organizer"] if args.demo else []),
        categories=args.categories or (["kitchen", "office_products"] if args.demo else []),
        asin_seeds=args.asin_seeds,
        exclude_terms=args.exclude,
        persona=args.persona,
        price_min=args.price_min,
        price_max=args.price_max,
        proven_mode=args.proven_mode,
        shortlist_size=args.shortlist or 0,
    )
    if not ctx.seeds:
        print("No seeds given. Use --seeds or --demo.")
        return 2

    p = run_discover(ctx, ai_backend=args.ai)

    print(f"\n=== PHASE 1 DISCOVER — run {p['run_id']} · persona {ctx.persona} "
          f"· connector {p['connector']} · ai {p['ai_backend']} ===\n")
    hdr = f"{'#':>2} {'ln':2} {'asin':10} {'title':38} {'price':>7} {'u/mo':>5} {'mrg%':>5} {'score':>5}  marks"
    print(hdr + "\n" + "-" * len(hdr))
    for i, c in enumerate(p["candidates"], 1):
        e, raw = c["economics"], c["raw"]
        print(f"{i:>2} {LANE_EMOJI[c['lane']]:2} {c['asin']:10} {raw['title'][:38]:38} "
              f"{raw['price']:>7.2f} {e['units_per_month']:>5} {e['margin_pct'] * 100:>5.1f} "
              f"{c['score']:>5.1f}  {','.join(c['marks']) or '-'}")
        if c["rationale"]:
            print(f"      ↳ {c['rationale']}")

    print("\nGUARDRAILS")
    for k, v in p["guardrails"].items():
        print(f"  {k}: {v}")

    print(f"\nshortlist -> data/runs/shortlist.json\nledger    -> {p['ledger_path']}")
    if args.ai == "claude_session":
        print("AI seams queued -> data/runs/ai_requests/ "
              "(answer them in a Claude Code session, then re-rank)")
    print("➡️  next: Phase 2 Screen reads data/runs/shortlist.json (see PHASES.md)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
