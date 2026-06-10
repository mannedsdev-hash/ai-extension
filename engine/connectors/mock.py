"""MockConnector — deterministic fake marketplace.

Seeded from md5 of the query (NOT python hash(), which is salted per
process), so the same run inputs always produce the same catalog. This makes
the whole engine reproducible and testable with zero API spend. Replace with
the apify connector for real data; the shapes are identical.
"""
from __future__ import annotations

import hashlib
import random

BRANDS = ["Norvik", "HoldFast", "Brioka", "TidyPeak", "Cervo", "Lumare",
          "Pakka", "Quenta", "Strivo", "Maven&Co"]
VARIANTS = ["2-Pack", "Large", "Slim", "Adjustable", "with Lid", "Bamboo",
            "Stainless", "Foldable", "XL", "Mini"]
CATEGORIES = ["kitchen", "home_and_kitchen", "office_products", "pet_supplies",
              "toys_and_games", "sports_and_outdoors", "baby_products"]
PRICE_BANDS = {"kitchen": (12, 45), "home_and_kitchen": (15, 60),
               "office_products": (9, 35), "pet_supplies": (10, 40),
               "toys_and_games": (12, 50), "sports_and_outdoors": (15, 70),
               "baby_products": (14, 55)}
PLATFORM_PHRASES = {
    "tiktok": ["this changed my kitchen", "restock with me", "#amazonfinds"],
    "reddit": ["does anyone make a decent", "I wish there was", "recommend me"],
    "pinterest": ["small space ideas", "organization hacks", "aesthetic setup"],
}


def _rng(*parts: str) -> random.Random:
    digest = hashlib.md5("|".join(parts).encode()).hexdigest()
    return random.Random(int(digest[:12], 16))


class MockConnector:
    name = "mock"

    def __init__(self) -> None:
        self._cache: dict[str, dict] = {}   # asin -> product dict

    # ---------- product generation ----------

    def _make_products(self, query: str, category: str | None, n: int,
                       bsr_lo: int, bsr_hi: int) -> list[dict]:
        rng = _rng("catalog", query, category or "any")
        out: list[dict] = []
        parent = None
        for i in range(n):
            asin = "B0" + hashlib.md5(f"{query}|{category}|{i}".encode()).hexdigest()[:8].upper()
            cat = category or rng.choice(CATEGORIES)
            lo, hi = PRICE_BANDS.get(cat, (10, 50))
            # every 3rd item is a variant of the previous one (shared parent)
            parent = parent if (i % 3 == 2 and parent) else asin
            bsr = int(rng.uniform(bsr_lo ** 0.5, bsr_hi ** 0.5) ** 2)
            reviews = max(0, int(60000 / (bsr ** 0.55) * rng.uniform(0.4, 1.8)))
            p = {
                "asin": asin,
                "parent_asin": parent,
                "title": f"{rng.choice(BRANDS)} {query.title()} {rng.choice(VARIANTS)}",
                "category": cat,
                "price": round(rng.uniform(lo, hi), 2),
                "bsr": bsr,
                "rating": round(rng.uniform(3.6, 4.8), 1),
                "reviews_count": reviews,
                "sellers_count": rng.randint(1, 24),
                "weight_oz": round(rng.uniform(3, 70), 1),
                "longest_side_in": round(rng.uniform(4, 24), 1),
                "source": self.name,
            }
            self._cache[asin] = p
            out.append(p)
        return out

    # ---------- Connector protocol ----------

    def search(self, term: str, category: str | None = None) -> list[dict]:
        return self._make_products(term, category, n=8, bsr_lo=800, bsr_hi=160000)

    def best_sellers(self, category: str) -> list[dict]:
        items = self._make_products(f"bestsellers {category}", category,
                                    n=10, bsr_lo=40, bsr_hi=6000)
        return sorted(items, key=lambda p: p["bsr"])

    def autocomplete(self, term: str) -> list[str]:
        rng = _rng("auto", term)
        forms = [f"{term} organizer", f"{term} for small spaces", f"mini {term}",
                 f"{term} set", f"{term} holder", f"large {term}"]
        rng.shuffle(forms)
        return forms[:3]

    def product(self, asin: str) -> dict | None:
        if asin in self._cache:
            return self._cache[asin]
        made = self._make_products(f"asin {asin}", None, n=1, bsr_lo=500, bsr_hi=80000)
        made[0]["asin"] = asin
        made[0]["parent_asin"] = asin
        self._cache[asin] = made[0]
        return made[0]

    def bsr_trend(self, asin: str) -> list[int]:
        rng = _rng("trend", asin)
        base = self._cache.get(asin, {}).get("bsr", rng.randint(1000, 80000))
        shape = rng.choice(["growing", "growing", "peak", "flat", "declining"])
        slope = {"growing": -0.09, "peak": -0.01, "flat": 0.0, "declining": 0.10}[shape]
        series, cur = [], base * (1 - slope * 8)
        for _ in range(8):  # 8 weekly points, oldest -> newest
            cur = max(20, cur * (1 + slope + rng.uniform(-0.02, 0.02)))
            series.append(int(cur))
        return series

    def social_feed(self, platform: str, term: str) -> dict:
        rng = _rng("social", platform, term)
        growth = round(rng.uniform(-10, 60), 1)
        return {
            "platform": platform,
            "term": term,
            "mentions_30d": int(rng.uniform(40, 9000)),
            "growth_pct": growth,
            "top_phrases": rng.sample(PLATFORM_PHRASES.get(platform, ["trending"]),
                                      k=min(2, len(PLATFORM_PHRASES.get(platform, ["x"])))),
        }
