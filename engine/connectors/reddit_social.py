"""Reddit as the real social signal source (script-app OAuth, stdlib only).

Needs in .env or the environment:
  REDDIT_CLIENT_ID=...      (under the app name at reddit.com/prefs/apps)
  REDDIT_CLIENT_SECRET=...

Signal model (honest about its coarseness):
  mentions_30d  = posts matching the term in the last month (API caps at 100)
  growth_pct    = month count vs (year count / 12) baseline, as a percentage
  top_phrases   = up to 3 recent post titles, verbatim
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from ..cache import FileCache

UA = "discover-engine/0.1 (personal product research)"


def _env(key: str) -> str:
    val = os.environ.get(key, "")
    if not val and Path(".env").exists():
        for line in Path(".env").read_text(encoding="utf-8").splitlines():
            if line.startswith(key + "="):
                val = line.split("=", 1)[1].strip()
    return val


class RedditSocial:
    def __init__(self, client_id: str, secret: str, cache: FileCache):
        self.client_id = client_id
        self.secret = secret
        self.cache = cache
        self._token = ""
        self._token_exp = 0.0

    @classmethod
    def from_env(cls, cache: FileCache) -> "RedditSocial | None":
        cid, sec = _env("REDDIT_CLIENT_ID"), _env("REDDIT_CLIENT_SECRET")
        return cls(cid, sec, cache) if cid and sec else None

    def _auth(self) -> str:
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        basic = base64.b64encode(f"{self.client_id}:{self.secret}".encode()).decode()
        req = urllib.request.Request(
            "https://www.reddit.com/api/v1/access_token",
            data=b"grant_type=client_credentials",
            headers={"Authorization": f"Basic {basic}", "User-Agent": UA},
            method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            tok = json.loads(r.read().decode())
        self._token = tok["access_token"]
        self._token_exp = time.time() + tok.get("expires_in", 3600)
        return self._token

    def _count(self, term: str, window: str) -> tuple[int, list[str]]:
        q = urllib.parse.quote_plus(term)
        req = urllib.request.Request(
            f"https://oauth.reddit.com/search?q={q}&sort=new&t={window}&limit=100",
            headers={"Authorization": f"Bearer {self._auth()}", "User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            posts = json.loads(r.read().decode()).get("data", {}).get("children", [])
        titles = [p["data"]["title"] for p in posts[:3]]
        return len(posts), titles

    def feed(self, term: str) -> dict:
        key = f"reddit|{term}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        try:
            month, titles = self._count(term, "month")
            year, _ = self._count(term, "year")
            baseline = max(1.0, year / 12)
            out = {
                "platform": "reddit", "term": term,
                "mentions_30d": month,
                "growth_pct": round((month - baseline) / baseline * 100, 1),
                "top_phrases": titles,
            }
            self.cache.put(key, out)
            return out
        except Exception as exc:
            print(f"[reddit] feed '{term}' failed: {exc}", file=sys.stderr)
            return {"platform": "reddit", "term": term, "mentions_30d": 0,
                    "growth_pct": 0.0, "top_phrases": [], "error": str(exc)[:120]}
