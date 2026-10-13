"""Evaluation of titles and games: qualifying builds, the stage, confidence, the timeline, evidence that is
quoted or repeated, and the ranking counted by game. No network."""

import datetime as dt
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from anyps5_roadmap import evaluate  # noqa: E402
from anyps5_roadmap.assemble import game_records  # noqa: E402
from anyps5_roadmap.identity import parse_catalog  # noqa: E402
from anyps5_roadmap.model import Model  # noqa: E402

NOW = dt.datetime(2026, 10, 13, 12, 0, tzinfo=dt.UTC)
REPO = "example/AnyPS5"
MERGED = {3497}


def merged(n):
    return n in MERGED


def ev(stage, date, author="a", origin="mined", build_kind="main", prs=(), url=None, quote=None, build=None):
    return {
        "stage": stage,
        "date": date,
        "author": author,
        "origin": origin,
        "build_kind": build_kind if origin == "mined" else None,
        "build": build or ("main" if build_kind == "main" else "x"),
        "prs": list(prs),
        "url": url or f"https://github.com/{REPO}/issues/1#{stage}-{date}-{author}",
        "quote": quote,
    }


class Rules(unittest.TestCase):
    def test_only_main_or_merged_prs_count(self):
        self.assertTrue(evaluate.on_main(ev("Starts", "2026-10-01"), merged))
        self.assertTrue(evaluate.on_main(ev("Starts", "2026-10-01", build_kind="prs", prs=[3497]), merged))
        self.assertFalse(evaluate.on_main(ev("Starts", "2026-10-01", build_kind="prs", prs=[3497, 12]), merged))
        self.assertFalse(evaluate.on_main(ev("Starts", "2026-10-01", build_kind="patched"), merged))
        # curated labels: "main + #3497" counts once #3497 is merged; patches never
        self.assertTrue(evaluate.on_main({"build": "main + #3497"}, merged))
        self.assertFalse(evaluate.on_main({"build": "main + local patches"}, merged))

    def test_best_stage_skips_branches_and_claims(self):
        evidence = [
            ev("Starts", "2026-09-01"),
            ev("Presents", "2026-09-02", build_kind="patched"),
            ev("First draw", "2026-09-03", build_kind="prs", prs=[3497]),
            ev("Menus", "2026-09-04"),  # a claim: Menus and higher need a person's review
        ]
        best = evaluate.best_stage(evidence, merged)
        self.assertEqual((best["stage"], best["verified"]), ("First draw", False))
        self.assertEqual(evaluate.unverified_claim(evidence, best)["stage"], "Menus")

    def test_a_curated_fact_supersedes_older_mined_reports_only(self):
        evidence = [
            ev("Presents", "2026-09-01", author="x"),
            ev("Starts", "2026-10-01", origin="curated"),
        ]
        self.assertEqual(evaluate.best_stage(evidence, merged)["stage"], "Starts")
        evidence.append(ev("Presents", "2026-10-05", author="y"))
        best = evaluate.best_stage(evidence, merged)
        self.assertEqual((best["stage"], best["author"]), ("Presents", "y"))

    def test_confidence_levels(self):
        one = [ev("Presents", "2026-10-01", author="a")]
        two = one + [ev("Presents", "2026-10-02", author="b"), ev("Presents", "2026-10-03", author="b")]
        hand = two + [ev("Menus", "2026-10-04", origin="curated")]
        self.assertEqual(evaluate.confidence([], merged)["level"], "none")
        self.assertEqual(
            (evaluate.confidence(one, merged)["level"], evaluate.confidence(one, merged)["label"]),
            ("reported", "1 report on main"),
        )
        c2 = evaluate.confidence(two, merged)
        self.assertEqual(
            (c2["level"], c2["label"], c2["last_seen"]), ("corroborated", "2 reports on main", "2026-10-03")
        )
        self.assertEqual(evaluate.confidence(hand, merged)["label"], "Checked by hand")

    def test_timeline_lists_each_rise(self):
        evidence = [
            ev("Converts", "2026-08-01"),
            ev("Starts", "2026-08-20"),
            ev("Converts", "2026-09-01"),
            ev("Presents", "2026-09-10", build_kind="patched"),  # not on main: no rise
            ev("Presents", "2026-10-01"),
        ]
        steps = [(t["date"], t["stage"]) for t in evaluate.timeline(evidence, merged)]
        self.assertEqual(steps, [("2026-08-01", "Converts"), ("2026-08-20", "Starts"), ("2026-10-01", "Presents")])

    def test_the_stage_off_main_and_what_it_needs(self):
        evidence = [
            ev("Presents", "2026-10-01"),
            ev("Ingame", "2026-10-02", author="b", build_kind="patched", prs=[12]),
            ev("Ingame", "2026-10-03", author="c", build_kind="prs", prs=[12, 3497]),
            ev("Menus", "2026-10-04", author="d", build_kind="prs", prs=[44]),
        ]
        best = evaluate.best_stage(evidence, merged)
        branch = evaluate.branch_stage(evidence, merged, best, evaluate.unverified_claim(evidence, best, merged))
        # open PRs alone beat a build with local patches; a merged PR is not needed any more
        self.assertEqual((branch["stage"], branch["needs"], branch["patches"]), ("Ingame", [12], False))
        self.assertEqual(branch["confidence"]["label"], "2 reports off main")
        # nothing off main that is not above the stage on main
        self.assertIsNone(evaluate.branch_stage(evidence[:1], merged, best))
        # once #12 is merged the same report is on main: a claim, not off main
        both = {12, 3497}.__contains__
        now = evaluate.unverified_claim(evidence, evaluate.best_stage(evidence, both), both)
        self.assertEqual(now["stage"], "Ingame")

    def test_dedupe_folds_a_quote_repeated_in_another_thread(self):
        quote = "Stray (PPSA02100) reaches the loading screen on current main"
        a = ev("Presents", "2026-10-01", author="a", url="https://github.com/x/y/issues/1#c1", quote=quote)
        b = ev("Presents", "2026-10-02", author="b", url="https://github.com/x/y/pull/9#c2", quote=quote + ".")
        c = dict(a)  # the same line read twice (two title IDs of one game)
        out = evaluate.dedupe([b, a, c])
        self.assertEqual(len(out), 1)
        self.assertEqual((out[0]["author"], out[0]["also"]), ("a", ["https://github.com/x/y/pull/9#c2"]))


def issue(number, title, body="", comments=(), state="OPEN", created="2026-10-01T00:00:00Z"):
    return {
        "number": number,
        "title": title,
        "body": body,
        "url": f"https://github.com/{REPO}/issues/{number}",
        "state": state,
        "createdAt": created,
        "updatedAt": created,
        "author": "reporter",
        "labels": [],
        "assignees": [],
        "comments": [
            {"body": b, "url": f"https://github.com/{REPO}/issues/{number}#c{i}", "createdAt": d, "author": who}
            for i, (b, d, who) in enumerate(comments)
        ],
        "xrefs": [],
        "closed_by": [],
    }


def pr(number, title, body, state="OPEN", merged_=False):
    return {
        "number": number,
        "title": title,
        "body": body,
        "url": f"https://github.com/{REPO}/pull/{number}",
        "state": "MERGED" if merged_ else state,
        "merged": merged_,
        "mergedAt": "2026-10-05T00:00:00Z" if merged_ else None,
        "isDraft": False,
        "createdAt": "2026-10-02T00:00:00Z",
        "updatedAt": "2026-10-05T00:00:00Z",
        "author": "dev",
        "labels": [],
        "closes": [],
        "xrefs": [],
        "comments": [],
        "reviews": [],
        "review_comments": [],
    }


TSV = (
    "titleId\tconceptId\tname\tcontentId\tregion\tpublisherId\n"
    "PPSA04263_00\t201930\tGrand Theft Auto V\tEP1004-PPSA04263_00-GTAVFULLGAMEDISC\tEP\tEP1004\n"
    "PPSA04264_00\t201930\tGrand Theft Auto V\tUP1004-PPSA04264_00-GTAVFULLGAMEDISC\tUP\tUP1004\n"
)
CRASH = "AGC graphics: storage image access to depth surface is not implemented"


class GameModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = {
            "repo": REPO,
            "issues": [
                issue(
                    1,
                    "GTA V (PPSA04264): compute queue stall",
                    f"GTA V (PPSA04264) boots on current main and stops at:\n`{CRASH}`",
                    comments=[
                        (
                            "Grand Theft Auto V (PPSA04263) on Windows renders the loading screen, then stops the same way.",
                            "2026-10-03T00:00:00Z",
                            "eu",
                        ),
                        (
                            "> GTA V (PPSA04264) reaches the main menu\nThat was on my local build, not main.",
                            "2026-10-04T00:00:00Z",
                            "skeptic",
                        ),
                    ],
                ),
                issue(2, "Example content ID", "Labels look like `UP0000-PPSA00000_00-LABEL` (PPSA00000 renders)."),
            ],
            "prs": [
                pr(
                    5,
                    "fix(agc): depth storage",
                    "Fixes #1. GTA V (PPSA04264) presents its loading screen with this PR.",
                    merged_=True,
                ),
                pr(4006, "feat(audio): mixer", "Adds the mixer."),
            ],
            "discussions": [
                {
                    "number": 9,
                    "title": "Grand Theft Auto V (PPSA04264)",
                    "body": "Bring-up thread. GTA V (PPSA04264) on Linux, current main: the intro renders.",
                    "url": f"https://github.com/{REPO}/discussions/9",
                    "createdAt": "2026-10-06T00:00:00Z",
                    "updatedAt": "2026-10-06T00:00:00Z",
                    "author": "linuxer",
                    "category": "Game bring-up",
                    "closed": False,
                    "comments": [],
                }
            ],
            "working_groups": [
                {
                    "repo": "AlxcBTW/AnyPS5",
                    "number": 44,
                    "title": "Grand Theft Auto V (PPSA04264) working group",
                    "body": "Build main plus boykopovar/AnyPS5#5 and #4006 (still open), then run the title.",
                    "url": "https://github.com/AlxcBTW/AnyPS5/issues/44",
                    "createdAt": "2026-10-07T00:00:00Z",
                    "updatedAt": "2026-10-07T00:00:00Z",
                    "author": "lead",
                    "comments": [
                        {
                            "body": "**Grand Theft Auto V is in-game.** The prologue runs at 2 FPS.",
                            "url": "https://github.com/AlxcBTW/AnyPS5/issues/44#issuecomment-1",
                            "createdAt": "2026-10-08T00:00:00Z",
                            "author": "lead",
                        },
                        {
                            "body": "The pause menu of another game renders too.\nEpic Mickey (PPSA15657) also starts.",
                            "url": "https://github.com/AlxcBTW/AnyPS5/issues/44#issuecomment-2",
                            "createdAt": "2026-10-09T00:00:00Z",
                            "author": "other",
                        },
                    ],
                }
            ],
            "dependencies": {},
            "external_prs": {},
        }
        cls.model = Model(
            raw, {"blockers": [], "titles": [], "not_blockers": []}, REPO, NOW, catalog=parse_catalog(TSV)
        )
        cls.games = {g["id"]: g for g in game_records(cls.model)}

    def test_both_region_ids_are_one_game_with_merged_evidence(self):
        g = self.games["grand-theft-auto-v"]
        self.assertEqual(g["title_ids"], ["PPSA04263", "PPSA04264"])
        self.assertEqual([t["region"] for t in g["titles"]], ["EU", "US"])
        self.assertIn("GTA V", g["aliases"])
        self.assertEqual({e["title"] for e in g["evidence"]}, {"PPSA04263", "PPSA04264"})
        self.assertEqual(g["store_url"], "https://store.playstation.com/en-us/concept/201930")
        self.assertEqual(self.model.titles["PPSA04264"]["game"], "grand-theft-auto-v")

    def test_stage_counts_main_and_merged_prs_and_reads_discussions(self):
        g = self.games["grand-theft-auto-v"]
        self.assertEqual(g["stage"]["stage"], "Presents")
        authors = g["confidence"]["authors"]
        # eu (issue comment, main), dev (merged PR #5's branch) and linuxer (discussion, main)
        self.assertEqual(authors, ["dev", "eu", "linuxer"])
        self.assertEqual(g["confidence"]["level"], "corroborated")
        self.assertEqual(g["discussions"], [9])
        self.assertEqual([t["stage"] for t in g["timeline"]], ["Starts", "Presents"])

    def test_a_quoted_claim_is_not_the_quoters_report(self):
        g = self.games["grand-theft-auto-v"]
        self.assertIsNone(g["unverified_claim"])
        self.assertNotIn("skeptic", {e.get("author") for e in g["evidence"]})

    def test_placeholder_ids_are_not_titles(self):
        self.assertNotIn("PPSA00000", self.model.titles)
        self.assertEqual(self.model.placeholders, {"PPSA00000"})

    def test_a_working_group_is_off_main_with_its_recipe(self):
        g = self.games["grand-theft-auto-v"]
        off = g["stage_on_branches"]
        # the line names the game, not its ID; the thread's recipe names #5 (merged) and #4006 (open)
        self.assertEqual((off["stage"], off["needs"], off["patches"]), ("Ingame", [4006], True))
        self.assertEqual(off["url"], "https://github.com/AlxcBTW/AnyPS5/issues/44#issuecomment-1")
        self.assertEqual(g["stage"]["stage"], "Presents")  # never the stage
        # a comment about another title says nothing about this one
        self.assertFalse(any(e["url"].endswith("issuecomment-2") for e in g["evidence"]))

    def test_blocker_counts_games_not_title_ids(self):
        b = self.model.blockers["1"]
        self.assertEqual(sorted(b["titles"]), ["PPSA04263", "PPSA04264"])
        self.assertEqual((b["games"], b["total"]), (["grand-theft-auto-v"], 1))
        self.assertEqual(b["score"], 3 * b["one_fix_away"] + 2 * b["frontier"] + b["total"])
        self.assertLessEqual(b["frontier"], 1)


if __name__ == "__main__":
    unittest.main()
