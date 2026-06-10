"""economics.estimate_all — unit economics per candidate.

BSR -> units/mo via per-category power curves (config/discovery.json, rough
proxies until a Keepa-calibrated source is wired). Fees come straight from
config/amazon-fees.json — the same file the margin-scorer skill uses, so the
engine and the Claude-side skills can never disagree on fee math.
"""
from __future__ import annotations

import json
from pathlib import Path

from .ledger import Ledger
from .models import Candidate, Economics


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _units_per_month(bsr: int, category: str, curves: dict) -> int:
    c = curves.get(category, curves["default"])
    return max(0, int(c["a"] * (max(bsr, 1) ** -c["b"])))


def _fba_fee(weight_oz: float, oversize: bool, fees: dict) -> float:
    if oversize:
        return next(t["fee"] for t in fees["fba_fulfillment_fee"]["tiers"]
                    if t["id"] == "large_bulky")
    for tier in fees["fba_fulfillment_fee"]["tiers"]:
        if tier["size"] == "large_standard" and weight_oz <= tier["max_weight_oz"]:
            return tier["fee"]
    return fees["fba_fulfillment_fee"]["tiers"][-1]["fee"]


def estimate_all(candidates: list[Candidate], cfg: dict, ledger: Ledger,
                 fees_path: str = "config/amazon-fees.json") -> list[Candidate]:
    fees = _load(fees_path)
    econ_cfg = cfg["economics"]
    curves = cfg["bsr_to_units"]
    rate_by_cat = fees["referral_fee_rate"]["by_category"]
    default_rate = fees["referral_fee_rate"]["default"]

    for cand in candidates:
        r = cand.raw
        oversize = "oversize" in cand.marks
        rate = rate_by_cat.get(r.category, default_rate)
        referral = max(fees["minimum_referral_fee"], round(r.price * rate, 2))
        fba = _fba_fee(r.weight_oz, oversize, fees)
        landed = round(r.price * econ_cfg["assumed_cogs_ratio"], 2)
        units = _units_per_month(r.bsr, r.category, curves)
        margin = (r.price - referral - fba - landed) / r.price if r.price else 0.0
        breakeven = round((fba + landed) / max(1e-6, (1 - rate)), 2)

        cand.economics = Economics(
            units_per_month=units,
            revenue_per_month=round(units * r.price, 2),
            referral_fee=referral,
            fba_fee=fba,
            landed_cost_est=landed,
            margin_pct=round(margin, 4),
            breakeven_price=breakeven,
            fba_ready=(not oversize
                       and margin >= econ_cfg["margin_floor"]
                       and r.weight_oz <= 48),
        )

    ledger.event("economics_done", estimated=len(candidates))
    return candidates
