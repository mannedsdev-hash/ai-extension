"""Connector protocol — the engine is data-source agnostic.

Implementations: mock (built, deterministic). Next tiers: apify (free
credits), then sp-api/keepa. Swap via config/discovery.json -> "connector".
Per the 2026 BSA rules: official/third-party data APIs only, never browser
bots on Seller Central.
"""
from __future__ import annotations

from typing import Protocol


class Connector(Protocol):
    name: str

    def search(self, term: str, category: str | None = None) -> list[dict]: ...
    def best_sellers(self, category: str) -> list[dict]: ...
    def autocomplete(self, term: str) -> list[str]: ...
    def product(self, asin: str) -> dict | None: ...
    def bsr_trend(self, asin: str) -> list[int]: ...          # oldest -> newest
    def social_feed(self, platform: str, term: str) -> dict: ...


def get_connector(name: str, cfg: dict | None = None) -> "Connector":
    if name == "mock":
        from .mock import MockConnector
        return MockConnector()
    if name == "apify":
        from .apify import ApifyConnector
        return ApifyConnector(cfg or {})
    raise ValueError(f"unknown connector '{name}' — wire it in engine/connectors/")
