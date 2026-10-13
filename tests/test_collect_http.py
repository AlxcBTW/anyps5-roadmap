"""Tests for gh retries, rate limits and ETags (github.py) and fetch_cached (upstream.py). No network."""

import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from anyps5_roadmap import github as g  # noqa: E402
from anyps5_roadmap.upstream import USER_AGENT, fetch_cached  # noqa: E402


class FakeRun:
    """Stands in for subprocess.run: answers from a list and records the gh arguments."""

    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    def __call__(self, cmd, **kwargs):
        self.calls.append(cmd[1:])
        code, out, err = self.answers.pop(0)
        return SimpleNamespace(returncode=code, stdout=out, stderr=err)


class Retries(unittest.TestCase):
    def test_a_transient_error_is_retried_with_a_short_delay(self):
        sleeps = []
        run = FakeRun((1, "", "gh: Bad Gateway (HTTP 502)"), (0, '{"ok": 1}', ""))
        self.assertEqual(g._gh(["api", "x"], sleep=sleeps.append, run=run), '{"ok": 1}')
        self.assertEqual(sleeps, [2.0])

    def test_a_secondary_rate_limit_backs_off_for_longer_and_gives_up_after_three_tries(self):
        err = "gh: You have exceeded a secondary rate limit. (HTTP 403)"
        sleeps = []
        run = FakeRun((1, "", err), (1, "", err), (0, "{}", ""))
        self.assertEqual(g._gh(["api", "x"], sleep=sleeps.append, run=run), "{}")
        self.assertEqual(sleeps, [30.0, 60.0])
        sleeps = []
        run = FakeRun((1, "", err), (1, "", err), (1, "", err), (0, "{}", ""))
        with self.assertRaises(g.GhError) as ctx:
            g._gh(["api", "x"], sleep=sleeps.append, run=run)
        self.assertNotIsInstance(ctx.exception, g.RateLimited)
        self.assertEqual(sleeps, [30.0, 60.0])
        self.assertEqual(len(run.answers), 1)  # the fourth answer was never asked for

    def test_a_403_with_retry_after_is_a_secondary_limit(self):
        sleeps = []
        run = FakeRun((1, "HTTP/2.0 403 Forbidden\nRetry-After: 60\n\n", "gh: Forbidden (HTTP 403)"), (0, "[]", ""))
        g._gh(["api", "x"], sleep=sleeps.append, run=run)
        self.assertEqual(sleeps, [30.0])

    def test_the_primary_rate_limit_raises_at_once_with_the_reset_time(self):
        sleeps = []
        out = "HTTP/2.0 403 Forbidden\nX-Ratelimit-Reset: 1791891856\n\n"
        run = FakeRun((1, out, "gh: API rate limit exceeded for user ID 1. (HTTP 403)"))
        with self.assertRaises(g.RateLimited) as ctx:
            g._gh(["api", "x"], sleep=sleeps.append, run=run)
        self.assertEqual((sleeps, ctx.exception.reset, ctx.exception.status), ([], 1791891856, 403))
        self.assertIsInstance(ctx.exception, g.GhError)

    def test_graphql_rate_limit_errors_become_rate_limited(self):
        body = {"errors": [{"type": "RATE_LIMITED", "message": "API rate limit exceeded for user ID 1."}]}
        with self.assertRaises(g.RateLimited):
            g.gh_graphql("query { x }", {}, run=FakeRun((0, json.dumps(body), "")))
        # gh exits 1 on GraphQL errors and prints the body to stdout
        with self.assertRaises(g.RateLimited):
            g.gh_graphql(
                "query { x }", {}, sleep=lambda s: None, run=FakeRun((1, json.dumps(body), "gh: API rate limit"))
            )
        other = {"errors": [{"type": "NOT_FOUND", "message": "Could not resolve"}]}
        with self.assertRaises(g.GhError) as ctx:
            g.gh_graphql("query { x }", {}, run=FakeRun((0, json.dumps(other), "")))
        self.assertNotIsInstance(ctx.exception, g.RateLimited)
        self.assertEqual(g.gh_graphql("query { x }", {}, run=FakeRun((0, '{"data": {"a": 1}}', ""))), {"a": 1})


class Etags(unittest.TestCase):
    OK = 'HTTP/2.0 200 OK\r\nContent-Type: application/json\r\nEtag: W/"abc"\r\n\r\n[{"number": 1}]'
    NOT_MODIFIED = 'HTTP/2.0 304 Not Modified\r\nEtag: "abc"\r\n\r\n'

    def test_a_200_is_stored_and_a_304_reuses_the_body(self):
        store = {}
        run = FakeRun((0, self.OK, ""))
        self.assertEqual(g.gh_rest_cached("repos/o/r/x", store, run=run), [{"number": 1}])
        self.assertEqual(store["repos/o/r/x"], {"etag": 'W/"abc"', "body": [{"number": 1}]})
        self.assertNotIn("If-None-Match", " ".join(run.calls[0]))
        self.assertIn("-i", run.calls[0])
        # gh exits 1 on a 304, prints the headers to stdout and "gh: HTTP 304" to stderr
        run = FakeRun((1, self.NOT_MODIFIED, "gh: HTTP 304"))
        self.assertEqual(g.gh_rest_cached("repos/o/r/x", store, run=run), [{"number": 1}])
        self.assertIn('If-None-Match: W/"abc"', run.calls[0])
        self.assertEqual(len(run.calls), 1)  # no retry for a 304

    def test_a_changed_answer_replaces_the_stored_one(self):
        store = {"p": {"etag": 'W/"old"', "body": [1]}}
        new = 'HTTP/2.0 200 OK\nEtag: W/"new"\n\n[2, 3]'
        self.assertEqual(g.gh_rest_cached("p", store, run=FakeRun((0, new, ""))), [2, 3])
        self.assertEqual(store["p"], {"etag": 'W/"new"', "body": [2, 3]})

    def test_errors_still_raise_and_leave_the_store_alone(self):
        store = {"p": {"etag": 'W/"old"', "body": [1]}}
        run = FakeRun((1, "HTTP/2.0 404 Not Found\n\n{}", "gh: Not Found (HTTP 404)"))
        with self.assertRaises(g.GhError) as ctx:
            g.gh_rest_cached("p", store, run=run)
        self.assertEqual(ctx.exception.status, 404)
        self.assertEqual(store["p"]["etag"], 'W/"old"')

    def test_a_304_without_a_stored_body_is_not_trusted(self):
        # the store lost the body: no If-None-Match is sent, so a 304 cannot come back; a 200 fills it
        store = {"p": {"etag": 'W/"old"'}}
        run = FakeRun((0, self.OK, ""))
        g.gh_rest_cached("p", store, run=run)
        self.assertNotIn("If-None-Match", " ".join(run.calls[0]))
        self.assertEqual(store["p"]["body"], [{"number": 1}])

    def test_parse_response(self):
        status, headers, body = g.parse_response('HTTP/2.0 200 OK\r\nEtag: W/"a"\r\nX-Y: 1\r\n\r\n{"a": 1}\r\n\r\n')
        self.assertEqual((status, headers["etag"], headers["x-y"]), (200, 'W/"a"', "1"))
        self.assertTrue(body.startswith('{"a": 1}'))


class FakeResponse:
    def __init__(self, data, headers=None):
        self.data, self.headers = data, headers or {}

    def read(self):
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FetchCached(unittest.TestCase):
    URL = "https://example.test/PS5_Titles.tsv"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "sub" / "titles.tsv"
        self.logs = []

    def tearDown(self):
        self.tmp.cleanup()

    def opener(self, *answers):
        self.requests = []
        queue = list(answers)

        def open_(req, timeout=None):
            self.requests.append(req)
            answer = queue.pop(0)
            if isinstance(answer, Exception):
                raise answer
            return answer

        return open_

    def sidecar(self):
        return json.loads(Path(str(self.path) + ".meta.json").read_text(encoding="utf-8"))

    def test_a_200_is_written_with_its_validators(self):
        headers = {"ETag": '"v1"', "Last-Modified": "Tue, 13 Oct 2026 10:00:00 GMT"}
        op = self.opener(FakeResponse(b"a\tb\n", headers))
        self.assertEqual(fetch_cached(self.URL, self.path, log=self.logs.append, opener=op), b"a\tb\n")
        self.assertEqual(self.path.read_bytes(), b"a\tb\n")
        meta = self.sidecar()
        self.assertEqual(
            (meta["etag"], meta["last_modified"], meta["url"]), ('"v1"', headers["Last-Modified"], self.URL)
        )
        self.assertIn("fetched_at", meta)
        self.assertEqual(self.requests[0].get_header("User-agent"), USER_AGENT)
        self.assertIsNone(self.requests[0].get_header("If-none-match"))  # nothing cached yet

    def test_a_304_returns_the_cached_bytes_after_sending_the_validators(self):
        fetch_cached(
            self.URL,
            self.path,
            opener=self.opener(
                FakeResponse(b"old", {"ETag": '"v1"', "Last-Modified": "Tue, 13 Oct 2026 10:00:00 GMT"})
            ),
        )
        err = urllib.error.HTTPError(self.URL, 304, "Not Modified", {}, None)
        op = self.opener(err)
        self.assertEqual(fetch_cached(self.URL, self.path, log=self.logs.append, opener=op), b"old")
        self.assertEqual(self.requests[0].get_header("If-none-match"), '"v1"')
        self.assertEqual(self.requests[0].get_header("If-modified-since"), "Tue, 13 Oct 2026 10:00:00 GMT")
        self.assertEqual(self.logs, [])

    def test_a_changed_file_replaces_the_cache_and_the_sidecar(self):
        fetch_cached(self.URL, self.path, opener=self.opener(FakeResponse(b"old", {"ETag": '"v1"'})))
        fetch_cached(self.URL, self.path, opener=self.opener(FakeResponse(b"new", {"ETag": '"v2"'})))
        self.assertEqual(self.path.read_bytes(), b"new")
        self.assertEqual(self.sidecar()["etag"], '"v2"')

    def test_a_network_error_falls_back_to_the_cache_and_says_so(self):
        fetch_cached(self.URL, self.path, opener=self.opener(FakeResponse(b"old", {"ETag": '"v1"'})))
        for err in (
            urllib.error.URLError("offline"),
            TimeoutError("slow"),
            urllib.error.HTTPError(self.URL, 503, "x", {}, None),
        ):
            with self.subTest(err=err):
                self.logs.clear()
                got = fetch_cached(self.URL, self.path, log=self.logs.append, opener=self.opener(err))
                self.assertEqual(got, b"old")
                self.assertEqual(len(self.logs), 1)
                self.assertIn("cached copy", self.logs[0])

    def test_a_network_error_without_a_cache_returns_none(self):
        got = fetch_cached(
            self.URL, self.path, log=self.logs.append, opener=self.opener(urllib.error.URLError("offline"))
        )
        self.assertIsNone(got)
        self.assertFalse(self.path.exists())
        self.assertEqual(len(self.logs), 1)

    def test_a_file_without_a_sidecar_is_fetched_without_validators(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b"manual")
        op = self.opener(FakeResponse(b"fresh"))
        self.assertEqual(fetch_cached(self.URL, self.path, opener=op), b"fresh")
        self.assertIsNone(self.requests[0].get_header("If-none-match"))
        self.assertIsNone(self.sidecar()["etag"])


if __name__ == "__main__":
    unittest.main()
