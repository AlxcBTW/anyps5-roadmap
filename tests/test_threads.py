"""Fixture tests for the deep extraction: PR comments, reviews and review threads, builds,
fenced logs, confidence and issue-to-PR links. No network."""

import datetime as dt
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import roadmap as r  # noqa: E402
from anyps5_roadmap import mine  # noqa: E402

FIX = HERE / "fixtures"
NOW = dt.datetime(2026, 10, 10, 12, 0, tzinfo=dt.UTC)
GHOST = "PPSA01999"


class Rules(unittest.TestCase):
    def test_build_of_reads_main_and_branches(self):
        self.assertEqual(
            mine.build_of("Tested on current main after the merge: reaches the title screen", "pr", 7), "main"
        )
        self.assertEqual(mine.build_of("main at 262c031 shows the menu", "pr", 7), "main")
        self.assertEqual(mine.build_of("On main it crashes; with this PR it reaches the menu", "pr", 7), "PR #7")
        self.assertEqual(mine.build_of("reaches the menu", "pr", 7), "PR #7")
        self.assertEqual(mine.build_of("the domain at 1234567 is mapped", "pr", 7), "PR #7")
        self.assertEqual(mine.build_of("reaches the menu", "issue", 7), "main")
        self.assertEqual(mine.build_of("on main plus #1157 it reaches gameplay", "issue", 7), "main + patches")

    def test_a_named_branch_is_a_patched_build(self):
        line = "PPSA21567, on oneandonlydean's astrobot branch with an equivalent local export: it boots"
        self.assertEqual(mine.build_of(line, "issue", 1), "main + patches")
        self.assertEqual(mine.build_of("PPSA01999 boots fine on my audio branch.", "pr", 50), "PR #50")
        self.assertEqual(
            mine.build_of("on `main` de5e541d plus this PR, the game stops at start-up", "pr", 846), "PR #846"
        )
        self.assertEqual(mine.build_of("main + the patch from #12 reaches the menu", "issue", 1), "main + patches")
        self.assertEqual(mine.build_of("two titles plus three homebrew apps reach the menu", "issue", 1), "main")

    def test_code_blocks_and_their_last_error_line(self):
        text = (
            "PPSA01746 crashes:\n```text\nfoo\n  what():  AGC graphics: color views of several array slices "
            "are unsupported\nbar\n```\nthen\n~~~\nLowLevelFatalError [File:Unknown] [Line: 1234] "
            "RemoveFromOuterMap NumRemoved = 0\n~~~\n```\nunclosed"
        )
        blocks = mine.code_blocks(text)
        self.assertEqual([len(b) for b in blocks], [3, 1, 1])
        self.assertEqual(mine.block_stop(blocks[0])["key"], "color views of several array slices are unsupported")
        crash = mine.block_stop(blocks[1])
        self.assertEqual(crash["family"], "crash")
        self.assertEqual(
            crash["display"], "LowLevelFatalError [File:Unknown] [Line: N] RemoveFromOuterMap NumRemoved = 0"
        )
        self.assertIsNone(mine.block_stop(blocks[2]))
        # crash words in prose are not stops
        self.assertEqual(mine.code_blocks("A Segmentation fault happens on boot."), [])

    def test_bots(self):
        self.assertTrue(mine.is_bot("github-actions[bot]"))
        self.assertTrue(mine.is_bot("dependabot"))
        self.assertFalse(mine.is_bot("alice"))


class DeepModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = json.loads((FIX / "threads_raw.json").read_text(encoding="utf-8"))
        cls.raw = raw
        cls.model = r.Model(raw, {"blockers": [], "titles": [], "not_blockers": []}, "example/AnyPS5", NOW)
        cls.ghost = cls.model.titles[GHOST]

    def test_pr_comments_reviews_and_review_threads_are_mined_with_author_and_build(self):
        ev = {(e["author"], e["part"]): e for e in self.ghost["evidence"] if e["origin"] == "mined"}
        self.assertEqual((ev[("dave", "comment")]["stage"], ev[("dave", "comment")]["build"]), ("Menus", "PR #50"))
        self.assertEqual((ev[("erin", "review")]["stage"], ev[("erin", "review")]["build"]), ("First draw", "main"))
        self.assertEqual((ev[("frank", "review")]["stage"], ev[("frank", "review")]["build"]), ("Starts", "PR #50"))
        self.assertEqual(ev[("bob", "comment")]["os"], "Linux")

    def test_bot_comments_are_skipped(self):
        self.assertFalse(any((e.get("author") or "").endswith("[bot]") for e in self.ghost["evidence"]))

    def test_a_fenced_log_gives_the_stop_when_the_comment_names_one_title(self):
        stops = [s for s in self.ghost["stops"] if s.get("via") == "log block"]
        self.assertEqual(len(stops), 1)
        self.assertEqual(stops[0]["url"], "https://github.com/example/AnyPS5/issues/40#issuecomment-401")
        # the stop matches blocker 40's signature, so the chain starts there
        self.assertEqual([s["blocker"] for s in self.ghost["chain"]][:1], ["40"])
        self.assertEqual(self.ghost["chain"][0]["why"], "latest recorded stop matches its signature")

    def test_confidence_counts_independent_authors_on_main(self):
        conf = self.model.confidence(self.ghost)
        self.assertEqual(conf["stage"], "Presents")
        self.assertEqual(conf["authors"], ["alice", "bob"])
        self.assertEqual(conf["label"], "2 reports on main")
        self.assertEqual(conf["claim"], {"stage": "Menus", "reports_on_main": 0, "reports_on_branches": 1})
        # the claim stays a claim: confidence never promotes it
        self.assertEqual(self.model.best_stage(self.ghost)["stage"], "Presents")
        self.assertEqual(self.model.unverified_claim(self.ghost)["stage"], "Menus")

    def test_links_record_how_they_are_known(self):
        b40 = {p["ref"]: p for p in self.model.blockers["40"]["prs"]}
        self.assertEqual((b40["#51"]["link"], b40["#51"]["via"]), ("fixes", ["closing"]))
        b41 = {p["ref"]: p for p in self.model.blockers["41"]["prs"]}
        self.assertEqual((b41["#50"]["link"], b41["#50"]["via"]), ("mentions", ["xref"]))

    def test_roadmap_json_carries_confidence_and_extraction_stats(self):
        upstream = r.Upstream(None, "HEAD", "example/AnyPS5", fetch=False, log=lambda m: None, network=False)
        doc = r.assemble(self.model, {"isa": None, "hle": None, "pm4": None, "registers": []}, self.raw, upstream, NOW)
        ghost = next(t for t in doc["titles"] if t["id"] == GHOST)
        self.assertEqual(ghost["confidence"]["label"], "2 reports on main")
        stats = doc["stats"]
        self.assertEqual(stats["stops_from_log_blocks"], 1)
        self.assertEqual(stats["titles_with_two_or_more_reports"], 1)
        self.assertEqual(stats["links"]["closing"], 1)
        self.assertEqual(stats["links"]["xref"], 1)
        self.assertGreaterEqual(stats["evidence_by_part"]["review"], 2)
        self.assertEqual(stats["api"]["graphql_cost"], 6)
        html = r.render_html.Page(doc).render()
        self.assertIn("2 reports on main", html)


if __name__ == "__main__":
    unittest.main()
