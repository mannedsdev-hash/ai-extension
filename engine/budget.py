"""BudgetGovernor — every paid or rate-limited call asks permission first.

Resources are just named counters with caps (connector_calls, social_calls,
trend_checks, llm_calls...). A denial is ledgered and the caller degrades
gracefully — the engine finishes on whatever it already has.
"""
from __future__ import annotations

from collections import defaultdict

from .ledger import Ledger

DEFAULT_CAPS = {
    "connector_calls": 90,
    "social_calls": 24,
    "trend_checks": 25,
    "llm_calls": 20,
}


class BudgetGovernor:
    def __init__(self, ledger: Ledger, caps: dict | None = None):
        self.ledger = ledger
        self.caps = {**DEFAULT_CAPS, **(caps or {})}
        self.spent: dict[str, int] = defaultdict(int)
        self.denials: dict[str, int] = defaultdict(int)

    def spend(self, resource: str, n: int = 1, note: str = "") -> bool:
        cap = self.caps.get(resource)
        if cap is not None and self.spent[resource] + n > cap:
            self.denials[resource] += 1
            # first denial per resource is worth a ledger line; the rest are counted
            if self.denials[resource] == 1:
                self.ledger.event("budget_deny", resource=resource, cap=cap,
                                  spent=self.spent[resource], note=note)
            return False
        self.spent[resource] += n
        return True

    def summary(self) -> dict:
        return {r: {"spent": self.spent[r], "cap": self.caps.get(r), "denied": self.denials[r]}
                for r in set(list(self.caps) + list(self.spent))}
