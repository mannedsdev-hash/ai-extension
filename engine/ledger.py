"""Append-only run ledger — the moat / flywheel.

Every candidate decision (kept, dropped, marked), every AI seam output, and
every budget denial is one JSON line in data/runs/<run_id>.jsonl. Later
phases and future runs read this history; nothing is decided silently.
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path


class Ledger:
    def __init__(self, runs_dir: str = "data/runs"):
        self.runs_dir = Path(runs_dir)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = time.strftime("%Y%m%d-%H%M%S")
        self.path = self.runs_dir / f"{self.run_id}.jsonl"
        self._fh = self.path.open("a", encoding="utf-8")
        self._count = 0

    def event(self, kind: str, **data) -> None:
        line = {"ts": time.time(), "run_id": self.run_id, "kind": kind, **data}
        self._fh.write(json.dumps(line, default=str) + "\n")
        self._count += 1

    def write_shortlist(self, payload: dict) -> Path:
        out = self.runs_dir / "shortlist.json"
        out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return out

    def close(self) -> Path:
        self.event("run_closed", events_written=self._count)
        self._fh.close()
        last = self.runs_dir / "last_run.jsonl"
        shutil.copyfile(self.path, last)
        return self.path
