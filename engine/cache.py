"""TTL file cache for connector calls — credits only get spent once per query.

Keyed by md5(connector|method|query), stored as JSON under data/cache/engine/.
TTL default 24h (config/discovery.json -> cache_ttl_hours). Stale entries are
re-fetched, not served.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path


class FileCache:
    def __init__(self, root: str = "data/cache/engine", ttl_hours: float = 24):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl_hours * 3600
        self.hits = 0
        self.misses = 0

    def _path(self, key: str) -> Path:
        return self.root / (hashlib.md5(key.encode()).hexdigest() + ".json")

    def get(self, key: str):
        f = self._path(key)
        if not f.exists():
            self.misses += 1
            return None
        try:
            blob = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self.misses += 1
            return None
        if time.time() - blob.get("ts", 0) > self.ttl:
            self.misses += 1
            return None
        self.hits += 1
        return blob["value"]

    def put(self, key: str, value) -> None:
        self._path(key).write_text(
            json.dumps({"ts": time.time(), "key": key, "value": value}, default=str),
            encoding="utf-8")
