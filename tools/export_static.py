#!/usr/bin/env python3
"""Export the dashboard + the latest run as ONE self-contained HTML file.

  python3 tools/export_static.py            # -> docs/phase1.html

Inlines web/styles.css and web/app.js into web/index.html and embeds the
latest data/runs/shortlist.json (+ ledger events) as window.__ENGINE_DATA__ /
window.__ENGINE_LEDGER__ — the page then works with no server: file://,
GitHub Pages, htmlpreview. Run the engine first so there is data to embed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_LEDGER_EVENTS = 400


def main() -> int:
    shortlist = ROOT / "data/runs/shortlist.json"
    if not shortlist.exists():
        print("No run found — run `python3 run_engine.py --demo` first.")
        return 1
    data = shortlist.read_text(encoding="utf-8")

    ledger_file = ROOT / "data/runs/last_run.jsonl"
    events = []
    if ledger_file.exists():
        for line in ledger_file.read_text(encoding="utf-8").splitlines()[:MAX_LEDGER_EVENTS]:
            events.append(json.loads(line))

    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    css = (ROOT / "web/styles.css").read_text(encoding="utf-8")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")

    # a literal "</" inside the JSON would terminate the <script> tag early;
    # "<\/" is the standard JSON/JS escape with identical meaning
    safe = lambda j: j.replace("</", "<\\/")
    embed = ("<script>\n"
             f"window.__ENGINE_DATA__ = {safe(data)};\n"
             f"window.__ENGINE_LEDGER__ = {safe(json.dumps(events, default=str))};\n"
             "</script>")

    html = html.replace('<link rel="stylesheet" href="styles.css">',
                        f"<style>\n{css}\n</style>")
    html = html.replace('<script src="app.js"></script>',
                        f"{embed}\n<script>\n{js}\n</script>")

    out = ROOT / "docs/phase1.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    run_id = json.loads(data).get("run_id", "?")
    print(f"exported run {run_id} -> {out} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
