"""run_discover — the whole Phase 1 pipeline as one callable.

Single source of truth for the run sequence; both run_engine.py (CLI) and
serve.py (web) call this. Returns a JSON-safe payload and writes the same
artifacts either way: data/runs/<run_id>.jsonl + data/runs/shortlist.json.
"""
from __future__ import annotations

import json
from pathlib import Path

from .ai import AIGate
from .budget import BudgetGovernor
from .connectors import get_connector
from .discovery import SearchResolver
from .economics import estimate_all
from .filters import rough_filter
from .fusion import rank
from .ledger import Ledger
from .models import RunContext
from .scouts import CustomScout, ProvenScout, SocialScout


def load_configs(base: str = "config") -> tuple[dict, dict]:
    cfg = json.loads(Path(base, "discovery.json").read_text(encoding="utf-8"))
    personas = json.loads(Path(base, "personas.json").read_text(encoding="utf-8"))
    return cfg, personas


def run_discover(ctx: RunContext, ai_backend: str = "heuristic",
                 connector_name: str | None = None) -> dict:
    cfg, personas = load_configs()
    if ctx.persona not in personas:
        raise ValueError(f"unknown persona '{ctx.persona}'")
    cfg["connector"] = connector_name or cfg["connector"]
    limits = dict(cfg["run_limits"])
    if cfg["connector"] == "apify":     # real actor runs are slow + cost credits
        limits["max_connector_calls"] = cfg["apify"]["max_connector_calls"]
    ctx.shortlist_size = ctx.shortlist_size or limits["shortlist_size"]

    ledger = Ledger()
    ledger.event("run_started", ctx=ctx.to_dict(), connector=cfg["connector"], ai=ai_backend)
    governor = BudgetGovernor(ledger, caps={
        "connector_calls": limits["max_connector_calls"],
        "social_calls": limits["max_social_terms"] * 3,
        "trend_checks": limits["max_trend_checks"],
    })
    ai = AIGate(ledger, governor, backend=ai_backend)
    connector = get_connector(cfg["connector"], cfg)

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

    payload = {
        "run_id": ledger.run_id,
        "connector": cfg["connector"],
        "ai_backend": ai_backend,
        "ctx": ctx.to_dict(),
        "pool": pool,
        "whitespace_terms": ws_terms,
        "signals": signals,
        "guardrails": guardrails,
        "total_ranked": len(ranked),
        "candidates": [c.to_dict() for c in shortlist],
    }
    ledger.write_shortlist(payload)
    ledger.event("guardrails", **{k: v for k, v in guardrails.items() if k != "G1_budget"})
    payload["ledger_path"] = str(ledger.close())
    return payload
