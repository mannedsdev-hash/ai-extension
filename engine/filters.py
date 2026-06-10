"""rough_filter — RawProduct -> Candidate, with every drop ledgered.

Hard drops (always with a reason in the ledger): price outside band, category
not requested, excluded term in title. Everything regulatory or size-related
is a MARK, never a silent drop — compliance_triage (AI seam) annotates the
risk and humans/scoring decide downstream.
"""
from __future__ import annotations

from .ai import AIGate
from .ledger import Ledger
from .models import Candidate, RawProduct, RunContext


def _origin_for(raw: RawProduct, pool: dict[str, str], ws_terms: list[str]) -> str:
    title = raw.title.lower()
    if any(f"asin_seed:" in f for f in raw.found_by):
        return "asin_seed"
    if any(f.startswith("best_sellers") for f in raw.found_by):
        best = "bestseller"
    else:
        best = "search"
    for term, origin in pool.items():
        if term in title:
            return {"seed": "seed", "concept": "concept"}.get(origin, best)
    if any(t in title for t in ws_terms):
        return "whitespace"
    return best


def rough_filter(raws: list[RawProduct], ctx: RunContext, cfg: dict,
                 pool: dict[str, str], ws_terms: list[str],
                 ai: AIGate, ledger: Ledger) -> list[Candidate]:
    size = cfg["size_limits"]
    comp_kw: dict[str, str] = cfg["compliance_keywords"]
    candidates: list[Candidate] = []
    drops: dict[str, int] = {}

    for raw in raws:
        reason = None
        if not (ctx.price_min <= raw.price <= ctx.price_max):
            reason = "price_out_of_band"
        elif ctx.categories and raw.category not in ctx.categories:
            reason = "category_not_requested"
        elif any(x.lower() in raw.title.lower() for x in ctx.exclude_terms):
            reason = "excluded_term"
        if reason:
            drops[reason] = drops.get(reason, 0) + 1
            ledger.event("candidate_dropped", asin=raw.asin, reason=reason,
                         title=raw.title, price=raw.price)
            continue

        cand = Candidate(raw=raw, origin=_origin_for(raw, pool, ws_terms))

        if raw.weight_oz > size["oversize_weight_oz"] or \
           raw.longest_side_in > size["oversize_longest_side_in"]:
            cand.marks.append("oversize")

        title = raw.title.lower()
        for kw, mark in comp_kw.items():
            if kw in title and mark not in cand.marks:
                cand.marks.append(mark)
                cand.compliance_notes.append(
                    ai.judge("compliance_triage", {"mark": mark, "title": raw.title}))

        candidates.append(cand)

    ledger.event("rough_filter", kept=len(candidates), drops=drops)
    return candidates
