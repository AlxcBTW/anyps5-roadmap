"""Tests for the since-cursor listing, discussions and the GraphQL budget in collect.py. No network."""

import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from test_collect import CUTOFF, NOW, FakeGitHub, comment, run  # noqa: E402

from anyps5_roadmap import collect as c  # noqa: E402
from anyps5_roadmap.github import RateLimited  # noqa: E402

LISTINGS = ("issues(first: 100", "pullRequests(first: 100", "discussions(first: 100")


def listing_queries(fake, marker):
    return [q for q in fake.queries if marker in q]


def reply(n, body="a reply"):
    return {"body": body, "url": f"https://x/r{n}", "createdAt": "2026-10-06T10:00:00Z", "author": {"login": "eve"}}


def with_discussions(fake):
    fake.discussions = {
        30: {
            "updatedAt": "2026-10-09T12:00:00Z",
            "comments": [
                {**comment(10, "PPSA01999 starts"), "replies": {"totalCount": 2, "nodes": [reply(1), reply(2)]}},
                {**comment(11, "second"), "replies": {"totalCount": 0, "nodes": []}},
            ],
        },
        31: {"updatedAt": "2026-10-08T12:00:00Z", "comments": []},
    }
    return fake


class Listing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def later(self, **kw):
        return NOW + dt.timedelta(**kw)

    def test_the_first_run_lists_in_full_and_stores_the_listing(self):
        fake = with_discussions(FakeGitHub())
        run(fake, self.cache)
        self.assertEqual([len(listing_queries(fake, m)) for m in LISTINGS], [2, 2, 1])
        stored = json.loads((self.cache / c.LISTING_FILE).read_text(encoding="utf-8"))
        self.assertEqual(stored["version"], 1)
        self.assertEqual(stored["since"]["issue"], "2026-10-09T10:00:00Z")
        self.assertEqual(stored["since"]["pr"], "2026-10-09T11:00:00Z")
        self.assertEqual(stored["since"]["discussion"], "2026-10-09T12:00:00Z")
        self.assertEqual(stored["full_at"], "2026-10-10T12:00:00Z")
        self.assertEqual(sorted(stored["issue"]), ["7", "8"])
        self.assertEqual(stored["pr"]["20"]["comment_count"], 2)  # the flattened node

    def test_the_second_run_stops_paging_at_the_cursor(self):
        def crowded():
            fake = with_discussions(FakeGitHub())
            fake.page = 2
            for n in range(100, 110):  # ten old closed issues, so a full listing needs several pages
                fake.issues[n] = {"updatedAt": f"2026-09-{n - 90:02d}T10:00:00Z", "comments": [], "xrefs": 0}
                fake.issues[n]["state"] = "CLOSED"
            return fake

        full = crowded()
        run(full, self.cache)
        self.assertGreater(len(listing_queries(full, LISTINGS[0])), 4)
        fake = crowded()
        fake.issues[7]["updatedAt"] = "2026-10-10T08:00:00Z"
        raw = run(fake, self.cache, now=self.later(hours=1))
        # page one holds issue 7 (changed) and issue 8 (older than the cursor): stop there, not at page two
        self.assertEqual(len(listing_queries(fake, LISTINGS[0])), 1)
        self.assertEqual(len(listing_queries(fake, LISTINGS[1])), 1)
        self.assertEqual(len(listing_queries(fake, LISTINGS[2])), 1)
        self.assertEqual(next(i for i in raw["issues"] if i["number"] == 7)["updatedAt"], "2026-10-10T08:00:00Z")
        self.assertEqual(len(raw["issues"]), 12)  # the old closed ones still count, from the store

    def test_an_incremental_listing_uses_all_states_and_the_overlap(self):
        run(FakeGitHub(), self.cache)
        stored = json.loads((self.cache / c.LISTING_FILE).read_text(encoding="utf-8"))
        # one issue was updated 5 minutes before the cursor: inside the overlap, so it is listed again
        fake = FakeGitHub()
        fake.issues[9] = {"updatedAt": "2026-10-09T09:55:00Z", "comments": [], "xrefs": 0}
        fake.issues[10] = {"updatedAt": "2026-10-09T09:40:00Z", "comments": [], "xrefs": 0}  # 20 minutes before
        fake.page = 100
        run(fake, self.cache, now=self.later(hours=1))
        self.assertEqual(stored["since"]["issue"], "2026-10-09T10:00:00Z")
        after = json.loads((self.cache / c.LISTING_FILE).read_text(encoding="utf-8"))
        self.assertIn("9", after["issue"])
        self.assertNotIn("10", after["issue"])  # beyond the overlap, so the cursor run did not see it
        self.assertEqual(after["full_at"], stored["full_at"])  # no full listing happened

    def test_changed_items_are_upserted_and_the_window_is_derived_from_the_store(self):
        run(FakeGitHub(), self.cache)
        fake = FakeGitHub()
        fake.prs[21].update(state="MERGED", updatedAt="2026-10-10T09:00:00Z")
        raw = run(fake, self.cache, now=self.later(hours=1))
        self.assertEqual(next(p for p in raw["prs"] if p["number"] == 21)["state"], "MERGED")
        self.assertEqual([p["number"] for p in raw["prs"]], [20, 21])  # open first, then the merged one

    def test_open_items_outside_the_window_stay_and_old_closed_ones_stay_out(self):
        def fake_with_old():
            fake = FakeGitHub()
            fake.issues[1] = {"updatedAt": "2026-01-01T10:00:00Z", "comments": [], "xrefs": 0}  # open, old
            fake.issues[2] = {"updatedAt": "2026-01-02T10:00:00Z", "comments": [], "xrefs": 0, "state": "CLOSED"}
            fake.issues[3] = {"updatedAt": "2026-09-02T10:00:00Z", "comments": [], "xrefs": 0, "state": "CLOSED"}
            return fake

        for when in (NOW, self.later(hours=1)):  # a full and then an incremental run
            raw = run(fake_with_old(), self.cache, now=when)
            self.assertEqual(sorted(i["number"] for i in raw["issues"]), [1, 3, 7, 8])

    def test_a_full_listing_after_seven_days_drops_vanished_items(self):
        run(FakeGitHub(), self.cache)
        fake = FakeGitHub()
        del fake.issues[8]
        raw = run(fake, self.cache, now=self.later(days=2))
        self.assertIn(8, [i["number"] for i in raw["issues"]])  # nothing says it is gone yet
        self.assertEqual(len(listing_queries(fake, LISTINGS[0])), 1)
        fake = FakeGitHub()
        del fake.issues[8]
        raw = run(fake, self.cache, now=self.later(days=8))
        self.assertNotIn(8, [i["number"] for i in raw["issues"]])
        self.assertEqual(len(listing_queries(fake, LISTINGS[0])), 2)  # open, then closed

    def test_refresh_a_new_version_and_an_earlier_window_list_in_full(self):
        run(FakeGitHub(), self.cache)
        fake = FakeGitHub()
        run(fake, self.cache, now=self.later(hours=1), refresh=True)
        self.assertEqual(len(listing_queries(fake, LISTINGS[0])), 2)
        path = self.cache / c.LISTING_FILE
        stored = json.loads(path.read_text(encoding="utf-8"))
        stored["version"] = 99
        path.write_text(json.dumps(stored), encoding="utf-8")
        fake = FakeGitHub()
        run(fake, self.cache, now=self.later(hours=2))
        self.assertEqual(len(listing_queries(fake, LISTINGS[0])), 2)
        fake = FakeGitHub()  # a window that reaches further back than the stored one
        api = c.Api(graphql=fake, rest=lambda path: [])
        c.collect("o/r", "2026-07-01T00:00:00Z", {"blockers": []}, lambda m: None, cache_dir=self.cache, api=api,
                  now=self.later(hours=3))  # fmt: skip
        self.assertEqual(len(listing_queries(fake, LISTINGS[0])), 2)

    def test_a_damaged_listing_file_means_a_full_listing(self):
        (self.cache / c.LISTING_FILE).write_text("{not json", encoding="utf-8")
        fake = FakeGitHub()
        run(fake, self.cache)
        self.assertEqual(len(listing_queries(fake, LISTINGS[0])), 2)


class Discussions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_discussions_come_with_their_comments_and_flattened_replies(self):
        fake = with_discussions(FakeGitHub())
        raw = run(fake, self.cache)
        self.assertEqual([d["number"] for d in raw["discussions"]], [30, 31])
        d = raw["discussions"][0]
        self.assertEqual(
            {k: d[k] for k in ("title", "url", "closed", "category", "author", "createdAt", "updatedAt", "body")},
            {
                "title": "Discussion 30", "url": "https://x/discussions/30", "closed": False,
                "category": "Game bring-up", "author": "zoe", "createdAt": "2026-10-01T10:00:00Z",
                "updatedAt": "2026-10-09T12:00:00Z", "body": "report",
            },
        )  # fmt: skip
        self.assertEqual([x["body"] for x in d["comments"]], ["PPSA01999 starts", "a reply", "a reply", "second"])
        self.assertEqual(sorted(d["comments"][1]), ["author", "body", "createdAt", "url"])
        self.assertEqual(d["comments"][1]["author"], "eve")
        self.assertEqual(raw["discussions"][1]["comments"], [])
        q = next(q for q in fake.queries if "d30: discussion(number: 30)" in q)
        self.assertIn("comments(first: 2)", q)  # sized from the listing
        self.assertIn("replies(first: 50) { totalCount", q)
        self.assertNotIn("d31:", q)  # nothing to read

    def test_discussion_threads_are_cached_and_old_caches_load(self):
        run(with_discussions(FakeGitHub()), self.cache)
        stored = json.loads((self.cache / c.THREADS_FILE).read_text(encoding="utf-8"))
        self.assertEqual(sorted(stored["discussion"]), ["30", "31"])
        fake = with_discussions(FakeGitHub())
        raw = run(fake, self.cache, now=NOW + dt.timedelta(hours=1))
        self.assertEqual([q for q in fake.queries if "discussion(number" in q], [])
        self.assertEqual(len(raw["discussions"][0]["comments"]), 4)
        # a cache written before discussions existed has no such key
        del stored["discussion"]
        (self.cache / c.THREADS_FILE).write_text(json.dumps(stored), encoding="utf-8")
        fake = with_discussions(FakeGitHub())
        raw = run(fake, self.cache, now=NOW + dt.timedelta(hours=2))
        self.assertEqual(len(raw["discussions"][0]["comments"]), 4)
        self.assertEqual(len([q for q in fake.queries if "d30: discussion" in q]), 1)

    def test_a_changed_discussion_is_read_again(self):
        run(with_discussions(FakeGitHub()), self.cache)
        fake = with_discussions(FakeGitHub())
        fake.discussions[30]["updatedAt"] = "2026-10-10T09:00:00Z"
        fake.discussions[30]["comments"].append({**comment(12, "third"), "replies": {"totalCount": 0, "nodes": []}})
        raw = run(fake, self.cache, now=NOW + dt.timedelta(hours=1))
        self.assertEqual(len(raw["discussions"][0]["comments"]), 5)

    def test_too_many_replies_are_reported_as_truncated(self):
        fake = with_discussions(FakeGitHub())
        fake.discussions[30]["comments"][0]["replies"]["totalCount"] = 60
        raw = run(fake, self.cache)
        self.assertEqual(raw["truncated"], ["Discussion #30: a comment has 60 replies, 50 read"])

    def test_the_window_keeps_open_discussions_and_drops_old_closed_ones(self):
        fake = with_discussions(FakeGitHub())
        fake.discussions[32] = {"updatedAt": "2026-01-01T00:00:00Z", "comments": []}
        fake.discussions[33] = {"updatedAt": "2026-01-01T00:00:00Z", "comments": [], "closed": True}
        fake.discussions[34] = {"updatedAt": "2026-09-20T00:00:00Z", "comments": [], "closed": True}
        raw = run(fake, self.cache)
        self.assertEqual([d["number"] for d in raw["discussions"]], [30, 31, 32, 34])
        self.assertTrue(raw["discussions"][-1]["closed"])

    def test_without_discussions_the_key_is_an_empty_list(self):
        self.assertEqual(run(FakeGitHub(), self.cache)["discussions"], [])


class Budget(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def deep(self, fake):
        return [q for q in fake.queries if not any(m in q for m in LISTINGS)]

    def test_a_low_budget_stops_the_thread_pass_and_marks_the_run_partial(self):
        fake = with_discussions(FakeGitHub())
        fake.remaining = c.RESERVE - 1
        raw = run(fake, self.cache)
        self.assertEqual(self.deep(fake), [])
        self.assertTrue(raw["api"]["partial"])
        self.assertEqual(raw["api"]["unread_threads"], 3)  # issue 7, PR 20 and discussion 30
        self.assertEqual(len(raw["truncated"]), 1)
        self.assertIn("3 threads were left for the next run", raw["truncated"][0])
        self.assertEqual(next(i for i in raw["issues"] if i["number"] == 7)["comments"], [])  # no cache, no text
        self.assertEqual(raw["api"]["threads_read"], 0)
        # the next run, with budget, reads them: their cache entries were never made
        fake = with_discussions(FakeGitHub())
        raw = run(fake, self.cache, now=NOW + dt.timedelta(hours=1))
        self.assertFalse(raw["api"]["partial"])
        self.assertEqual(raw["api"]["unread_threads"], 0)
        self.assertEqual(raw["truncated"], [])
        self.assertEqual(len(next(p for p in raw["prs"] if p["number"] == 20)["comments"]), 2)

    def test_unread_threads_keep_their_stale_cache(self):
        run(FakeGitHub(), self.cache)
        fake = FakeGitHub()
        fake.prs[20]["updatedAt"] = "2026-10-10T09:00:00Z"
        fake.prs[20]["comments"].append(comment(5, "new"))
        fake.remaining = 10
        raw = run(fake, self.cache, now=NOW + dt.timedelta(hours=1))
        pr = next(p for p in raw["prs"] if p["number"] == 20)
        self.assertEqual(len(pr["comments"]), 2)  # the old copy
        self.assertEqual(pr["updatedAt"], "2026-10-10T09:00:00Z")
        self.assertEqual(raw["api"]["unread_threads"], 1)
        stored = json.loads((self.cache / c.THREADS_FILE).read_text(encoding="utf-8"))
        self.assertEqual(stored["pr"]["20"]["updatedAt"], "2026-10-09T11:00:00Z")  # still stale, so read next time

    def test_the_budget_is_checked_before_every_batch(self):
        fake = FakeGitHub()
        for n in range(100, 100 + c.BATCH + 5):  # two batches of issues with text
            fake.issues[n] = {"updatedAt": "2026-10-09T09:00:00Z", "comments": [comment(n, "x")], "xrefs": 0}
        fake.drain_to = 100  # the first thread query reports a spent budget
        raw = run(fake, self.cache)
        self.assertEqual(len(self.deep(fake)), 1)
        self.assertTrue(raw["api"]["partial"])
        self.assertEqual(raw["api"]["threads_read"], c.BATCH)
        self.assertEqual(raw["api"]["unread_threads"], 32 - c.BATCH)  # 30 issues, issue 7 and PR 20 in all

    def test_a_query_that_times_out_is_split_and_a_single_failure_is_reported(self):
        fake = with_discussions(FakeGitHub())
        fake.max_aliases = 1
        raw = run(fake, self.cache)
        self.assertEqual(raw["api"]["threads_read"], 3)
        self.assertFalse(raw["api"]["partial"])
        self.assertEqual(len(next(p for p in raw["prs"] if p["number"] == 20)["comments"]), 2)
        self.assertEqual(len(self.deep(fake)), 5)  # one of three, then two halves of one and two
        fake = with_discussions(FakeGitHub())
        fake.max_aliases = 0
        raw = run(fake, self.cache, refresh=True)
        self.assertEqual(raw["api"]["threads_read"], 0)
        self.assertEqual(raw["api"]["unread_threads"], 0)
        self.assertFalse(raw["api"]["partial"])
        self.assertEqual(len(raw["truncated"]), 1)
        self.assertIn("could not read the threads of", raw["truncated"][0])

    def test_a_rate_limit_error_is_caught_and_the_listing_is_kept(self):
        fake = with_discussions(FakeGitHub())
        fake.thread_error = RateLimited("API rate limit exceeded for user ID 1.")
        raw = run(fake, self.cache)
        self.assertTrue(raw["api"]["partial"])
        self.assertEqual(raw["api"]["unread_threads"], 3)
        self.assertEqual([i["number"] for i in raw["issues"]], [7, 8])
        self.assertEqual([d["number"] for d in raw["discussions"]], [30, 31])
        self.assertIn("left for the next run", raw["truncated"][-1])
        self.assertTrue((self.cache / c.LISTING_FILE).exists())  # saved before the thread pass

    def test_reset_time_and_remaining_are_tracked(self):
        raw = run(FakeGitHub(), self.cache)
        self.assertEqual(raw["api"]["graphql_remaining"], 4000)
        self.assertEqual(raw["api"]["graphql_reset_at"], "2026-10-10T13:00:00Z")
        self.assertFalse(raw["api"]["partial"])


class Dependencies(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_dependencies_go_through_the_etag_store(self):
        seen = []

        def rest_cached(path, store):
            seen.append((path, dict(store.get(path) or {})))
            if path not in store:
                store[path] = {"etag": 'W/"1"', "body": [{"number": 8, "state": "open", "title": "dep"}]}
            return store[path]["body"]

        def go(now):
            api = c.Api(graphql=FakeGitHub(), rest=lambda path: [], rest_cached=rest_cached)
            curated = {"blockers": [{"issue": 7}]}
            return c.collect("o/r", CUTOFF, curated, lambda m: None, cache_dir=self.cache, api=api, now=now)

        raw = go(NOW)
        self.assertEqual(raw["dependencies"]["7"][0]["number"], 8)
        self.assertEqual(seen[0][1], {})
        stored = json.loads((self.cache / c.ETAGS_FILE).read_text(encoding="utf-8"))
        self.assertEqual(list(stored.values())[0]["etag"], 'W/"1"')
        go(NOW + dt.timedelta(hours=1))
        self.assertEqual(seen[1][1]["etag"], 'W/"1"')  # the second run starts from the stored answer
        self.assertEqual(seen[1][0], "repos/o/r/issues/7/dependencies/blocked_by?per_page=100")


if __name__ == "__main__":
    unittest.main()
