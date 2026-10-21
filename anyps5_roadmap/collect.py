"""Collect upstream issues, PRs and discussions over GraphQL into the raw cache (data/cache).

Two passes keep a run cheap:

1. A listing of every open issue, PR and discussion, and of those closed, merged or
   updated inside the window, with their own fields and the counts of their comments,
   reviews, review threads and cross-references. The listing is kept in
   data/cache/listing.json with one updatedAt cursor per kind. A run with a usable listing
   asks only for what changed (UPDATED_AT descending over all states, stopped at the first
   node older than the cursor minus a 10 minute overlap), upserts it, and derives the
   window from the stored nodes. A full listing (about 50 pages for the PRs) happens when
   there is no listing, its version or window differs, refresh is set, or the last full
   listing is over 7 days old, which also drops items that were deleted or transferred.
2. The threads themselves (comments, reviews, review-thread comments, cross-references;
   for discussions the comments with their replies flattened behind them), fetched only
   where something is there to read and the thread changed since data/cache/threads.json
   was written (its updatedAt differs), or the cached copy is older than its time to live.
   Up to BATCH threads share one query as aliases, and every nested connection asks for
   exactly as many nodes as the listing counted, so the cost tracks the data that is
   actually read. Newest threads go first.

Every query asks for rateLimit { cost remaining resetAt }; the total lands in raw["api"].
When the remaining GraphQL budget falls below RESERVE, or GitHub answers that the rate limit
is spent, the thread pass stops: threads not read keep their cached copy (or none), and
raw["api"]["partial"], raw["api"]["unread_threads"] and raw["truncated"] say so. The next run
picks them up, because their cache entries are still stale. The pass also writes threads.json every
CHECKPOINT_SECONDS, so a run stopped by the workflow's time limit keeps the threads it read.

The REST dependency calls keep the ETag and body of the last answer in data/cache/etags.json
and send If-None-Match; a 304 reuses the body and costs no REST rate limit.
"""

from __future__ import annotations

import datetime as dt
import json
import time
from collections import defaultdict
from pathlib import Path

from .github import GhError, RateLimited, gh_graphql, gh_rest, gh_rest_cached

THREADS_FILE = "threads.json"
THREADS_VERSION = 1
LISTING_FILE = "listing.json"
LISTING_VERSION = 1
ETAGS_FILE = "etags.json"
FULL_LISTING_DAYS = 7  # a full listing again after this long, to drop deleted or transferred items
OVERLAP = dt.timedelta(minutes=10)  # an incremental listing reaches this far behind its cursor
RESERVE = 500  # GraphQL points that stay unspent; below this the thread pass stops
BATCH = 25  # threads per query
BATCH_NODES = 1200  # and at most this many requested nodes per query
TTL_HOURS = 24  # a cached thread is read again after 24 to 47 hours, spread by number
REVIEW_THREAD_COMMENTS = 50
CHECKPOINT_SECONDS = 120  # the thread pass writes threads.json at least this often
REPLIES = 50  # replies read per discussion comment
REPLY_WEIGHT = 10  # nodes a discussion comment counts for in a batch (itself and its replies)
PAGE = 100

COMMENT = "body url createdAt author { login __typename }"
DISCUSSION_COMMENT = f"{COMMENT} replies(first: {REPLIES}) {{ totalCount nodes {{ {COMMENT} }} }}"
XREF_SOURCE = """__typename
  ... on PullRequest { number title url state merged updatedAt isDraft repository { nameWithOwner } }
  ... on Issue { number title url state repository { nameWithOwner } }"""
XREF_NODE = """__typename
... on CrossReferencedEvent { createdAt willCloseTarget source { %s } }
... on ConnectedEvent { createdAt subject { %s } }""" % (XREF_SOURCE, XREF_SOURCE)
XREF_TYPES = {"issue": "CROSS_REFERENCED_EVENT, CONNECTED_EVENT", "pr": "CROSS_REFERENCED_EVENT"}

ISSUE_FIELDS = """
number title body url state stateReason createdAt updatedAt closedAt
author { login }
assignees(first: 5) { nodes { login } }
labels(first: 20) { nodes { name } }
comments { totalCount }
timelineItems(itemTypes: [CROSS_REFERENCED_EVENT, CONNECTED_EVENT]) { filteredCount }
issueDependenciesSummary { blockedBy totalBlockedBy blocking totalBlocking }
closedByPullRequestsReferences(first: 10, includeClosedPrs: true) { nodes { number title url state merged updatedAt repository { nameWithOwner } } }
"""

PR_FIELDS = """
number title body url state merged mergedAt closedAt createdAt updatedAt isDraft
author { login }
labels(first: 20) { nodes { name } }
closingIssuesReferences(first: 10) { nodes { number repository { nameWithOwner } } }
comments { totalCount }
reviews { totalCount }
reviewThreads { totalCount }
timelineItems(itemTypes: [CROSS_REFERENCED_EVENT]) { filteredCount }
"""

DISCUSSION_FIELDS = """
number title body url createdAt updatedAt lastEditedAt closed closedAt
author { login }
category { name }
comments { totalCount }
"""

LIST_QUERY = """
query($owner: String!, $name: String!, $cursor: String%s) {
  repository(owner: $owner, name: $name) {
    %s(first: 100, after: $cursor%s, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes { %s }
    }
  }
  rateLimit { cost remaining resetAt }
}
"""
ISSUES_QUERY = LIST_QUERY % (", $states: [IssueState!]", "issues", ", states: $states", ISSUE_FIELDS)
PRS_QUERY = LIST_QUERY % (", $states: [PullRequestState!]", "pullRequests", ", states: $states", PR_FIELDS)
DISCUSSIONS_QUERY = LIST_QUERY % ("", "discussions", "", DISCUSSION_FIELDS)

# kind -> (listing query, GraphQL connection, states for an incremental listing)
LISTINGS = {
    "issue": (ISSUES_QUERY, "issues", ["OPEN", "CLOSED"]),
    "pr": (PRS_QUERY, "pullRequests", ["OPEN", "CLOSED", "MERGED"]),
    "discussion": (DISCUSSIONS_QUERY, "discussions", None),
}
FIELD = {"issue": "issue", "pr": "pullRequest", "discussion": "discussion"}

MORE_QUERY = """
query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    thread: %s(number: $number) { %s }
  }
  rateLimit { cost remaining resetAt }
}
"""


class Api:
    """GraphQL and REST calls with the GraphQL cost added up (tests pass fakes in)."""

    def __init__(self, graphql=gh_graphql, rest=gh_rest, rest_cached=None):
        self._graphql, self.rest = graphql, rest
        # a custom `rest` without a cached variant serves both
        self.rest_cached = rest_cached or (gh_rest_cached if rest is gh_rest else lambda path, store: rest(path))
        self.queries = 0
        self.cost = 0
        self.remaining = None
        self.reset_at = None

    def graphql(self, query: str, variables: dict | None = None) -> dict:
        data = self._graphql(query, variables or {})
        self.queries += 1
        rl = data.get("rateLimit") or {}
        self.cost += rl.get("cost") or 0
        if rl.get("remaining") is not None:
            self.remaining = rl["remaining"]
        if rl.get("resetAt"):
            self.reset_at = rl["resetAt"]
        return data


# -- normalising GraphQL nodes ------------------------------------------------


def _login(node: dict | None) -> str | None:
    author = (node or {}).get("author") or {}
    login = author.get("login")
    return f"{login}[bot]" if login and author.get("__typename") == "Bot" and not login.endswith("[bot]") else login


def _comment(c: dict) -> dict:
    return {"body": c.get("body") or "", "url": c["url"], "createdAt": c["createdAt"], "author": _login(c)}


def _xref(ev: dict) -> dict | None:
    src = ev.get("source") or ev.get("subject")
    if not src or "number" not in src:
        return None
    return {
        "kind": "pr" if src.get("__typename") == "PullRequest" else "issue",
        "repo": src["repository"]["nameWithOwner"],
        "number": src["number"],
        "title": src.get("title"),
        "url": src.get("url"),
        "state": src.get("state"),
        "merged": src.get("merged"),
        "draft": src.get("isDraft"),
        "updatedAt": src.get("updatedAt"),
        "event": ev["__typename"],
        "createdAt": ev.get("createdAt"),
        "willClose": ev.get("willCloseTarget", False) or ev["__typename"] == "ConnectedEvent",
    }


def _flatten_issue(node: dict) -> dict:
    node["labels"] = [lb["name"] for lb in node.get("labels", {}).get("nodes", [])]
    node["author"] = _login(node)
    node["assignees"] = [a["login"] for a in (node.get("assignees") or {}).get("nodes", [])]
    node["comment_count"] = (node.pop("comments", None) or {}).get("totalCount", 0)
    node["xref_count"] = (node.pop("timelineItems", None) or {}).get("filteredCount", 0)
    node["closed_by"] = [
        {
            "repo": p["repository"]["nameWithOwner"],
            "number": p["number"],
            "title": p.get("title"),
            "url": p["url"],
            "state": p["state"],
            "merged": p.get("merged"),
            "updatedAt": p.get("updatedAt"),
        }
        for p in (node.pop("closedByPullRequestsReferences", None) or {}).get("nodes", [])
    ]
    return node


def _flatten_pr(node: dict) -> dict:
    node["labels"] = [lb["name"] for lb in node.get("labels", {}).get("nodes", [])]
    node["author"] = _login(node)
    node["closes"] = [
        {"repo": n["repository"]["nameWithOwner"], "number": n["number"]}
        for n in (node.pop("closingIssuesReferences", None) or {}).get("nodes", [])
    ]
    node["comment_count"] = (node.pop("comments", None) or {}).get("totalCount", 0)
    node["review_count"] = (node.pop("reviews", None) or {}).get("totalCount", 0)
    node["thread_count"] = (node.pop("reviewThreads", None) or {}).get("totalCount", 0)
    node["xref_count"] = (node.pop("timelineItems", None) or {}).get("filteredCount", 0)
    return node


def _flatten_discussion(node: dict) -> dict:
    node["author"] = _login(node)
    node["editedAt"] = node.pop("lastEditedAt", None)
    node["category"] = (node.pop("category", None) or {}).get("name")
    node["comment_count"] = (node.pop("comments", None) or {}).get("totalCount", 0)
    return node


FLATTEN = {"issue": _flatten_issue, "pr": _flatten_pr, "discussion": _flatten_discussion}


# -- pass 1: listings ---------------------------------------------------------


def _paged(api: Api, query: str, key: str, owner: str, name: str, states: list[str] | None, cutoff: str | None, log):
    """Pages of one connection, newest update first, until a node is older than `cutoff`."""
    out, cursor, cost = [], None, api.cost
    while True:
        variables = {"owner": owner, "name": name, "cursor": cursor}
        if states is not None:
            variables["states"] = states
        data = api.graphql(query, variables)
        conn = data["repository"][key]
        stop = False
        for node in conn["nodes"]:
            if cutoff and node["updatedAt"] < cutoff:
                stop = True
                break
            out.append(node)
        if stop or not conn["pageInfo"]["hasNextPage"]:
            break
        cursor = conn["pageInfo"]["endCursor"]
    log(f"  {key} {','.join(states or ['all'])}: {len(out)} (graphql cost {api.cost - cost})")
    return out


def _iso(t: dt.datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(stamp: str) -> dt.datetime:
    return dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def load_listing(cache_dir: Path | None) -> dict | None:
    path = cache_dir / LISTING_FILE if cache_dir else None
    if not path or not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) and data.get("version") == LISTING_VERSION else None


def save_listing(cache_dir: Path | None, listing: dict) -> None:
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / LISTING_FILE).write_text(json.dumps(listing), encoding="utf-8")


def _incremental_ok(listing: dict | None, cutoff: str, now: dt.datetime, refresh: bool) -> bool:
    """Whether the stored listing can be brought up to date by asking for what changed."""
    if not listing or refresh:
        return False
    try:
        if now - _parse(listing["full_at"]) > dt.timedelta(days=FULL_LISTING_DAYS):
            return False
        return cutoff >= listing["cutoff"] and all(k in listing["since"] and k in listing for k in LISTINGS)
    except (KeyError, ValueError, TypeError):
        return False


def _is_open(kind: str, node: dict) -> bool:
    return not node.get("closed") if kind == "discussion" else node.get("state") == "OPEN"


def _in_window(kind: str, node: dict, cutoff: str) -> bool:
    return _is_open(kind, node) or node["updatedAt"] >= cutoff


def _full_listing(api: Api, owner: str, name: str, kind: str, cutoff: str, log) -> list[dict]:
    """Every open item and every other item updated since `cutoff` (the two-pass listing)."""
    query, key, states = LISTINGS[kind]
    if kind == "discussion":
        return _paged(api, query, key, owner, name, None, None, log)
    nodes = _paged(api, query, key, owner, name, ["OPEN"], None, log)
    return nodes + _paged(api, query, key, owner, name, states[1:], cutoff, log)


def update_listing(api: Api, owner: str, name: str, cutoff: str, cache_dir: Path | None, now, refresh, log) -> dict:
    """The stored listing brought up to date: incrementally when it can be, else in full."""
    old = load_listing(cache_dir)
    incremental = _incremental_ok(old, cutoff, now, refresh)
    listing = {"version": LISTING_VERSION, "since": {}, "full_at": old["full_at"] if incremental else _iso(now)}
    for kind, (query, key, states) in LISTINGS.items():
        if incremental:
            since = old["since"][kind]
            fresh = _paged(api, query, key, owner, name, states, _iso(_parse(since) - OVERLAP), log)
            log(f"  {kind}: {len(fresh)} changed since {since} (incremental)")
            store = dict(old[kind])
        else:
            fresh = _full_listing(api, owner, name, kind, cutoff, log)
            log(f"  {kind}: {len(fresh)} listed (full)")
            store = {}
        marks = [n["updatedAt"] for n in fresh] + ([old["since"][kind]] if incremental else [])
        for node in fresh:
            store[str(node["number"])] = FLATTEN[kind](node)
        listing["since"][kind] = max(marks, default=_iso(now))
        # closed items older than the window leave the store
        listing[kind] = {k: n for k, n in store.items() if _in_window(kind, n, cutoff)}
    listing["cutoff"] = cutoff
    save_listing(cache_dir, listing)
    return listing


def windowed(kind: str, listing: dict, cutoff: str) -> list[dict]:
    """Copies of the listed nodes in the window: open ones first, each group newest update first."""
    nodes = [dict(n) for n in listing[kind].values() if _in_window(kind, n, cutoff)]
    nodes.sort(key=lambda n: n["updatedAt"], reverse=True)
    return [n for n in nodes if _is_open(kind, n)] + [n for n in nodes if not _is_open(kind, n)]


# -- pass 2: threads ----------------------------------------------------------


def counts_of(kind: str, node: dict) -> dict[str, int]:
    if kind == "discussion":
        return {"comments": node.get("comment_count", 0)}
    out = {"comments": node.get("comment_count", 0), "xrefs": node.get("xref_count", 0)}
    if kind == "pr":
        out.update(reviews=node.get("review_count", 0), threads=node.get("thread_count", 0))
    return out


def thread_fields(kind: str, counts: dict[str, int]) -> str:
    """The nested connections one thread needs, each sized to what the listing counted."""
    parts = ["number updatedAt"]
    if counts.get("comments"):
        n = min(PAGE, counts["comments"])
        node = DISCUSSION_COMMENT if kind == "discussion" else COMMENT
        parts.append(f"comments(first: {n}) {{ pageInfo {{ hasNextPage endCursor }} nodes {{ {node} }} }}")
    if counts.get("reviews"):
        n = min(PAGE, counts["reviews"])
        parts.append(f"reviews(first: {n}) {{ nodes {{ body url submittedAt state author {{ login __typename }} }} }}")
    if counts.get("threads"):
        n = min(PAGE, counts["threads"])
        parts.append(
            f"reviewThreads(first: {n}) {{ nodes {{ path "
            f"comments(first: {REVIEW_THREAD_COMMENTS}) {{ totalCount nodes {{ {COMMENT} }} }} }} }}"
        )
    if counts.get("xrefs"):
        n = min(PAGE, counts["xrefs"])
        parts.append(
            f"timelineItems(first: {n}, itemTypes: [{XREF_TYPES[kind]}]) "
            f"{{ pageInfo {{ hasNextPage endCursor }} nodes {{ {XREF_NODE} }} }}"
        )
    return " ".join(parts)


def _requested(kind: str, counts: dict[str, int]) -> int:
    threads = min(PAGE, counts.get("threads", 0))
    total = sum(min(PAGE, v) for v in counts.values()) + threads * REVIEW_THREAD_COMMENTS
    return total * REPLY_WEIGHT if kind == "discussion" else total


def batches(wanted: list[tuple[str, int, dict]]) -> list[list[tuple[str, int, dict]]]:
    out, cur, nodes = [], [], 0
    for item in wanted:
        need = _requested(item[0], item[2])
        if cur and (len(cur) >= BATCH or nodes + need > BATCH_NODES):
            out.append(cur)
            cur, nodes = [], 0
        cur.append(item)
        nodes += need
    if cur:
        out.append(cur)
    return out


def threads_query(batch: list[tuple[str, int, dict]]) -> str:
    fields = []
    for kind, number, counts in batch:
        fields.append(f"{kind[0]}{number}: {FIELD[kind]}(number: {number}) {{ {thread_fields(kind, counts)} }}")
    return (
        "query($owner: String!, $name: String!) { repository(owner: $owner, name: $name) { "
        + " ".join(fields)
        + " } rateLimit { cost remaining resetAt } }"
    )


def _more(api: Api, owner: str, name: str, kind: str, number: int, conn: str, cursor: str) -> list[dict]:
    """Further pages of one connection of one thread (more than PAGE comments or references)."""
    field = FIELD[kind]
    if conn == "comments":
        node = DISCUSSION_COMMENT if kind == "discussion" else COMMENT
        sel = f"comments(first: {PAGE}, after: $cursor) {{ pageInfo {{ hasNextPage endCursor }} nodes {{ {node} }} }}"
    else:
        sel = (
            f"timelineItems(first: {PAGE}, after: $cursor, itemTypes: [{XREF_TYPES[kind]}]) "
            f"{{ pageInfo {{ hasNextPage endCursor }} nodes {{ {XREF_NODE} }} }}"
        )
    nodes = []
    while cursor:
        data = api.graphql(
            MORE_QUERY % (field, sel), {"owner": owner, "name": name, "number": number, "cursor": cursor}
        )
        page = data["repository"]["thread"][conn]
        nodes += page["nodes"]
        cursor = page["pageInfo"]["endCursor"] if page["pageInfo"]["hasNextPage"] else None
    return nodes


def _with_replies(nodes: list[dict], truncated: list[str]) -> list[dict]:
    """Discussion comments as flat comments, each followed by its replies."""
    out = []
    for c in nodes:
        out.append(_comment(c))
        replies = c.get("replies") or {}
        out += [_comment(r) for r in replies.get("nodes", [])]
        if replies.get("totalCount", 0) > REPLIES:
            truncated.append(f"a comment has {replies['totalCount']} replies, {REPLIES} read")
    return out


def thread_entry(kind: str, node: dict, fetched_at: str, more=None) -> dict:
    """A cache entry from one aliased thread node. `more(conn, cursor)` reads further pages."""
    comments = (node.get("comments") or {}).get("nodes", [])
    page = (node.get("comments") or {}).get("pageInfo") or {}
    if page.get("hasNextPage") and more:
        comments += more("comments", page["endCursor"])
    timeline = (node.get("timelineItems") or {}).get("nodes", [])
    page = (node.get("timelineItems") or {}).get("pageInfo") or {}
    if page.get("hasNextPage") and more:
        timeline += more("timelineItems", page["endCursor"])
    entry = {
        "updatedAt": node["updatedAt"],
        "fetched_at": fetched_at,
        "comments": [_comment(c) for c in comments],
        "xrefs": [x for x in (_xref(ev) for ev in timeline) if x],
    }
    if kind == "discussion":
        entry["truncated"] = []
        entry["comments"] = _with_replies(comments, entry["truncated"])
    if kind == "pr":
        entry["reviews"] = [
            {
                "body": r["body"],
                "url": r["url"],
                "createdAt": r["submittedAt"],
                "author": _login(r),
                "state": r["state"],
            }
            for r in (node.get("reviews") or {}).get("nodes", [])
            if (r.get("body") or "").strip() and r.get("submittedAt")
        ]
        entry["review_comments"] = []
        entry["truncated"] = []
        for t in (node.get("reviewThreads") or {}).get("nodes", []):
            conn = t.get("comments") or {}
            entry["review_comments"] += [{**_comment(c), "path": t.get("path")} for c in conn.get("nodes", [])]
            if conn.get("totalCount", 0) > REVIEW_THREAD_COMMENTS:
                entry["truncated"].append(f"a review thread on {t.get('path')} has {conn['totalCount']} comments")
    return entry


def _stale(entry: dict | None, number: int, updated: str, now: dt.datetime) -> bool:
    if not entry or entry.get("updatedAt") != updated:
        return True
    try:
        fetched = dt.datetime.fromisoformat(entry["fetched_at"].replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return True
    return now - fetched > dt.timedelta(hours=TTL_HOURS + number % TTL_HOURS)


def load_threads(cache_dir: Path | None) -> dict:
    empty = {"version": THREADS_VERSION, "issue": {}, "pr": {}, "discussion": {}}
    path = cache_dir / THREADS_FILE if cache_dir else None
    if not path or not path.exists():
        return empty
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty
    if data.get("version") != THREADS_VERSION:
        return empty
    for kind in empty:
        data.setdefault(kind, {})  # caches from before discussions have no such key
    return data


def save_threads(cache_dir: Path | None, threads: dict) -> None:
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        # written aside and renamed, so a run killed mid-write leaves the previous copy whole
        partial = cache_dir / (THREADS_FILE + ".tmp")
        partial.write_text(json.dumps(threads), encoding="utf-8")
        partial.replace(cache_dir / THREADS_FILE)


def load_etags(cache_dir: Path | None) -> dict:
    path = cache_dir / ETAGS_FILE if cache_dir else None
    if not path or not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_etags(cache_dir: Path | None, etags: dict) -> None:
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / ETAGS_FILE).write_text(json.dumps(etags), encoding="utf-8")


def fetch_threads(
    api: Api, owner: str, name: str, items: dict[str, list[dict]], threads: dict, now, log, checkpoint=None
) -> dict:
    """Bring threads.json up to date for the listed items; returns what was read.

    Stops early, with the rest counted as `unread`, when the GraphQL budget is below RESERVE
    or GitHub reports the rate limit spent; unread threads keep their cached copy. `checkpoint`,
    when given, is called after a query whenever CHECKPOINT_SECONDS have passed since the last call."""
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    wanted, empty, cached, updated, known = [], 0, 0, {}, set()
    for kind, nodes in items.items():
        for node in nodes:
            key = str(node["number"])
            counts = counts_of(kind, node)
            entry = threads.setdefault(kind, {}).get(key)
            if not _stale(entry, node["number"], node["updatedAt"], now):
                cached += 1
            elif not any(counts.values()):
                threads[kind][key] = thread_entry(kind, {"updatedAt": node["updatedAt"]}, stamp)
                empty += 1
            else:
                wanted.append((kind, node["number"], counts))
                updated[(kind, node["number"])] = node["updatedAt"]
                if entry:
                    known.add((kind, node["number"]))
    # threads with no cached copy first, then the most recently updated
    wanted.sort(key=lambda w: updated[w[0], w[1]], reverse=True)
    wanted.sort(key=lambda w: (w[0], w[1]) in known)
    cost, queries, done, why = api.cost, api.queries, 0, None
    queue, failed = batches(wanted), []
    saved = time.monotonic()
    while queue:
        batch = queue.pop(0)
        if api.remaining is not None and api.remaining < RESERVE:
            why = f"the GraphQL budget is low ({api.remaining} left, reserve {RESERVE})"
            break
        stored = set()
        try:
            data = api.graphql(threads_query(batch), {"owner": owner, "name": name})
            for kind, number, _ in batch:
                node = data["repository"].get(f"{kind[0]}{number}")
                if not node:
                    stored.add((kind, number))  # gone since the listing
                    continue

                def more(conn, cursor, kind=kind, number=number):
                    return _more(api, owner, name, kind, number, conn, cursor)

                threads[kind][str(number)] = thread_entry(kind, node, stamp, more)
                stored.add((kind, number))
        except RateLimited as e:
            why = f"GitHub reports the rate limit is spent ({str(e)[:80]})"
            done += len(stored)
            break
        except GhError as e:
            # a query that is too heavy times out (HTTP 499, 502): read it again in halves
            if len(batch) > 1:
                log(f"  threads: a query for {len(batch)} threads failed ({str(e)[:60]}); splitting it")
                queue[:0] = [batch[: len(batch) // 2], batch[len(batch) // 2 :]]
            else:
                failed.append(f"{batch[0][0]} #{batch[0][1]}")
                log(f"  warning: could not read {failed[-1]}: {str(e)[:80]}")
            continue
        done += len(batch)
        if checkpoint and time.monotonic() - saved >= CHECKPOINT_SECONDS:
            checkpoint()
            saved = time.monotonic()
    unread = len(wanted) - done - len(failed)
    if why:
        log(f"  threads: stopped, {unread} left for the next run: {why}")
    log(
        f"  threads: {done} read in {api.queries - queries} queries (graphql cost {api.cost - cost}), "
        f"{cached} unchanged from the cache, {empty} without comments or references"
    )
    return {"read": done, "cached": cached, "empty": empty, "cost": api.cost - cost, "unread": unread, "failed": failed}


def merge_threads(kind: str, node: dict, entry: dict | None) -> dict:
    entry = entry or {}
    node["comments"] = entry.get("comments", [])
    if kind == "discussion":
        return node
    node["xrefs"] = entry.get("xrefs", [])
    if kind == "pr":
        node["reviews"] = entry.get("reviews", [])
        node["review_comments"] = entry.get("review_comments", [])
    return node


# -- the whole collection -----------------------------------------------------


def collect(
    repo: str,
    cutoff: str,
    curated: dict,
    log,
    cache_dir: Path | None = None,
    api: Api | None = None,
    now: dt.datetime | None = None,
    refresh: bool = False,
    working_groups: tuple[str, ...] = (),
) -> dict:
    owner, name = repo.split("/")
    api = api or Api()
    now = now or dt.datetime.now(dt.UTC)
    listing = update_listing(api, owner, name, cutoff, cache_dir, now, refresh, log)
    issues = windowed("issue", listing, cutoff)
    prs = windowed("pr", listing, cutoff)
    discussions = windowed("discussion", listing, cutoff)

    threads = load_threads(None) if refresh else load_threads(cache_dir)
    read = fetch_threads(
        api,
        owner,
        name,
        {"issue": issues, "pr": prs, "discussion": discussions},
        threads,
        now,
        log,
        checkpoint=lambda: save_threads(cache_dir, threads),
    )
    issues = [merge_threads("issue", i, threads["issue"].get(str(i["number"]))) for i in issues]
    prs = [merge_threads("pr", p, threads["pr"].get(str(p["number"]))) for p in prs]
    discussions = [merge_threads("discussion", d, threads["discussion"].get(str(d["number"]))) for d in discussions]
    discussions = [
        {
            "number": d["number"],
            "title": d["title"],
            "body": d.get("body") or "",
            "url": d["url"],
            "createdAt": d["createdAt"],
            "updatedAt": d["updatedAt"],
            "editedAt": d.get("editedAt"),
            "closed": bool(d.get("closed")),
            "category": d.get("category"),
            "author": d.get("author"),
            "comments": d["comments"],
        }
        for d in discussions
    ]
    truncated = [f"PR #{n}: {t}" for n, e in threads["pr"].items() for t in e.get("truncated", [])]
    truncated += [f"Discussion #{n}: {t}" for n, e in threads["discussion"].items() for t in e.get("truncated", [])]
    partial = read["unread"] > 0
    if read["failed"]:
        truncated.append(f"could not read the threads of {', '.join(read['failed'])}; kept from the cache if any")
    if partial:
        truncated.append(
            f"{read['unread']} threads were left for the next run because the GraphQL budget was low "
            f"(remaining {api.remaining}, resets {api.reset_at})"
        )
    save_threads(cache_dir, threads)

    # GitHub-native "blocked by" dependencies. The summary comes with the listing;
    # the REST endpoint is called only where the summary is non-zero and for
    # curated blocker issues, and 404s are tolerated. Answers are revalidated with their
    # ETag (etags.json), so an unchanged list costs no rate limit.
    deps: dict[str, list] = {}
    etags = load_etags(cache_dir)
    used: set[str] = set()
    curated_issue_numbers = {b["issue"] for b in curated.get("blockers", []) if b.get("issue")}
    for issue in issues:
        summary = issue.get("issueDependenciesSummary") or {}
        if not summary.get("totalBlockedBy") and issue["number"] not in curated_issue_numbers:
            continue
        if issue["state"] != "OPEN" and not summary.get("totalBlockedBy"):
            continue
        path = f"repos/{repo}/issues/{issue['number']}/dependencies/blocked_by?per_page=100"
        used.add(path)
        try:
            rows = api.rest_cached(path, etags)
            deps[str(issue["number"])] = [
                {
                    "number": r["number"],
                    "url": r.get("html_url"),
                    "state": r.get("state"),
                    "title": r.get("title"),
                    "repo": (r.get("repository_url") or "").split("/repos/")[-1] or repo,
                }
                for r in rows
            ]
        except RateLimited as e:
            log(f"  warning: REST rate limit spent, dependencies of #{issue['number']} and later skipped: {e}")
            partial = True
            break
        except GhError as e:
            if e.status not in (404, 410):
                raise
            deps[str(issue["number"])] = []
    if not partial:
        etags = {p: v for p, v in etags.items() if p in used}  # forget issues that left the window
    save_etags(cache_dir, etags)
    log(f"  dependencies queried for {len(deps)} issues")

    # PRs outside the upstream repo (fork PRs) named in the curated file.
    external = collect_external_prs(api, repo, curated, issues, log)
    groups = collect_working_groups(api, working_groups, log)
    log(f"  graphql: {api.queries} queries, cost {api.cost}, remaining {api.remaining}")
    return {
        "fetched_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": repo,
        "cutoff": cutoff,
        "issues": issues,
        "prs": prs,
        "discussions": discussions,
        "working_groups": groups,
        "dependencies": deps,
        "external_prs": external,
        # GraphQL's own rateLimit; the REST /rate_limit view of the graphql bucket lags behind it
        "rate_limit": {"graphql": {"cost": api.cost, "remaining": api.remaining}},
        "api": {
            "graphql_queries": api.queries,
            "graphql_cost": api.cost,
            "graphql_remaining": api.remaining,
            "graphql_reset_at": api.reset_at,
            "threads_read": read["read"],
            "threads_from_cache": read["cached"],
            "threads_without_text": read["empty"],
            "thread_cost": read["cost"],
            "partial": partial,
            "unread_threads": read["unread"],
        },
        "truncated": truncated,
    }


WORKING_GROUP_QUERY = (
    """
query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) {
      number title body url createdAt updatedAt author { login __typename }
      comments(first: 100, after: $cursor) { pageInfo { hasNextPage endCursor } nodes { %s } }
    }
  }
  rateLimit { cost remaining resetAt }
}
"""
    % COMMENT
)


def collect_working_groups(api: Api, refs: tuple[str, ...], log) -> list[dict]:
    """The working-group threads (issues of other repositories, "Owner/Repo#N") with all of their comments.
    A thread that cannot be read is skipped with a note; it never stops the build."""
    out = []
    for ref in refs:
        repo, _, number = ref.partition("#")
        owner, name = repo.split("/")
        comments, cursor, issue = [], None, None
        try:
            while True:
                data = api.graphql(
                    WORKING_GROUP_QUERY, {"owner": owner, "name": name, "number": int(number), "cursor": cursor}
                )
                issue = (data.get("repository") or {}).get("issue")
                if not issue:
                    break
                page = issue["comments"]
                comments += [_comment(c) for c in page["nodes"] if not (_login(c) or "").endswith("[bot]")]
                if not page["pageInfo"]["hasNextPage"]:
                    break
                cursor = page["pageInfo"]["endCursor"]
        except GhError as e:
            log(f"  warning: working group {ref} could not be read: {e}")
            continue
        if issue:
            out.append(
                {
                    "repo": repo,
                    "number": issue["number"],
                    "title": issue["title"],
                    "body": issue.get("body") or "",
                    "url": issue["url"],
                    "createdAt": issue["createdAt"],
                    "updatedAt": issue["updatedAt"],
                    "author": _login(issue),
                    "comments": comments,
                }
            )
    if refs:
        log(f"  working groups: {len(out)} read, {sum(len(g['comments']) for g in out)} comments")
    return out


def collect_external_prs(api: Api, repo: str, curated: dict, issues: list[dict], log) -> dict:
    wanted: set[tuple[str, int]] = set()
    for b in curated.get("blockers", []):
        for ref in b.get("fix_prs", []) + b.get("related_prs", []):
            r = ref.get("repo", repo)
            if r != repo:
                wanted.add((r, int(ref["number"])))
    known = {}
    for issue in issues:
        for x in issue["xrefs"] + issue["closed_by"]:
            if x.get("repo") != repo and (x.get("kind", "pr") == "pr"):
                known[f"{x['repo']}#{x['number']}"] = x
    missing = sorted(w for w in wanted if f"{w[0]}#{w[1]}" not in known)
    by_repo: dict[str, list[int]] = defaultdict(list)
    for r, n in missing:
        by_repo[r].append(n)
    out = {
        k: {
            "repo": v["repo"],
            "number": v["number"],
            "title": v.get("title"),
            "url": v.get("url"),
            "state": v.get("state"),
            "merged": v.get("merged"),
            "draft": v.get("draft"),
            "updatedAt": v.get("updatedAt"),
        }
        for k, v in known.items()
    }
    for r, numbers in by_repo.items():
        owner, name = r.split("/")
        fields = " ".join(
            f"p{n}: pullRequest(number: {n}) {{ number title url state merged isDraft updatedAt }}" for n in numbers
        )
        try:
            data = api.graphql(
                f'query {{ repository(owner: "{owner}", name: "{name}") {{ {fields} }} rateLimit {{ cost remaining resetAt }} }}'
            )
        except GhError as e:
            log(f"  warning: could not read PRs from {r}: {e}")
            continue
        for n in numbers:
            p = (data.get("repository") or {}).get(f"p{n}")
            if p:
                out[f"{r}#{n}"] = {
                    "repo": r,
                    "number": n,
                    "title": p["title"],
                    "url": p["url"],
                    "state": p["state"],
                    "merged": p["merged"],
                    "draft": p["isDraft"],
                    "updatedAt": p["updatedAt"],
                }
    log(f"  external PRs: {len(out)}")
    return out
