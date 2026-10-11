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

    def test_a_line_that_links_a_ci_run_does_not_name_the_os_of_title_runs(self):
        text = (
            "- Windows was last built on the earlier base (fork run [1](https://github.com/someone/AnyPS5/actions/runs/1): "
            "Windows 511/511).\n- Linux (CachyOS), RTX 3080: full ctest passes."
        )
        self.assertEqual(r.classify(r.OS_RULES, text), "Windows")  # Windows is the first OS rule
        self.assertEqual(r.classify(r.OS_RULES, mine.run_text(text)), "Linux")
        # an OS named without a CI run link still counts
        self.assertEqual(mine.run_text("Windows 11, MinGW: ctest passes"), "Windows 11, MinGW: ctest passes")

    def test_a_parenthesis_after_the_description_restates_it(self):
        line = "This measures something different from the description (PPSA01317 menu load, warm caches): 007 boots."
        spans = mine.restated_spans(line)
        self.assertEqual([line[a:b] for a, b in spans], ["(PPSA01317 menu load, warm caches)"])
        self.assertEqual(r.stage_in(mine.blank(line, spans), line.find("007"))[0], "Starts")
        for line in ("Hollow Knight (PPSA12544) reaches the main menu", "As the PR description says: PPSA01317 menu"):
            with self.subTest(line=line):
                self.assertEqual(mine.restated_spans(line), [])
        self.assertTrue(mine.restated_spans("unlike this PR's description (PPSA01317 menu)"))

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

    def test_a_review_of_one_comment_drops_only_that_comment(self):
        raw = json.loads((FIX / "threads_raw.json").read_text(encoding="utf-8"))
        review = {
            "title": GHOST,
            "claim": "Menus",
            "claim_url": "https://github.com/example/AnyPS5/pull/50#issuecomment-501",
            "verdict": "suppressed",
            "quote": "With this PR, Ghostrunner (PPSA01999) reaches the main menu.",
            "reason": "fixture",
        }
        curated = {"blockers": [], "titles": [], "not_blockers": [], "stage_reviews": [review]}
        m = r.Model(raw, curated, "example/AnyPS5", NOW)
        urls = {e["url"] for e in m.titles[GHOST]["evidence"]}
        self.assertNotIn("https://github.com/example/AnyPS5/pull/50#issuecomment-501", urls)
        self.assertIn("https://github.com/example/AnyPS5/pull/50#discussion_r503", urls)  # same PR, other comment
        self.assertIsNone(m.unverified_claim(m.titles[GHOST]))
        # without an anchor the whole thread is dropped, as before
        review["claim_url"] = "https://github.com/example/AnyPS5/pull/50"
        m = r.Model(raw, curated, "example/AnyPS5", NOW)
        self.assertFalse(any("/pull/50" in e["url"] for e in m.titles[GHOST]["evidence"]))

    def test_title_runs_take_their_os_from_the_text_not_from_a_ci_run(self):
        ev = [e for e in self.model.titles["PPSA01888"]["evidence"] if e["url"].endswith("/pull/52")]
        self.assertEqual(
            [(e["stage"], e["os"], e["gpu"], e["build"]) for e in ev], [("Converts", "Linux", "NVIDIA", "main")]
        )

    def test_a_title_named_only_in_a_restated_description_gets_no_stage(self):
        self.assertEqual(self.model.titles["PPSA01777"]["evidence"], [])
        self.assertIsNone(self.model.unverified_claim(self.model.titles["PPSA01777"]))
        self.assertTrue(self.model.titles["PPSA01777"]["mentions"])  # still linked to the PR
        # the restated menu is not read for the title the comment is about either
        comment = [e for e in self.model.titles["PPSA01888"]["evidence"] if e["url"].endswith("#issuecomment-521")]
        self.assertEqual(comment, [])

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
