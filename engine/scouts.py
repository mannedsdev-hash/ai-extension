"""Wave 1 — the three data scouts.

CustomScout : seller's own ideas -> concept candidates (AI seam concept_expand)
ProvenScout : tags resolver output with BSR-trend class, filters by mode
SocialScout : off-Amazon signal across 3 platforms; agreement = strength;
              hot-but-thin terms become whitespace concepts (AI seam
              whitespace_synth)

Scouts never call connectors directly except through the BudgetGovernor.
"""
from __future__ import annotations

from .ai import AIGate
from .budget import BudgetGovernor
from .connectors import Connector
from .ledger import Ledger
from .models import RawProduct, RunContext

PLATFORMS = ("tiktok", "reddit", "pinterest")


class CustomScout:
    """Seeds in, term pool out. Registers every term with its origin."""

    def __init__(self, ai: AIGate, ledger: Ledger):
        self.ai = ai
        self.ledger = ledger

    def run(self, ctx: RunContext, max_terms: int) -> dict[str, str]:
        pool: dict[str, str] = {s.lower(): "seed" for s in ctx.seeds}
        expanded = self.ai.judge("concept_expand",
                                 {"seeds": ctx.seeds, "categories": ctx.categories})
        for c in expanded.get("concepts", []):
            pool.setdefault(c["term"].lower(), "concept")
        pool = dict(list(pool.items())[:max_terms])
        self.ledger.event("custom_scout", pool=pool)
        return pool


class SocialScout:
    """Cross-platform signal. agreement = #platforms with hot growth."""

    def __init__(self, connector: Connector, governor: BudgetGovernor,
                 ai: AIGate, ledger: Ledger):
        self.c = connector
        self.gov = governor
        self.ai = ai
        self.ledger = ledger

    def run(self, pool: dict[str, str], hot_growth_pct: float,
            max_terms: int) -> tuple[dict, list[str]]:
        signals: dict[str, dict] = {}
        for term in list(pool)[:max_terms]:
            feeds = []
            for platform in PLATFORMS:
                if not self.gov.spend("social_calls", note=f"{platform}:{term}"):
                    break
                feeds.append(self.c.social_feed(platform, term))
            if not feeds:
                break
            hot = [f for f in feeds if f["growth_pct"] >= hot_growth_pct]
            signals[term] = {
                "agreement": len(hot),
                "strength": round(sum(f["growth_pct"] for f in feeds) / len(feeds), 1),
                "mentions": sum(f["mentions_30d"] for f in feeds),
                "evidence": [f"{f['platform']}:+{f['growth_pct']}%" for f in hot],
            }

        whitespace_terms = [t for t, s in signals.items() if s["agreement"] >= 2]
        ws = self.ai.judge("whitespace_synth", {"terms": whitespace_terms})
        ws_terms = [c["term"].lower() for c in ws.get("concepts", [])]
        self.ledger.event("social_scout", signals=signals, whitespace=ws_terms)
        return signals, ws_terms


class ProvenScout:
    """On-Amazon movers: classify each raw product's BSR trend, filter by mode."""

    def __init__(self, connector: Connector, governor: BudgetGovernor, ledger: Ledger):
        self.c = connector
        self.gov = governor
        self.ledger = ledger

    @staticmethod
    def _classify(series: list[int]) -> str:
        if len(series) < 2 or series[0] <= 0:
            return "unknown"
        change = (series[-1] - series[0]) / series[0]   # BSR falling = rank improving
        if change <= -0.25:
            return "growing"
        if change >= 0.25:
            return "declining"
        return "peak" if series[-1] <= 2000 else "flat"

    def run(self, ctx: RunContext, raws: list[RawProduct],
            max_checks: int) -> list[RawProduct]:
        counts: dict[str, int] = {}
        for raw in raws[:max_checks]:
            if not self.gov.spend("trend_checks", note=raw.asin):
                break
            raw.trend = self._classify(self.c.bsr_trend(raw.asin))
            counts[raw.trend] = counts.get(raw.trend, 0) + 1

        if ctx.proven_mode == "peak":
            keep_trends = {"peak", "flat", "unknown"}
        elif ctx.proven_mode == "growing":
            keep_trends = {"growing", "unknown"}
        else:                                            # both
            keep_trends = {"growing", "peak", "flat", "unknown"}
        kept = [r for r in raws if r.trend in keep_trends]
        dropped = len(raws) - len(kept)
        self.ledger.event("proven_scout", mode=ctx.proven_mode,
                          trend_counts=counts, dropped_declining=dropped)
        return kept
