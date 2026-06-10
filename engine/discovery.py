"""SearchResolver — fan out (term x category) into deduped RawProducts.

Channels per term: search, autocomplete-expanded search; per category:
best_sellers once; per asin_seed: direct product lookup. Every connector hit
passes the BudgetGovernor first; on denial the resolver returns what it has.
Dedupe is by parent_asin (keep the best BSR, merge provenance).
"""
from __future__ import annotations

from .budget import BudgetGovernor
from .connectors import Connector
from .ledger import Ledger
from .models import RawProduct, RunContext


class SearchResolver:
    def __init__(self, connector: Connector, governor: BudgetGovernor, ledger: Ledger):
        self.c = connector
        self.gov = governor
        self.ledger = ledger

    def resolve(self, ctx: RunContext, terms: list[str]) -> list[RawProduct]:
        hits: list[dict] = []

        for cat in ctx.categories:                            # one BSR pull per category
            if not self.gov.spend("connector_calls", note=f"best_sellers:{cat}"):
                break
            for p in self.c.best_sellers(cat):
                hits.append({**p, "found_by": [f"best_sellers:{cat}"]})

        for term in terms:
            variants = [term]
            if self.gov.spend("connector_calls", note=f"autocomplete:{term}"):
                variants += self.c.autocomplete(term)[:2]
            for v in variants:
                for cat in (ctx.categories or [None]):
                    if not self.gov.spend("connector_calls", note=f"search:{v}"):
                        return self._finish(hits)
                    for p in self.c.search(v, cat):
                        hits.append({**p, "found_by": [f"search:{v}" + (f"@{cat}" if cat else "")]})

        for asin in ctx.asin_seeds:
            if self.gov.spend("connector_calls", note=f"product:{asin}"):
                p = self.c.product(asin)
                if p:
                    hits.append({**p, "found_by": [f"asin_seed:{asin}"]})

        return self._finish(hits)

    def _finish(self, hits: list[dict]) -> list[RawProduct]:
        by_parent: dict[str, dict] = {}
        for h in hits:
            key = h["parent_asin"]
            kept = by_parent.get(key)
            if kept is None or h["bsr"] < kept["bsr"]:        # keep best-ranked variant
                merged_prov = (kept["found_by"] if kept else []) + h["found_by"]
                by_parent[key] = {**h, "found_by": sorted(set(merged_prov))}
            else:
                kept["found_by"] = sorted(set(kept["found_by"] + h["found_by"]))
        raws = [RawProduct(**{k: v for k, v in h.items()}) for h in by_parent.values()]
        raws.sort(key=lambda r: r.bsr)
        self.ledger.event("resolver_done", raw_hits=len(hits), unique_parents=len(raws))
        return raws
