"""ApifyConnector — real Amazon data through Apify actors (stdlib only).

Auth: APIFY_TOKEN from the environment or .env. Actor ids and limits live in
config/discovery.json -> "apify" (actors change; config, not code).

Honesty rules (the engine depends on these):
- A field the actor didn't return is 0/empty, NEVER guessed. economics marks
  no_bsr_data / no_weight_data so gaps stay visible all the way to the UI.
- bsr_trend returns [] (Apify has no history — that's Keepa's job), so
  ProvenScout classifies "unknown" and keeps the product.
- social_feed returns zero-signal until a real social source (Reddit) is
  wired — buzz/agreement scores honestly read 0 on the apify connector.

Every search/detail call is one actor run (slow, costs credits): keep
run_limits low and let FileCache absorb repeats.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from ..cache import FileCache

API = "https://api.apify.com/v2"


def _load_env_token() -> str:
    tok = os.environ.get("APIFY_TOKEN", "")
    if not tok and Path(".env").exists():
        for line in Path(".env").read_text(encoding="utf-8").splitlines():
            if line.startswith("APIFY_TOKEN="):
                tok = line.split("=", 1)[1].strip()
    if not tok:
        raise RuntimeError("APIFY_TOKEN not set — put it in .env or the environment")
    return tok


def _warn(msg: str) -> None:
    print(f"[apify] {msg}", file=sys.stderr)


class ApifyConnector:
    name = "apify"

    def __init__(self, cfg: dict):
        a = cfg.get("apify", {})
        self.token = _load_env_token()
        self.search_actor = a.get("search_actor", "junglee~amazon-crawler")
        self.detail_actor = a.get("detail_actor", "junglee~amazon-crawler")
        self.marketplace = a.get("marketplace", "https://www.amazon.com")
        self.max_items = int(a.get("max_items_per_search", 12))
        self.bestseller_urls = a.get("bestseller_urls", {})
        self.cache = FileCache(ttl_hours=float(cfg.get("cache_ttl_hours", 24)))
        from .reddit_social import RedditSocial
        self.reddit = RedditSocial.from_env(self.cache)   # None until creds in .env

    # ---------- HTTP ----------

    def _post_actor(self, actor: str, body: dict, timeout: int = 180) -> list:
        url = (f"{API}/acts/{actor}/run-sync-get-dataset-items"
               f"?token={self.token}&timeout=150&memory=1024")
        req = urllib.request.Request(
            url, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                items = json.loads(r.read().decode())
                return items if isinstance(items, list) else []
        except Exception as exc:
            _warn(f"actor {actor} failed: {exc}")
            return []

    def _run_url_actor(self, cache_key: str, actor: str, page_url: str,
                       max_items: int) -> list:
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        items = self._post_actor(actor, {
            "categoryOrProductUrls": [{"url": page_url}],
            "maxItemsPerStartUrl": max_items,
            "maxOffers": 0,
            "scrapeProductVariantPrices": False,
        })
        if items:                                   # never cache a failure
            self.cache.put(cache_key, items)
        return items

    # ---------- item mapping (defensive across actor schema versions) ----------

    @staticmethod
    def _num(v) -> float:
        if isinstance(v, dict):
            v = v.get("value", 0)
        if isinstance(v, str):
            v = v.replace("$", "").replace(",", "").strip()
        try:
            return float(v or 0)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _bsr(cls, item: dict) -> int:
        for key in ("bestsellersRank", "bestSellersRank", "salesRank", "bsr"):
            v = item.get(key)
            if isinstance(v, list) and v:
                v = v[0].get("rank") if isinstance(v[0], dict) else v[0]
            n = cls._num(v)
            if n > 0:
                return int(n)
        return 0

    def _to_raw(self, item: dict, category: str | None) -> dict | None:
        asin = item.get("asin") or item.get("ASIN") or ""
        title = item.get("title") or item.get("name") or ""
        if not asin or not title:
            return None
        price = self._num(item.get("price"))
        if price <= 0:
            price = self._num(item.get("listPrice"))
        return {
            "asin": asin,
            "parent_asin": item.get("parentAsin") or asin,
            "title": title,
            "category": category or (item.get("breadCrumbs") or "unknown").split(" › ")[0]
                        .strip().lower().replace(" ", "_").replace("&", "and"),
            "price": round(price, 2),
            "bsr": self._bsr(item),
            "rating": self._num(item.get("stars") or item.get("rating")),
            "reviews_count": int(self._num(item.get("reviewsCount") or item.get("ratingsTotal"))),
            "sellers_count": int(self._num(item.get("offersCount") or item.get("sellers"))),
            "weight_oz": 0.0,                     # search results never carry weight
            "longest_side_in": 0.0,
            "source": self.name,
        }

    # ---------- Connector protocol ----------

    def search(self, term: str, category: str | None = None) -> list[dict]:
        q = urllib.parse.quote_plus(term)
        url = f"{self.marketplace}/s?k={q}"
        items = self._run_url_actor(f"apify|search|{term}|{category}",
                                    self.search_actor, url, self.max_items)
        out = [r for r in (self._to_raw(i, category) for i in items) if r]
        if not out:
            _warn(f"search '{term}' returned 0 mappable items")
        return out

    def best_sellers(self, category: str) -> list[dict]:
        url = self.bestseller_urls.get(category)
        if not url:                                # unmapped category — say so, skip
            _warn(f"no bestseller_urls mapping for '{category}' in config/discovery.json")
            return []
        items = self._run_url_actor(f"apify|bestsellers|{category}",
                                    self.search_actor, url, self.max_items)
        return [r for r in (self._to_raw(i, category) for i in items) if r]

    def autocomplete(self, term: str) -> list[str]:
        cached = self.cache.get(f"amz|auto|{term}")
        if cached is not None:
            return cached
        url = ("https://completion.amazon.com/api/2017/suggestions?mid=ATVPDKIKX0DER"
               f"&alias=aps&prefix={urllib.parse.quote_plus(term)}")
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                sugg = [s.get("value", "") for s in json.loads(r.read().decode())
                        .get("suggestions", [])][:5]
        except Exception as exc:
            _warn(f"autocomplete failed ({exc}) — continuing without variants")
            sugg = []
        if sugg:
            self.cache.put(f"amz|auto|{term}", sugg)
        return sugg

    def product(self, asin: str) -> dict | None:
        cached = self.cache.get(f"apify|product|{asin}")
        if cached is not None:
            return cached
        items = self._post_actor(self.detail_actor, {
            "categoryOrProductUrls": [{"url": f"{self.marketplace}/dp/{asin}"}],
            "maxItemsPerStartUrl": 1,
        })
        raw = self._to_raw(items[0], None) if items else None
        if raw:
            self.cache.put(f"apify|product|{asin}", raw)
        return raw

    def bsr_trend(self, asin: str) -> list[int]:
        return []                                  # no history without Keepa — honest blank

    def social_feed(self, platform: str, term: str) -> dict:
        if platform == "reddit" and self.reddit:
            return self.reddit.feed(term)
        return {"platform": platform, "term": term, "mentions_30d": 0,
                "growth_pct": 0.0, "top_phrases": [],
                "note": "no source for this platform yet (PHASES.md: TikTok/Pinterest via Apify)"}
