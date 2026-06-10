"""AIGate — the only door AI judgment enters the engine through.

Four named seams in Phase 1: concept_expand, whitespace_synth,
compliance_triage, rank_rationale. Each seam has a deterministic heuristic
fallback so the engine NEVER blocks on AI availability:

  backend "heuristic"       — fallback only (default; zero cost, reproducible)
  backend "claude_session"  — writes the seam request to data/runs/ai_requests/
                              for the Claude Code session to answer, and uses
                              the heuristic in the meantime (marked ai_pending)
  backend "anthropic_api"   — calls the API if ANTHROPIC_API_KEY is set,
                              else falls back to heuristic

Every seam invocation is ledgered with the backend that actually answered.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .budget import BudgetGovernor
from .ledger import Ledger

CONCEPT_MODIFIERS = ["compact", "travel", "stackable", "kids", "eco", "pro"]


class AIGate:
    def __init__(self, ledger: Ledger, governor: BudgetGovernor,
                 backend: str = "heuristic", requests_dir: str = "data/runs/ai_requests"):
        self.ledger = ledger
        self.governor = governor
        self.backend = backend
        self.requests_dir = Path(requests_dir)

    def judge(self, seam: str, payload: dict) -> dict:
        backend_used = "heuristic"
        result = self._heuristic(seam, payload)

        if self.backend == "anthropic_api" and os.environ.get("ANTHROPIC_API_KEY"):
            if self.governor.spend("llm_calls", note=seam):
                api = self._anthropic(seam, payload)
                if api is not None:
                    result, backend_used = api, "anthropic_api"
        elif self.backend == "claude_session":
            self._write_request(seam, payload, result)
            result["ai_pending"] = True
            backend_used = "claude_session(queued)"

        self.ledger.event("ai_seam", seam=seam, backend=backend_used,
                          result_summary=str(result)[:300])
        return result

    # ---------- deterministic fallbacks ----------

    def _heuristic(self, seam: str, p: dict) -> dict:
        if seam == "concept_expand":
            concepts = []
            for seed in p.get("seeds", []):
                for mod in CONCEPT_MODIFIERS[:2]:
                    concepts.append({"term": f"{mod} {seed}", "from_seed": seed})
                for cat in p.get("categories", [])[:1]:
                    concepts.append({"term": f"{seed} for {cat.replace('_', ' ')}",
                                     "from_seed": seed})
            return {"concepts": concepts}

        if seam == "whitespace_synth":
            return {"concepts": [
                {"term": t, "angle": "strong off-Amazon interest, thin on-Amazon supply"}
                for t in p.get("terms", [])]}

        if seam == "compliance_triage":
            risk = {"hazmat": "high", "ingestible": "high", "safety_cert": "high",
                    "topical": "medium", "fcc": "medium", "restricted_age": "medium"}
            mark = p.get("mark", "")
            return {"mark": mark, "risk": risk.get(mark, "low"),
                    "action": f"verify '{mark}' requirements (certs/approval) before sourcing"}

        if seam == "rank_rationale":
            s, e = p.get("sub_scores", {}), p.get("economics", {})
            top = sorted(s.items(), key=lambda kv: kv[1], reverse=True)[:2]
            why = " and ".join(f"{k}={v:.0f}" for k, v in top) if top else "no sub-scores"
            return {"rationale": (f"Lane {p.get('lane', '?')}: strongest on {why}; "
                                  f"est. {e.get('units_per_month', 0)} units/mo at "
                                  f"{e.get('margin_pct', 0) * 100:.0f}% margin.")}

        return {}

    # ---------- real-AI backends ----------

    def _anthropic(self, seam: str, payload: dict) -> dict | None:
        try:
            import anthropic  # optional dependency
            client = anthropic.Anthropic()
            msg = client.messages.create(
                model=os.environ.get("ENGINE_AI_MODEL", "claude-haiku-4-5-20251001"),
                max_tokens=800,
                messages=[{"role": "user", "content": (
                    f"Seam '{seam}' for an Amazon product-research engine. "
                    f"Respond with JSON only, same shape as this fallback: "
                    f"{json.dumps(self._heuristic(seam, payload))}\n"
                    f"Input payload: {json.dumps(payload)[:4000]}")}],
            )
            return json.loads(msg.content[0].text)
        except Exception as exc:  # any failure -> heuristic already in hand
            self.ledger.event("ai_seam_error", seam=seam, error=str(exc)[:200])
            return None

    def _write_request(self, seam: str, payload: dict, fallback: dict) -> None:
        self.requests_dir.mkdir(parents=True, exist_ok=True)
        n = len(list(self.requests_dir.glob("*.json")))
        (self.requests_dir / f"{self.ledger.run_id}-{n:03d}-{seam}.json").write_text(
            json.dumps({"seam": seam, "payload": payload,
                        "heuristic_answer": fallback}, indent=2), encoding="utf-8")
