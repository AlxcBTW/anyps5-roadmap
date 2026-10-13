"""Tests for the change feed (anyps5_roadmap/feed.py). No network: fetches go to a fake."""

import copy
import datetime as dt
import io
import json
import re
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import roadmap as r  # noqa: E402
from anyps5_roadmap import feed  # noqa: E402

FIX = HERE / "fixtures"
NOW = dt.datetime(2026, 10, 10, 12, 0, tzinfo=dt.UTC)
PAGE = "https://alxcbtw.github.io/anyps5-roadmap/"
RFC3339 = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
ITEM_KEYS = {"id", "url", "external_url", "title", "content_html", "content_text", "summary", "image", "banner_image"}
ITEM_KEYS |= {"date_published", "date_modified", "authors", "tags", "language", "attachments"}  # JSON Feed 1.1


def build_doc(curated: dict, now: dt.datetime = NOW) -> dict:
    raw = json.loads((FIX / "raw.json").read_text(encoding="utf-8"))
    model = r.Model(raw, curated, "example/AnyPS5", now)
    upstream = r.Upstream(None, "HEAD", "example/AnyPS5", fetch=False, log=lambda m: None, network=False)
    return r.assemble(model, {"isa": None, "hle": None, "pm4": None, "registers": []}, raw, upstream, now)


def old_item(n: int) -> dict:
    stamp = f"2026-10-0{1 + n // 24}T{n % 24:02d}:41:00Z"
    return {"id": stamp, "content_text": f"change {n}", "date_published": stamp}


class Feed(unittest.TestCase):
    def setUp(self):
        self.curated = r.load_curated(FIX / "curated.json")
        self.base = build_doc(self.curated)
        changed = copy.deepcopy(self.curated)
        # #10 is fixed, and Stray gets a curated Menus stage
        next(b for b in changed["blockers"] if b["id"] == "10")["status"] = "resolved"
        changed["titles"].append(
            {
                "id": "PPSA02100",
                "evidence": [
                    {"stage": "Menus", "build": "main", "url": "https://github.com/example/AnyPS5/issues/40"},
                ],
            }
        )
        self.head = build_doc(changed, NOW + dt.timedelta(hours=1))

    def test_a_build_that_changes_things_adds_one_item_in_plain_sentences(self):
        item = feed.item(self.base, self.head)
        self.assertEqual(item["id"], "2026-10-10T13:00:00Z")
        self.assertEqual(item["date_published"], item["id"])
        self.assertEqual(item["title"], "1 blocker resolved, 1 ranking change, 2 games changed")
        self.assertEqual(
            item["content_text"].splitlines(),
            [
                "#10 “Packed pixel ancillary word” is resolved.",
                "#11 “Kena: Bridge of Spirits (PPSA01746): layered draw aborts” moved up from No. 5 to No. 4 "
                "(score 1 → 6).",
                "Kena: Bridge of Spirits (PPSA01746) now stops at #11 “Kena: Bridge of Spirits (PPSA01746): "
                "layered draw aborts” (was #10).",
                "Stray (PPSA02100) went from Starts to Menus.",
                "Stray (PPSA02100) has no known stop left (was #10).",
            ],
        )
        # pr-30 moves from No. 4 to No. 3 only because #10 left: not listed, and #10 is not listed twice
        types = [(c["type"], c.get("title") or c.get("blocker")) for c in item["_anyps5"]["changes"]]
        self.assertEqual(
            types,
            [("resolved", "10"), ("moved", "11"), ("stop", "PPSA01746"), ("stage", "PPSA02100"), ("stop", "PPSA02100")],
        )
        self.assertEqual(item["_anyps5"]["since"], self.base["generated_at"])

    def test_against_a_build_from_before_games_only_new_merges_are_listed(self):
        old = copy.deepcopy(self.base)
        old["schema_version"] = 1
        del old["games"], old["identity"]
        for t in old["titles"]:
            t.pop("game", None)
            if t["id"] == "PPSA01802":
                t["name"] = "Kena"  # the page showed two games then
        item = feed.item(old, self.base | {"generated_at": "2026-10-10T13:00:00Z"})
        self.assertEqual(item["title"], "1 game merged")
        (record,) = item["_anyps5"]["changes"]
        self.assertEqual(
            (record["type"], record["game"], record["titles"]),
            ("merged", "kena-bridge-of-spirits", ["PPSA01746", "PPSA01802"]),
        )
        self.assertTrue(
            item["content_text"].startswith("Kena: Bridge of Spirits (PPSA01746) now holds PPSA01746 and PPSA01802")
        )

    def test_each_change_links_its_blocker_or_title_on_the_page(self):
        item = feed.item(self.base, self.head)
        links = re.findall(r'<li><a href="([^"]+)">([^<]+)</a>', item["content_html"])
        self.assertEqual(
            links,
            [
                # resolved blockers are no longer on the page, so they link upstream
                ("https://github.com/example/AnyPS5/issues/10", "#10"),
                (PAGE + "#b-11", "#11"),
                (PAGE + "#g-PPSA01746", "Kena: Bridge of Spirits (PPSA01746)"),
                (PAGE + "#g-PPSA02100", "Stray (PPSA02100)"),
                (PAGE + "#g-PPSA02100", "Stray (PPSA02100)"),
            ],
        )
        self.assertEqual([c["url"] for c in item["_anyps5"]["changes"]], [url for url, _ in links])

    def test_no_change_adds_no_item(self):
        same = build_doc(self.curated, NOW + dt.timedelta(hours=1))
        self.assertIsNone(feed.item(self.base, same))
        self.assertIsNone(feed.item(self.head, self.head))  # the live build itself
        previous = {"items": [old_item(1), old_item(0)]}
        self.assertEqual(feed.build(same, self.base, previous)["items"], previous["items"])

    def test_the_feed_keeps_the_newest_items_up_to_the_cap(self):
        previous = feed.build(self.base, None, {"items": [old_item(n) for n in range(feed.MAX_ITEMS + 5, 0, -1)]})
        self.assertEqual(len(previous["items"]), feed.MAX_ITEMS)
        out = feed.build(self.head, self.base, previous)
        ids = [i["id"] for i in out["items"]]
        self.assertEqual(len(ids), feed.MAX_ITEMS)
        self.assertEqual(ids[0], self.head["generated_at"])
        self.assertEqual(ids[1:], [i["id"] for i in previous["items"][:-1]])
        # running the same build again replaces its item instead of adding a second one
        again = feed.build(self.head, self.base, out)
        self.assertEqual([i["id"] for i in again["items"]], ids)

    def test_a_large_diff_lists_the_first_changes_and_counts_the_rest(self):
        cap, feed.MAX_CHANGES = feed.MAX_CHANGES, 2
        try:
            item = feed.item(self.base, self.head)
        finally:
            feed.MAX_CHANGES = cap
        self.assertEqual(len(item["content_text"].splitlines()), 3)
        self.assertTrue(item["content_text"].endswith("And 3 more changes, not listed here."))
        self.assertEqual(item["_anyps5"]["not_listed"], 3)
        self.assertEqual(len(item["_anyps5"]["changes"]), 2)

    def test_the_feed_is_a_json_feed_1_1(self):
        out = feed.build(self.head, self.base, None)
        self.assertEqual(out["version"], "https://jsonfeed.org/version/1.1")
        self.assertEqual(out["feed_url"], PAGE + "feed.json")
        self.assertTrue(out["title"] and out["home_page_url"] == PAGE)
        for item in out["items"]:
            self.assertIsInstance(item["id"], str)
            self.assertTrue(item.get("content_html") or item.get("content_text"))
            self.assertRegex(item["date_published"], RFC3339)
            custom = [k for k in item if k not in ITEM_KEYS]
            self.assertTrue(all(k.startswith("_") for k in custom), custom)
        json.dumps(out)  # serialisable as is


class Publish(unittest.TestCase):
    """publish() against a fake live site."""

    def setUp(self):
        curated = r.load_curated(FIX / "curated.json")
        self.base = build_doc(curated)
        changed = copy.deepcopy(curated)
        next(b for b in changed["blockers"] if b["id"] == "10")["status"] = "resolved"
        self.head = build_doc(changed, NOW + dt.timedelta(hours=1))
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "site"
        self.cache = Path(self.tmp.name) / "cache"
        self.log = io.StringIO()

    def tearDown(self):
        self.tmp.cleanup()

    def site(self, **files):
        """A fake http_get: files maps 'roadmap.json' / 'feed.json' to a document, or to an exception."""

        def get(url: str) -> bytes:
            name = url.removeprefix(PAGE).split("?")[0]
            if name not in files:
                raise urllib.error.HTTPError(url, 404, "Not Found", None, io.BytesIO())
            body = files[name]
            if isinstance(body, Exception):
                raise body
            return json.dumps(body).encode("utf-8")

        return get

    def publish(self, network=True, **files):
        path = feed.publish(
            self.head, self.out, self.cache, network, lambda m: print(m, file=self.log), self.site(**files)
        )
        return json.loads(path.read_text(encoding="utf-8")) if path else None

    def test_first_run_starts_the_feed_from_the_live_roadmap(self):
        out = self.publish(**{"roadmap.json": self.base})
        self.assertEqual([i["id"] for i in out["items"]], [self.head["generated_at"]])
        self.assertIn("is resolved.", out["items"][0]["content_text"])
        self.assertEqual(json.loads((self.cache / "feed.json").read_text(encoding="utf-8")), out)

    def test_items_of_the_live_feed_are_carried_over(self):
        out = self.publish(**{"roadmap.json": self.base, "feed.json": {"items": [old_item(1), old_item(0)]}})
        self.assertEqual(
            [i["id"] for i in out["items"]], [self.head["generated_at"], old_item(1)["id"], old_item(0)["id"]]
        )

    def test_no_network_writes_no_feed(self):
        self.assertIsNone(self.publish(network=False, **{"roadmap.json": self.base}))
        self.assertFalse((self.out / "feed.json").exists())
        self.assertIn("skipped", self.log.getvalue())

    def test_an_unreadable_live_roadmap_keeps_the_items_without_a_new_one(self):
        down = urllib.error.URLError("timed out")
        out = self.publish(**{"roadmap.json": down, "feed.json": {"items": [old_item(0)]}})
        self.assertEqual([i["id"] for i in out["items"]], [old_item(0)["id"]])
        out = self.publish(**{"roadmap.json": {"schema_version": 0}, "feed.json": {"items": [old_item(0)]}})
        self.assertEqual([i["id"] for i in out["items"]], [old_item(0)["id"]])
        self.assertIn("could not be compared", self.log.getvalue())

    def test_an_offline_build_keeps_no_copy(self):
        path = feed.publish(self.head, self.out, None, True, lambda m: None, self.site(**{"roadmap.json": self.base}))
        self.assertTrue(path.exists())
        self.assertFalse(self.cache.exists())

    def test_an_unreadable_live_feed_falls_back_to_the_cached_copy(self):
        self.cache.mkdir(parents=True)
        (self.cache / "feed.json").write_text(json.dumps({"items": [old_item(0)]}), encoding="utf-8")
        out = self.publish(**{"roadmap.json": self.base, "feed.json": urllib.error.URLError("timed out")})
        self.assertEqual([i["id"] for i in out["items"]], [self.head["generated_at"], old_item(0)["id"]])


class Links(unittest.TestCase):
    def test_the_page_and_llms_txt_point_to_the_feed(self):
        doc = build_doc(r.load_curated(FIX / "curated.json"))
        page = r.render_html.Page(doc).render()
        self.assertIn('<link rel="alternate" type="application/feed+json" href="feed.json"', page)
        self.assertIn('<dt><a class="mono" href="feed.json">feed.json</a></dt>', page)
        self.assertIn("[feed.json](feed.json)", r.render_llms(doc))


if __name__ == "__main__":
    unittest.main()
