"""Covers: reading a store concept page, the lookup budget, the Steam fallback and overrides. No network."""

import datetime as dt
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from anyps5_roadmap import images  # noqa: E402

NOW = dt.datetime(2026, 10, 13, 12, 0, tzinfo=dt.UTC)
CDN = "https://image.api.playstation.com/vulcan/ap/rnd/202202/2816/"


def media(role, name, kind="IMAGE"):
    return {"__typename": "Media", "role": role, "type": kind, "url": CDN + name}


def page(concept: str, own: list, product: list | None = None, other: list | None = None) -> str:
    state = {
        "cache": {
            f"Concept:{concept}": {
                "id": concept,
                "defaultProduct": {"__ref": f"Product:UP0001-PPSA00001_00-{concept}"},
                "media": own,
            },
            f"Product:UP0001-PPSA00001_00-{concept}": {"media": product or []},
            "Product:UP0001-PPSA00002_00-ADDON": {"media": other or []},
        }
    }
    return (
        '<html><script id="env:1" type="application/json">{not json}</script>'
        f'<script id="env:2" type="application/json">{json.dumps(state)}</script></html>'
    )


class ConceptPage(unittest.TestCase):
    def test_the_concepts_own_art_by_use(self):
        html = page(
            "201930",
            [media("PREVIEW", "a.mp4", "VIDEO"), media("MASTER", "square.png"), media("GAMEHUB_COVER_ART", "wide.jpg")],
            product=[media("PORTRAIT_BANNER", "tall.jpg"), media("MASTER", "product-square.png")],
            other=[media("MASTER", "addon.png")],
        )
        self.assertEqual(
            images.concept_media(html, "201930"),
            {"square": CDN + "square.png", "wide": CDN + "wide.jpg", "portrait": CDN + "tall.jpg"},
        )

    def test_only_the_sony_cdn_and_nothing_from_other_products(self):
        html = page(
            "1",
            [{"role": "MASTER", "type": "IMAGE", "url": "https://evil.example/x.png"}],
            other=[media("MASTER", "a.png")],
        )
        self.assertEqual(images.concept_media(html, "1"), {})
        self.assertEqual(images.concept_media("<html>error</html>", "1"), {})


class Refresh(unittest.TestCase):
    def fake(self, pages: dict, steam: dict | None = None):
        calls = []

        def fetch(url, headers):
            calls.append(url)
            if url.startswith(images.WIKIDATA_SPARQL):
                rows = [{"concept": {"value": c}, "steam": {"value": a}} for c, a in (steam or {}).items()]
                return json.dumps({"results": {"bindings": rows}}).encode()
            concept = url.rsplit("/", 1)[1]
            if concept not in pages:
                raise images.urllib.error.URLError("down")
            return pages[concept].encode()

        return fetch, calls

    def test_found_missed_failed_and_steam(self):
        fetch, calls = self.fake(
            {"1": page("1", [media("MASTER", "one.png")]), "2": page("2", [])}, steam={"2": "813230"}
        )
        cache = {"version": 1, "concepts": {}}
        out = images.refresh(["1", "2", "3"], cache, NOW, log=lambda m: None, fetch=fetch, sleep=lambda s: None)
        self.assertEqual((out["read"], out["found"], out["failed"], out["steam"]), (3, 1, 1, 1))
        store = cache["concepts"]
        self.assertEqual(store["1"]["square"], CDN + "one.png")
        self.assertEqual(store["2"]["source"], "steam")
        self.assertTrue(store["2"]["portrait"].endswith("/813230/library_600x900.jpg"))
        self.assertNotIn("3", store)  # a failure keeps whatever was cached, so the next run tries again
        # a fresh cache is not read again
        calls.clear()
        images.refresh(
            ["1", "2"], cache, NOW + dt.timedelta(days=1), log=lambda m: None, fetch=fetch, sleep=lambda s: None
        )
        self.assertEqual(calls, [])

    def test_the_time_budget_leaves_the_rest_for_the_next_run(self):
        fetch, calls = self.fake({c: page(c, [media("MASTER", f"{c}.png")]) for c in "123456"})
        ticks = iter(range(0, 1000, 100))
        out = images.refresh(
            list("123456"),
            {"concepts": {}},
            NOW,
            log=lambda m: None,
            fetch=fetch,
            budget_s=150,
            clock=lambda: next(ticks),
            sleep=lambda s: None,
        )
        # the clock reads 0 at the start, 100 before the first round and 200 before the second: one round
        self.assertEqual((out["read"], out["left"]), (images.WORKERS, 6 - images.WORKERS))


class Choice(unittest.TestCase):
    cache = {
        "concepts": {
            "10": {"square": CDN + "s.png", "wide": CDN + "w.jpg", "source": "playstation", "checked": "x"},
            "20": {
                "portrait": "https://steam/p.jpg",
                "wide": "https://steam/h.jpg",
                "source": "steam",
                "steam_app": "5",
            },
            "30": {"miss": True},
        }
    }

    def test_store_then_steam_then_none(self):
        sony = images.image_for(["10"], None, self.cache)
        self.assertEqual(
            (sony["square"], sony["sizing"], sony["page"]), (CDN + "s.png", "w", images.CONCEPT_URL.format("10"))
        )
        steam = images.image_for(["30", "20"], None, self.cache)
        self.assertEqual((steam["source"], steam["square"], steam["sizing"]), ("Steam", None, None))
        self.assertIsNone(images.image_for(["30"], None, self.cache))
        self.assertIsNone(images.image_for([], None, self.cache))

    def test_a_person_can_set_or_remove_the_cover(self):
        self.assertIsNone(images.image_for(["10"], {"image": None}, self.cache))
        own = images.image_for(
            ["10"], {"image": {"url": "https://example.org/c.png", "page": "https://example.org"}}, {}
        )
        self.assertEqual(
            (own["square"], own["source"], own["sizing"]), ("https://example.org/c.png", "data/games.json", None)
        )


if __name__ == "__main__":
    unittest.main()
