"""GitHub access through the gh CLI (GraphQL and REST), with retries for transient errors.

Three kinds of failure are told apart:

- transient (HTTP 5xx, timeouts): retried up to four times with a doubling delay from 2 s;
- secondary rate limit ("secondary rate limit", or 403/429 with Retry-After): retried up to
  three times, waiting 30 s first and doubling;
- primary rate limit (the hourly budget is spent): raises RateLimited at once, since
  waiting would take up to an hour. collect() stops reading and keeps what it has.

REST calls that can be repeated cheaply go through gh_rest_cached, which sends If-None-Match
with the ETag of the last answer; a 304 does not count against the REST rate limit.
gh prints a 304 to stdout (with -i) but exits 1 and writes "gh: HTTP 304" to stderr.
"""

from __future__ import annotations

import json
import re
import subprocess
import time

SECONDARY_DELAY = 30.0
SECONDARY_TRIES = 3


class GhError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class RateLimited(GhError):
    """The primary rate limit is spent. `reset` is the epoch second it refills, when known."""

    def __init__(self, message: str, status: int | None = None, reset: int | None = None):
        super().__init__(message, status)
        self.reset = reset


def is_secondary_limit(err: str, status: int | None) -> bool:
    low = err.lower()
    return "secondary rate limit" in low or (status in (403, 429) and "retry-after" in low)


def is_primary_limit(err: str) -> bool:
    low = err.lower()
    return "rate limit" in low or '"type":"rate_limited"' in low.replace(" ", "")


def _reset_of(err: str) -> int | None:
    m = re.search(r"x-ratelimit-reset:\s*(\d+)", err, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _gh(
    args: list[str],
    stdin: str | None = None,
    attempts: int = 4,
    sleep=None,
    run=None,
    ok_status: tuple[int, ...] = (),
) -> str:
    """Run gh and return stdout. A nonzero exit whose stdout starts with an HTTP status in
    `ok_status` (a 304 under -i) counts as success."""
    sleep, run = sleep or time.sleep, run or subprocess.run
    delay, secondary = 2.0, 0
    attempt = 0
    while True:
        proc = run(["gh", *args], input=stdin, capture_output=True, text=True, encoding="utf-8")
        if proc.returncode == 0:
            return proc.stdout
        m = re.match(r"HTTP/\S+ (\d{3})", proc.stdout or "")
        if m and int(m.group(1)) in ok_status:
            return proc.stdout
        err = (proc.stderr or "") + (proc.stdout or "")
        status = None
        m = re.search(r"HTTP (\d{3})", err)
        if m:
            status = int(m.group(1))
        if is_secondary_limit(err, status):
            secondary += 1
            if secondary >= SECONDARY_TRIES:
                raise GhError(err.strip(), status)
            sleep(SECONDARY_DELAY * 2 ** (secondary - 1))
            continue
        if is_primary_limit(err):
            raise RateLimited(err.strip()[:800], status, _reset_of(err))
        if status in (404, 410, 422):
            raise GhError(err.strip(), status)
        attempt += 1
        transient = status in (None, 500, 502, 503, 504) or "timeout" in err.lower()
        if not transient or attempt >= attempts:
            raise GhError(err.strip(), status)
        sleep(delay)
        delay *= 2


def gh_graphql(query: str, variables: dict, sleep=None, run=None) -> dict:
    out = _gh(
        ["api", "graphql", "--input", "-"],
        stdin=json.dumps({"query": query, "variables": variables}),
        sleep=sleep,
        run=run,
    )
    data = json.loads(out)
    if data.get("errors"):
        errors = data["errors"]
        text = json.dumps(errors)[:800]
        if any(e.get("type") == "RATE_LIMITED" or "rate limit" in str(e.get("message", "")).lower() for e in errors):
            raise RateLimited(text)
        raise GhError(text)
    return data["data"]


def gh_rest(path: str) -> object:
    return json.loads(_gh(["api", "-H", "Accept: application/vnd.github+json", path]))


def parse_response(text: str) -> tuple[int, dict[str, str], str]:
    """Split the output of `gh api -i` into status, lower-cased headers and body."""
    parts = re.split(r"\r?\n\r?\n", text, maxsplit=1)
    head, body = parts[0], (parts[1] if len(parts) > 1 else "")
    lines = head.splitlines()
    m = re.match(r"HTTP/\S+ (\d{3})", lines[0]) if lines else None
    headers = {}
    for line in lines[1:]:
        key, sep, value = line.partition(":")
        if sep:
            headers[key.strip().lower()] = value.strip()
    return (int(m.group(1)) if m else 0), headers, body


def gh_rest_cached(path: str, store: dict, sleep=None, run=None) -> object:
    """GET `path`, revalidating with the ETag kept in `store[path]` ({"etag", "body"}).

    On 304 the stored body is returned; on 200 the store is updated in place."""
    entry = store.get(path) or {}
    args = ["api", "-i", "-H", "Accept: application/vnd.github+json"]
    if entry.get("etag") and "body" in entry:
        args += ["-H", f"If-None-Match: {entry['etag']}"]
    out = _gh(args + [path], sleep=sleep, run=run, ok_status=(304,))
    status, headers, body = parse_response(out)
    if status == 304 and "body" in entry:
        return entry["body"]
    data = json.loads(body)
    if headers.get("etag"):
        store[path] = {"etag": headers["etag"], "body": data}
    return data


def rate_limit() -> dict:
    try:
        data = gh_rest("rate_limit")
        res = data.get("resources", {})
        return {
            k: {"remaining": res[k]["remaining"], "limit": res[k]["limit"]}
            for k in ("core", "graphql", "search")
            if k in res
        }
    except GhError:
        return {}
