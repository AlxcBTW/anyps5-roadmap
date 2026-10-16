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
        self.assertEqual(mine.build_of("on main plus #1157 it reaches gameplay", "issue", 7), "main + #1157")

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

    def test_an_idless_issue_comment_uses_one_id_from_the_issue_title(self):
        issue = self.model.issues[60]
        self.assertGreater(len(self.model.issue_info[60]["titles"]), 1)
        self.assertFalse(self.model.issue_info[60]["tracker"])
        url = issue["comments"][0]["url"]
        blocks = mine.code_blocks_with_lead(issue["comments"][0]["body"])
        self.assertEqual(len(blocks), 2)
        self.assertEqual([lead for _, lead in blocks], ["On main, Windows 11, RTX 4080:"] * 2)
        title = self.model.titles["PPSA06001"]
        stops = [s for s in title["stops"] if s.get("via") == "log block" and s["url"] == url]
        self.assertEqual(len(stops), 1)
        evidence = [e for e in title["evidence"] if e["url"] == url and "(log block)" in e["note"]]
        self.assertEqual(len(evidence), 1)
        self.assertEqual(
            (
                evidence[0]["build"],
                evidence[0]["author"],
                evidence[0]["date"],
                evidence[0]["os"],
                evidence[0]["gpu"],
                evidence[0]["part"],
            ),
            ("main", "maria", "2026-10-06T10:00:00Z", "Windows", "NVIDIA", "comment"),
        )

    def test_tracker_comments_do_not_fall_back_to_the_issue_title(self):
        info = self.model.issue_info[61]
        self.assertTrue(info["tracker"])
        url = self.model.issues[61]["comments"][1]["url"]
        self.assertFalse(
            any(s.get("via") == "log block" and s["url"] == url for t in self.model.titles.values() for s in t["stops"])
        )
        self.assertFalse(self.model.titles["PPSA06101"]["assoc"].get(61, {}).get("url") == url)

    def test_idless_comments_do_not_infer_from_a_multi_id_issue_title(self):
        url = self.model.issues[62]["comments"][0]["url"]
        self.assertFalse(
            any(s.get("via") == "log block" and s["url"] == url for t in self.model.titles.values() for s in t["stops"])
        )

    def test_an_explicit_comment_id_wins_over_the_issue_title(self):
        url = self.model.issues[63]["comments"][0]["url"]
        chosen = self.model.titles["PPSA06302"]
        stops = [s for s in chosen["stops"] if s.get("via") == "log block" and s["url"] == url]
        self.assertEqual(len(stops), 1)
        self.assertFalse(
            any(s.get("via") == "log block" and s["url"] == url for s in self.model.titles["PPSA06301"]["stops"])
        )

    def test_title_fallback_is_limited_to_idless_issue_comments(self):
        text = "On main:\n```\nAGC graphics: source boundary must not infer a title\n```"
        sources = [
            ({"kind": "issue", "part": "body"}, self.model.issue_info[60]),
            ({"kind": "pr", "part": "comment"}, None),
            ({"kind": "pr", "part": "review"}, None),
            ({"kind": "discussion", "part": "comment"}, None),
            ({"kind": "fork", "part": "comment", "recipe": []}, None),
        ]
        for index, (partial, info) in enumerate(sources):
            url = f"https://example.test/source-boundary-{index}"
            self.model._mine_code_blocks(
                {"number": 60, "text": text, "url": url, "date": "2026-10-06T12:00:00Z", "author": "tester", **partial},
                info,
            )
            self.assertFalse(
                any(
                    s.get("via") == "log block" and s["url"] == url
                    for t in self.model.titles.values()
                    for s in t["stops"]
                )
            )

        placeholder_url = "https://example.test/placeholder-id"
        self.model._mine_code_blocks(
            {
                "kind": "issue",
                "part": "comment",
                "number": 60,
                "text": "PPSA00000\n```\nAGC graphics: placeholder must not trigger title fallback\n```",
                "url": placeholder_url,
                "date": "2026-10-06T12:01:00Z",
                "author": "tester",
            },
            self.model.issue_info[60],
        )
        self.assertFalse(
            any(
                s.get("via") == "log block" and s["url"] == placeholder_url
                for t in self.model.titles.values()
                for s in t["stops"]
            )
        )

    def test_a_nonfatal_yotei_summary_line_is_not_a_stop(self):
        url = "https://github.com/boykopovar/AnyPS5/issues/3751#issuecomment-6129225437"
        title = self.model.titles["PPSA26344"]
        self.assertFalse(any(s.get("via") == "log block" and s["url"] == url for s in title["stops"]))
        self.assertFalse(any(e["url"] == url and "(log block)" in e["note"] for e in title["evidence"]))

    def test_an_onimusha_build_warning_does_not_authorize_an_unspecified_log_lead(self):
        url = "https://github.com/boykopovar/AnyPS5/issues/6006#issuecomment-6179302597"
        title = self.model.titles["PPSA27836"]
        self.assertFalse(any(s.get("via") == "log block" and s["url"] == url for s in title["stops"]))
        self.assertFalse(any(e["url"] == url for e in title["evidence"]))

    def test_each_fallback_block_needs_its_own_build_lead(self):
        model = r.Model(self.raw, {"blockers": [], "titles": [], "not_blockers": []}, "example/AnyPS5", NOW)
        url = "https://example.test/per-block-leads"
        text = (
            "On current main:\n\n````text\nShaderRecompiler::Recompile: main-keyword lead failure\n````\n\n"
            "`main` 4c1de0c0c on Linux:\n````text\nShaderRecompiler::Recompile: commit-only lead failure\n````\n\n"
            "Build unspecified here:\n````text\nShaderRecompiler::Recompile: unqualified block failure\n````"
        )
        model._mine_code_blocks(
            {
                "kind": "issue",
                "part": "comment",
                "number": 60,
                "text": text,
                "url": url,
                "date": "2026-10-06T12:02:00Z",
                "author": "tester",
            },
            model.issue_info[60],
        )
        title = model.titles["PPSA06001"]
        stops = [s for s in title["stops"] if s.get("via") == "log block" and s["url"] == url]
        self.assertEqual(len(stops), 2)
        evidence = [e for e in title["evidence"] if e["url"] == url and "(log block)" in e["note"]]
        self.assertEqual([(e["build"], e["commit"]) for e in evidence], [("main", None), ("main", "4c1de0c0c")])

    def test_explicit_id_is_unchanged_without_a_build_lead(self):
        model = r.Model(self.raw, {"blockers": [], "titles": [], "not_blockers": []}, "example/AnyPS5", NOW)
        url = "https://example.test/explicit-id-no-build"
        model._mine_code_blocks(
            {
                "kind": "issue",
                "part": "comment",
                "number": 60,
                "text": "PPSA06001:\n```text\nAGC graphics: explicit-ID behavior remains unchanged\n```",
                "url": url,
                "date": "2026-10-06T12:03:00Z",
                "author": "tester",
            },
            model.issue_info[60],
        )
        stops = [s for s in model.titles["PPSA06001"]["stops"] if s.get("via") == "log block" and s["url"] == url]
        self.assertEqual(len(stops), 1)

    def test_fallback_with_a_local_patch_lead_stays_a_patched_build(self):
        model = r.Model(self.raw, {"blockers": [], "titles": [], "not_blockers": []}, "example/AnyPS5", NOW)
        url = "https://example.test/fallback-local-patches"
        model._mine_code_blocks(
            {
                "kind": "issue",
                "part": "comment",
                "number": 60,
                "text": "On main 4c1de0c0c with local patches:\n```text\nAGC graphics: patched fallback lead\n```",
                "url": url,
                "date": "2026-10-06T12:04:00Z",
                "author": "tester",
            },
            model.issue_info[60],
        )
        evidence = [e for e in model.titles["PPSA06001"]["evidence"] if e["url"] == url]
        self.assertEqual(
            [(e["build"], e["build_kind"], e["commit"]) for e in evidence],
            [("main + patches", "patched", "4c1de0c0c")],
        )

    def test_confidence_counts_independent_authors_on_main(self):
        conf = self.model.confidence(self.ghost)
        self.assertEqual(conf["stage"], "Presents")
        self.assertEqual(conf["authors"], ["alice", "bob"])
        self.assertEqual(conf["label"], "2 reports on main")
        self.assertNotIn("claim", conf)  # dave's Menus ran on PR #50's branch: not a claim about main
        # it is the stage off main, never the stage
        self.assertEqual(self.model.best_stage(self.ghost)["stage"], "Presents")
        self.assertIsNone(self.model.unverified_claim(self.ghost))
        branch = self.model.branch_stage(self.ghost)
        self.assertEqual((branch["stage"], branch["needs"], branch["patches"]), ("Menus", [50], False))

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
        self.assertEqual(stats["stops_from_log_blocks"], 3)
        self.assertEqual(stats["titles_with_two_or_more_reports"], 1)
        self.assertEqual(stats["links"]["closing"], 1)
        self.assertEqual(stats["links"]["xref"], 1)
        self.assertGreaterEqual(stats["evidence_by_part"]["review"], 2)
        self.assertEqual(stats["api"]["graphql_cost"], 6)
        html = r.render_html.Page(doc).render()
        self.assertIn("2 reports on main", html)


if __name__ == "__main__":
    unittest.main()
