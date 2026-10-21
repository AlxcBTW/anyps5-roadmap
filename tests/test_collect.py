"""Tests for collect.py with a fake GitHub: listing, the thread cache, sized queries, cost. No network."""

import datetime as dt
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from anyps5_roadmap import collect as c  # noqa: E402
from anyps5_roadmap.github import GhError  # noqa: E402

NOW = dt.datetime(2026, 10, 10, 12, 0, tzinfo=dt.UTC)
CUTOFF = "2026-08-11T12:00:00Z"


def comment(n, body, author="alice"):
    return {"body": body, "url": f"https://x/c{n}", "createdAt": "2026-10-05T10:00:00Z", "author": {"login": author}}


class FakeGitHub:
    """Answers the listing and thread queries collect.py sends, from plain dicts."""

    def __init__(self):
        self.issues = {
            7: {"updatedAt": "2026-10-09T10:00:00Z", "comments": [comment(1, "PPSA01999 boots")], "xrefs": 1},
            8: {"updatedAt": "2026-10-08T10:00:00Z", "comments": [], "xrefs": 0},
        }
        self.prs = {
            20: {
                "updatedAt": "2026-10-09T11:00:00Z",
                "comments": [comment(2, "on main it reaches the menu"), comment(3, "ci", "github-actions")],
                "reviews": [
                    {"body": "", "url": "https://x/r0", "submittedAt": "2026-10-06T10:00:00Z", "state": "APPROVED"}
                ],
                "threads": [{"path": "a.cpp", "comments": {"totalCount": 1, "nodes": [comment(4, "nit")]}}],
            },
            21: {"updatedAt": "2026-10-07T11:00:00Z", "comments": [], "reviews": [], "threads": []},
        }
        self.discussions = {}
        self.queries = []
        self.page = 100  # nodes per listing page
        self.remaining = 4000
        self.thread_error = None  # raised by the next thread queries instead of answering
        self.max_aliases = None  # a thread query with more aliases times out (HTTP 499)
        self.drain_to = None  # the budget reported from the first thread query on
        self.gone = set()  # issue numbers the listing holds but GitHub no longer resolves

    def listing_page(self, nodes, variables, key):
        """One page of a listing as GitHub answers it: newest update first, cursor = offset."""
        nodes = sorted(nodes, key=lambda n: n["updatedAt"], reverse=True)
        start = int(variables.get("cursor") or 0)
        page = nodes[start : start + self.page]
        info = {"hasNextPage": start + self.page < len(nodes), "endCursor": str(start + self.page)}
        return {"repository": {key: {"pageInfo": info, "nodes": page}}}

    def discussion_node(self, n):
        d = self.discussions[n]
        return {
            "number": n, "title": f"Discussion {n}", "body": "report", "url": f"https://x/discussions/{n}",
            "createdAt": "2026-10-01T10:00:00Z", "updatedAt": d["updatedAt"], "closed": d.get("closed", False),
            "lastEditedAt": d.get("editedAt"), "closedAt": None, "author": {"login": "zoe"},
            "category": {"name": d.get("category", "Game bring-up")},
            "comments": {"totalCount": len(d["comments"])},
        }  # fmt: skip

    def issue_node(self, n):
        d = self.issues[n]
        return {
            "number": n, "title": f"Issue {n}", "body": "", "url": f"https://x/issues/{n}", "state": d.get("state", "OPEN"),
            "stateReason": None, "createdAt": "2026-10-01T10:00:00Z", "updatedAt": d["updatedAt"], "closedAt": None,
            "author": {"login": "zoe"}, "assignees": {"nodes": []}, "labels": {"nodes": []},
            "comments": {"totalCount": len(d["comments"])}, "timelineItems": {"filteredCount": d["xrefs"]},
            "issueDependenciesSummary": {"totalBlockedBy": 0}, "closedByPullRequestsReferences": {"nodes": []},
        }  # fmt: skip

    def pr_node(self, n):
        d = self.prs[n]
        return {
            "number": n, "title": f"PR {n}", "body": "", "url": f"https://x/pull/{n}", "state": d.get("state", "OPEN"), "merged": False,
            "mergedAt": None, "closedAt": None, "createdAt": "2026-10-01T10:00:00Z", "updatedAt": d["updatedAt"],
            "isDraft": False, "author": {"login": "dave"}, "labels": {"nodes": []},
            "closingIssuesReferences": {"nodes": [{"number": 7, "repository": {"nameWithOwner": "o/r"}}]},
            "comments": {"totalCount": len(d["comments"])}, "reviews": {"totalCount": len(d["reviews"])},
            "reviewThreads": {"totalCount": len(d["threads"])}, "timelineItems": {"filteredCount": 0},
        }  # fmt: skip

    def __call__(self, query, variables):
        self.queries.append(query)
        if self.drain_to is not None and "(first: 100" not in query:
            self.remaining = self.drain_to
        rl = {"cost": 1, "remaining": self.remaining, "resetAt": "2026-10-10T13:00:00Z"}
        states = variables.get("states")
        if "issues(first: 100" in query:
            nodes = [self.issue_node(n) for n, d in self.issues.items() if d.get("state", "OPEN") in states]
            return {**self.listing_page(nodes, variables, "issues"), "rateLimit": rl}
        if "pullRequests(first: 100" in query:
            nodes = [self.pr_node(n) for n, d in self.prs.items() if d.get("state", "OPEN") in states]
            return {**self.listing_page(nodes, variables, "pullRequests"), "rateLimit": rl}
        if "discussions(first: 100" in query:
            nodes = [self.discussion_node(n) for n in self.discussions]
            return {**self.listing_page(nodes, variables, "discussions"), "rateLimit": rl}
        if self.thread_error:
            raise self.thread_error
        found = re.findall(r"\b([ipd])(\d+): ", query)
        if self.max_aliases is not None and len(found) > self.max_aliases:
            raise GhError("gh: HTTP 499", 499)
        repo = {}
        for kind, n in re.findall(r"\b([ipd])(\d+): ", query):
            n = int(n)
            if kind == "i" and n in self.gone:
                continue  # GitHub answers null for the alias
            if kind == "i":
                d = self.issues[n]
                xref = {
                    "__typename": "CrossReferencedEvent", "createdAt": "2026-10-06T10:00:00Z", "willCloseTarget": True,
                    "source": {"__typename": "PullRequest", "number": 20, "title": "PR 20", "url": "https://x/pull/20",
                               "state": "OPEN", "merged": False, "updatedAt": "2026-10-09T11:00:00Z", "isDraft": False,
                               "repository": {"nameWithOwner": "o/r"}},
                }  # fmt: skip
                repo[f"i{n}"] = {
                    "number": n,
                    "updatedAt": d["updatedAt"],
                    "comments": {"pageInfo": {"hasNextPage": False}, "nodes": d["comments"]},
                    "timelineItems": {"pageInfo": {"hasNextPage": False}, "nodes": [xref] * d["xrefs"]},
                }
            elif kind == "d":
                d = self.discussions[n]
                repo[f"d{n}"] = {
                    "number": n,
                    "updatedAt": d["updatedAt"],
                    "comments": {"pageInfo": {"hasNextPage": False}, "nodes": d["comments"]},
                }
            else:
                d = self.prs[n]
                repo[f"p{n}"] = {
                    "number": n,
                    "updatedAt": d["updatedAt"],
                    "comments": {"pageInfo": {"hasNextPage": False}, "nodes": d["comments"]},
                    "reviews": {"nodes": d["reviews"]},
                    "reviewThreads": {"nodes": d["threads"]},
                }
        return {"repository": repo, "rateLimit": rl}


def run(fake, cache_dir, now=NOW, refresh=False):
    api = c.Api(graphql=fake, rest=lambda path: [])
    return c.collect(
        "o/r", CUTOFF, {"blockers": []}, lambda m: None, cache_dir=cache_dir, api=api, now=now, refresh=refresh
    )


class Collect(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def deep(self, fake):
        listings = ("issues(first: 100", "pullRequests(first: 100", "discussions(first: 100")
        return [q for q in fake.queries if not any(m in q for m in listings)]

    def test_first_run_reads_only_threads_with_text_and_sizes_each_connection(self):
        fake = FakeGitHub()
        raw = run(fake, self.cache)
        deep = self.deep(fake)
        self.assertEqual(len(deep), 1)  # issue 7 and PR 20 share one query; issue 8 and PR 21 have nothing to read
        q = deep[0]
        self.assertIn("i7: issue(number: 7)", q)
        self.assertIn("p20: pullRequest(number: 20)", q)
        self.assertNotIn("i8:", q)
        self.assertNotIn("p21:", q)
        self.assertIn("comments(first: 2)", q)  # sized to the listing's count
        self.assertIn("reviewThreads(first: 1)", q)
        self.assertIn("rateLimit { cost remaining resetAt }", q)
        self.assertEqual(raw["api"]["graphql_cost"], len(fake.queries))
        self.assertEqual(raw["api"]["threads_read"], 2)
        self.assertEqual(raw["api"]["threads_without_text"], 2)

    def test_threads_land_in_the_raw_format(self):
        raw = run(FakeGitHub(), self.cache)
        pr = next(p for p in raw["prs"] if p["number"] == 20)
        self.assertEqual([x["author"] for x in pr["comments"]], ["alice", "github-actions"])
        self.assertEqual(pr["reviews"], [])  # an approval without a body says nothing
        self.assertEqual(pr["review_comments"][0]["path"], "a.cpp")
        self.assertEqual(pr["closes"], [{"repo": "o/r", "number": 7}])
        issue = next(i for i in raw["issues"] if i["number"] == 7)
        self.assertEqual(issue["xrefs"][0]["number"], 20)
        self.assertTrue(issue["xrefs"][0]["willClose"])
        self.assertEqual(issue["comments"][0]["body"], "PPSA01999 boots")

    def test_unchanged_threads_come_from_the_cache(self):
        run(FakeGitHub(), self.cache)
        self.assertTrue((self.cache / c.THREADS_FILE).exists())
        fake = FakeGitHub()
        raw = run(fake, self.cache)
        self.assertEqual(self.deep(fake), [])
        self.assertEqual(raw["api"]["threads_from_cache"], 4)
        pr = next(p for p in raw["prs"] if p["number"] == 20)
        self.assertEqual(len(pr["comments"]), 2)  # still there, from the cache

    def test_a_changed_thread_is_read_again_alone(self):
        run(FakeGitHub(), self.cache)
        fake = FakeGitHub()
        fake.prs[20]["updatedAt"] = "2026-10-10T09:00:00Z"
        fake.prs[20]["comments"].append(comment(5, "PPSA01999 reaches gameplay on current main", "bob"))
        raw = run(fake, self.cache)
        deep = self.deep(fake)
        self.assertEqual(len(deep), 1)
        self.assertIn("p20:", deep[0])
        self.assertNotIn("i7:", deep[0])
        pr = next(p for p in raw["prs"] if p["number"] == 20)
        self.assertEqual(len(pr["comments"]), 3)

    def test_old_cache_entries_expire_and_refresh_reads_everything(self):
        run(FakeGitHub(), self.cache)
        fake = FakeGitHub()
        run(fake, self.cache, now=NOW + dt.timedelta(days=3))
        self.assertEqual(len(self.deep(fake)), 1)
        fake = FakeGitHub()
        run(fake, self.cache, refresh=True)
        self.assertEqual(len(self.deep(fake)), 1)

    def test_a_long_thread_pass_saves_its_progress_as_it_goes(self):
        fake = FakeGitHub()
        fake.issues = {
            n: {"updatedAt": "2026-10-09T10:00:00Z", "comments": [comment(n, "PPSA01999 boots")], "xrefs": 0}
            for n in range(100, 160)
        }
        saved = []
        real = c.save_threads

        def record(cache_dir, threads):
            saved.append(len(threads["issue"]))
            real(cache_dir, threads)

        with mock.patch.object(c, "CHECKPOINT_SECONDS", 0), mock.patch.object(c, "save_threads", record):
            run(fake, self.cache)
        self.assertGreater(len(saved), 2)  # checkpoints during the pass, then the final save
        self.assertLess(saved[0], 60)  # the first checkpoint came before every thread was read
        self.assertEqual(len(c.load_threads(self.cache)["issue"]), 60)

    def test_a_save_that_dies_mid_write_keeps_the_previous_thread_cache(self):
        c.save_threads(self.cache, {"version": c.THREADS_VERSION, "issue": {"1": {}}, "pr": {}, "discussion": {}})
        real = Path.write_text

        def torn(path, text, *args, **kwargs):
            real(path, text[: len(text) // 2], *args, **kwargs)
            raise OSError("killed")

        with mock.patch.object(Path, "write_text", torn), self.assertRaises(OSError):
            c.save_threads(self.cache, {"version": c.THREADS_VERSION, "issue": {"2": {}}, "pr": {}, "discussion": {}})
        self.assertEqual(c.load_threads(self.cache)["issue"], {"1": {}})

    def test_a_number_that_no_longer_resolves_is_remembered_not_asked_for_again(self):
        fake = FakeGitHub()
        fake.issues[9] = {"updatedAt": "2026-10-09T09:00:00Z", "comments": [comment(5, "gone soon")], "xrefs": 0}
        fake.gone = {9}
        raw = run(fake, self.cache)
        self.assertEqual(raw["api"]["unread_threads"], 0)
        self.assertEqual(len(self.deep(fake)), 1)
        again = FakeGitHub()
        again.issues, again.gone = fake.issues, {9}
        run(again, self.cache)
        self.assertEqual(self.deep(again), [])

    def test_the_thread_pass_stops_at_its_time_budget_and_the_rest_waits_for_the_next_run(self):
        fake = FakeGitHub()
        with mock.patch.object(c, "THREAD_BUDGET_SECONDS", 0):
            raw = run(fake, self.cache)
        self.assertTrue(raw["api"]["partial"])
        self.assertEqual(raw["api"]["unread_threads"], 2)
        self.assertTrue(any("time budget" in t for t in raw["truncated"]))
        self.assertEqual(self.deep(fake), [])
        run(fake, self.cache)  # the next run, with time, reads them
        self.assertEqual(len(self.deep(fake)), 1)

    def test_batches_respect_the_size_limits(self):
        many = [("pr", n, {"comments": 100, "xrefs": 0, "reviews": 0, "threads": 0}) for n in range(30)]
        sizes = [len(b) for b in c.batches(many)]
        self.assertTrue(all(s * 100 <= c.BATCH_NODES for s in sizes), sizes)
        self.assertEqual(sum(sizes), 30)
        small = [("issue", n, {"comments": 1, "xrefs": 0}) for n in range(60)]
        self.assertEqual([len(b) for b in c.batches(small)], [c.BATCH, c.BATCH, 10])

    def test_bot_authors_are_marked(self):
        node = {"author": {"login": "github-actions", "__typename": "Bot"}}
        self.assertEqual(c._login(node), "github-actions[bot]")
        self.assertEqual(c._login({"author": {"login": "alice", "__typename": "User"}}), "alice")


if __name__ == "__main__":
    unittest.main()
