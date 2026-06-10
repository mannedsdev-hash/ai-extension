"""Shared data contracts for the Phase 1 engine.

Plain dataclasses, stdlib only. Everything that crosses a module boundary is
defined here so the contract between waves is explicit and ledgerable.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional

LANES = ("safe", "early", "whitespace")
LANE_EMOJI = {"safe": "🟢", "early": "🟡", "whitespace": "🔵"}


@dataclass
class RunContext:
    """Everything a run is allowed to know up front."""
    seeds: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    asin_seeds: list[str] = field(default_factory=list)
    exclude_terms: list[str] = field(default_factory=list)
    persona: str = "default"
    price_min: float = 10.0
    price_max: float = 60.0
    proven_mode: str = "both"  # peak | growing | both
    budget_caps: dict = field(default_factory=dict)
    shortlist_size: int = 10

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RawProduct:
    """A product as a connector returned it, plus provenance."""
    asin: str
    parent_asin: str
    title: str
    category: str
    price: float
    bsr: int
    rating: float
    reviews_count: int
    sellers_count: int
    weight_oz: float
    longest_side_in: float
    source: str                       # connector name
    found_by: list[str] = field(default_factory=list)  # queries that surfaced it
    trend: str = "unknown"            # growing | peak | flat | declining | unknown

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Economics:
    units_per_month: int = 0
    revenue_per_month: float = 0.0
    referral_fee: float = 0.0
    fba_fee: float = 0.0
    landed_cost_est: float = 0.0
    margin_pct: float = 0.0
    breakeven_price: float = 0.0
    fba_ready: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Candidate:
    """A RawProduct that survived rough_filter, en route to fusion."""
    raw: RawProduct
    origin: str = "search"            # seed | concept | whitespace | search | bestseller | asin_seed
    marks: list[str] = field(default_factory=list)       # compliance/size marks — never silent drops
    compliance_notes: list[dict] = field(default_factory=list)
    economics: Optional[Economics] = None
    sub_scores: dict = field(default_factory=dict)
    score: float = 0.0
    lane: str = "safe"
    rationale: str = ""

    @property
    def asin(self) -> str:
        return self.raw.asin

    def to_dict(self) -> dict:
        d = asdict(self)
        d["asin"] = self.raw.asin
        return d
