"""fusion.rank — persona-weighted scoring, lane assignment, rationale.

Six sub-scores, all 0-100:
  velocity        estimated units/mo vs reference
  buzz            social strength on the term that matches this product
  idea_affinity   how close to the seller's own seeds/concepts it sits
  low_competition inverse of review depth + seller count
  agreement       cross-platform social agreement on the matching term
  supply_gap      demand high while seller count low

Lane: 🟢 safe (proven, reviewed) · 🟡 early (growing, thin reviews) ·
🔵 whitespace (off-Amazon heat, thin on-Amazon supply). A near-zero margin
never hides behind a good total — fba_ready=False caps the score.
"""
from __future__ import annotations

from .ai import AIGate
from .ledger import Ledger
from .models import Candidate

ORIGIN_AFFINITY = {"seed": 100, "asin_seed": 90, "concept": 70,
                   "whitespace": 55, "bestseller": 35, "search": 25}


def _match_signal(cand: Candidate, signals: dict) -> dict:
    title = cand.raw.title.lower()
    best = {"agreement": 0, "strength": 0.0}
    for term, sig in signals.items():
        if term in title and sig["strength"] > best["strength"]:
            best = sig
    return best


def rank(candidates: list[Candidate], signals: dict, weights: dict,
         cfg: dict, ai: AIGate, ledger: Ledger) -> list[Candidate]:
    econ_cfg = cfg["economics"]
    lanes = cfg["lanes"]

    for cand in candidates:
        r, e = cand.raw, cand.economics
        sig = _match_signal(cand, signals)

        velocity = min(100.0, e.units_per_month / econ_cfg["velocity_ref_units"] * 100)
        buzz = max(0.0, min(100.0, sig["strength"] * 2))          # 50% avg growth = 100
        idea = ORIGIN_AFFINITY.get(cand.origin, 25)
        review_pressure = min(100.0, r.reviews_count / econ_cfg["reviews_ref"] * 100)
        # sellers_count 0 means UNKNOWN on real connectors — score it neutral
        # (midpoint), not as an empty market
        sellers_known = r.sellers_count > 0
        seller_pressure = (min(100.0, r.sellers_count / econ_cfg["sellers_ref"] * 100)
                           if sellers_known else 50.0)
        low_comp = 100 - (review_pressure * 0.7 + seller_pressure * 0.3)
        agreement = sig["agreement"] / 3 * 100
        gap_room = (1 - min(1.0, r.sellers_count / econ_cfg["sellers_ref"])
                    if sellers_known else 0.5)
        supply_gap = min(100.0, velocity) * gap_room

        cand.sub_scores = {k: round(v, 1) for k, v in {
            "velocity": velocity, "buzz": buzz, "idea_affinity": idea,
            "low_competition": low_comp, "agreement": agreement,
            "supply_gap": supply_gap}.items()}
        score = sum(weights[k] * cand.sub_scores[k] for k in weights)
        if not e.fba_ready:                       # fatal-flaw cap, never masked
            score = min(score, 35.0)
        cand.score = round(score, 1)

        if cand.origin == "whitespace" or (
                r.reviews_count <= lanes["whitespace_max_reviews"] and sig["agreement"] >= 2):
            cand.lane = "whitespace"
        elif r.trend == "growing" and r.reviews_count < lanes["safe_min_reviews"]:
            cand.lane = "early"
        else:
            cand.lane = "safe"

    candidates.sort(key=lambda c: c.score, reverse=True)

    for i, cand in enumerate(candidates):
        if i < 10:                                # rationale only where humans will read
            cand.rationale = ai.judge("rank_rationale", {
                "lane": cand.lane, "sub_scores": cand.sub_scores,
                "economics": cand.economics.to_dict()}).get("rationale", "")
        ledger.event("candidate_ranked", asin=cand.asin, rank=i + 1,
                     score=cand.score, lane=cand.lane, origin=cand.origin,
                     marks=cand.marks, sub_scores=cand.sub_scores,
                     margin_pct=cand.economics.margin_pct,
                     units_per_month=cand.economics.units_per_month,
                     found_by=cand.raw.found_by)
    return candidates
