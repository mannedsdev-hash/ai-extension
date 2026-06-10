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
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.ai import AIGate
from engine.budget import BudgetGovernor
from engine.connectors import get_connector
from engine.discovery import SearchResolver
from engine.economics import estimate_all
from engine.filters import rough_filter
from engine.fusion import rank
from engine.ledger import Ledger
from engine.models import LANE_EMOJI, RunContext
from engine.scouts import CustomScout, ProvenScout, SocialScout


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
    cfg = json.loads(Path("config/discovery.json").read_text(encoding="utf-8"))
    personas = json.loads(Path("config/personas.json").read_text(encoding="utf-8"))
    limits = cfg["run_limits"]

    ctx = RunContext(
        seeds=args.seeds or (["spice rack", "cable organizer"] if args.demo else []),
        categories=args.categories or (["kitchen", "office_products"] if args.demo else []),
        asin_seeds=args.asin_seeds,
        exclude_terms=args.exclude,
        persona=args.persona,
        price_min=args.price_min,
        price_max=args.price_max,
        proven_mode=args.proven_mode,
        shortlist_size=args.shortlist or limits["shortlist_size"],
    )
    if not ctx.seeds:
        print("No seeds given. Use --seeds or --demo.")
        return 2
    if args.persona not in personas:
        print(f"Unknown persona '{args.persona}'. Options: "
              f"{', '.join(k for k in personas if k != 'meta')}")
        return 2

    ledger = Ledger()
    ledger.event("run_started", ctx=ctx.to_dict(), connector=cfg["connector"], ai=args.ai)
    governor = BudgetGovernor(ledger, caps={
        "connector_calls": limits["max_connector_calls"],
        "social_calls": limits["max_social_terms"] * 3,
        "trend_checks": limits["max_trend_checks"],
    })
    ai = AIGate(ledger, governor, backend=args.ai)
    connector = get_connector(cfg["connector"])

    # WAVE 1 — scouts
    pool = CustomScout(ai, ledger).run(ctx, limits["max_pool_terms"])
    signals, ws_terms = SocialScout(connector, governor, ai, ledger).run(
        pool, cfg["lanes"]["social_hot_growth_pct"], limits["max_social_terms"])

    # fan-out + trend tagging
    resolver = SearchResolver(connector, governor, ledger)
    raws = resolver.resolve(ctx, (list(pool) + ws_terms)[:limits["max_pool_terms"]])
    raws = ProvenScout(connector, governor, ledger).run(ctx, raws, limits["max_trend_checks"])

    # filter -> economics -> fusion
    candidates = rough_filter(raws, ctx, cfg, pool, ws_terms, ai, ledger)
    candidates = estimate_all(candidates, cfg, ledger)
    ranked = rank(candidates, signals, personas[ctx.persona], cfg, ai, ledger)
    shortlist = ranked[:ctx.shortlist_size]

    # ---- report ----
    print(f"\n=== PHASE 1 DISCOVER — run {ledger.run_id} · persona {ctx.persona} "
          f"· connector {cfg['connector']} · ai {args.ai} ===\n")
    hdr = f"{'#':>2} {'ln':2} {'asin':10} {'title':38} {'price':>7} {'u/mo':>5} {'mrg%':>5} {'score':>5}  marks"
    print(hdr + "\n" + "-" * len(hdr))
    for i, c in enumerate(shortlist, 1):
        e = c.economics
        print(f"{i:>2} {LANE_EMOJI[c.lane]:2} {c.asin:10} {c.raw.title[:38]:38} "
              f"{c.raw.price:>7.2f} {e.units_per_month:>5} {e.margin_pct * 100:>5.1f} "
              f"{c.score:>5.1f}  {','.join(c.marks) or '-'}")
        if c.rationale:
            print(f"      ↳ {c.rationale}")

    floor = cfg["economics"]["margin_floor"]
    guardrails = {
        "G1_budget": governor.summary(),
        "G2_data": ("MOCK DATA — not real market data; wire the apify connector"
                    if cfg["connector"] == "mock" else "live"),
        "G3_size_or_compliance_marked": sum(1 for c in ranked if c.marks),
        "G4_below_margin_floor": sum(1 for c in shortlist
                                     if c.economics.margin_pct < floor),
        "G5_saturated_in_shortlist": sum(
            1 for c in shortlist
            if c.raw.sellers_count > cfg["economics"]["sellers_ref"]
            or c.raw.reviews_count > cfg["economics"]["reviews_ref"]),
    }
    print("\nGUARDRAILS")
    for k, v in guardrails.items():
        print(f"  {k}: {v}")

    out = ledger.write_shortlist({
        "run_id": ledger.run_id, "ctx": ctx.to_dict(), "guardrails": guardrails,
        "candidates": [c.to_dict() for c in shortlist]})
    ledger.event("guardrails", **{k: v for k, v in guardrails.items() if k != "G1_budget"})
    path = ledger.close()
    print(f"\nshortlist -> {out}\nledger    -> {path}")
    if args.ai == "claude_session":
        print("AI seams queued -> data/runs/ai_requests/ "
              "(answer them in a Claude Code session, then re-rank)")
    print("➡️  next: Phase 2 Screen reads data/runs/shortlist.json (see PHASES.md)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
