#!/usr/bin/env python3
"""Phase 1 dashboard server — stdlib only, no dependencies.

  python3 serve.py            # http://localhost:8013
  python3 serve.py --port 9000

Serves web/ and a small JSON API the dashboard uses:
  GET  /api/config     personas + categories + defaults for the run form
  GET  /api/shortlist  last run's shortlist payload (404 until a run exists)
  GET  /api/ledger     last run's ledger events (capped)
  POST /api/run        body = run params -> runs the engine, returns payload
"""
from __future__ import annotations

import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from engine.models import RunContext
from engine.pipeline import load_configs, run_discover

RUNS = Path("data/runs")
MAX_LEDGER_EVENTS = 600


class Api(SimpleHTTPRequestHandler):
    def _json(self, obj, status: int = 200) -> None:
        body = json.dumps(obj, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path == "/api/config":
            cfg, personas = load_configs()
            return self._json({
                "personas": [k for k in personas if k != "meta"],
                "categories": sorted(cfg["bsr_to_units"].keys() - {"default"}),
                "connector": cfg["connector"],
                "defaults": {"seeds": "spice rack, cable organizer",
                             "price_min": 10, "price_max": 60},
            })
        if self.path == "/api/shortlist":
            f = RUNS / "shortlist.json"
            if not f.exists():
                return self._json({"error": "no run yet"}, 404)
            return self._json(json.loads(f.read_text(encoding="utf-8")))
        if self.path == "/api/ledger":
            f = RUNS / "last_run.jsonl"
            if not f.exists():
                return self._json({"error": "no run yet"}, 404)
            lines = f.read_text(encoding="utf-8").splitlines()[:MAX_LEDGER_EVENTS]
            return self._json({"events": [json.loads(x) for x in lines]})
        return super().do_GET()

    def do_POST(self):  # noqa: N802
        if self.path != "/api/run":
            return self._json({"error": "unknown endpoint"}, 404)
        try:
            n = int(self.headers.get("Content-Length", 0))
            p = json.loads(self.rfile.read(n) or b"{}")
            csv = lambda v: [x.strip() for x in str(v or "").split(",") if x.strip()]
            ctx = RunContext(
                seeds=csv(p.get("seeds")),
                categories=p.get("categories") or [],
                asin_seeds=csv(p.get("asin_seeds")),
                exclude_terms=csv(p.get("exclude")),
                persona=p.get("persona") or "default",
                price_min=float(p.get("price_min") or 10),
                price_max=float(p.get("price_max") or 60),
                proven_mode=p.get("proven_mode") or "both",
            )
            if not ctx.seeds:
                return self._json({"error": "at least one seed term is required"}, 400)
            payload = run_discover(ctx, ai_backend=p.get("ai") or "heuristic",
                                   connector_name=p.get("connector") or None)
            return self._json(payload)
        except Exception as exc:  # surface engine errors to the UI, don't 500-blank
            return self._json({"error": str(exc)}, 500)

    def log_message(self, fmt, *args):  # quieter console
        if "/api/" in (args[0] if args else ""):
            super().log_message(fmt, *args)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8013)
    args = ap.parse_args()
    handler = partial(Api, directory="web")
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), handler)
    print(f"Phase 1 dashboard -> http://localhost:{args.port}  (Ctrl-C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
