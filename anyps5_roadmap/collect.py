"""Collect upstream issues and PRs over GraphQL into the raw cache (data/cache).

Two passes keep a full run cheap:

1. A listing of every open issue and PR, and of those closed or merged inside the window,
   with their own fields and the counts of their comments, reviews, review threads and
   cross-references. About one GraphQL point per 50 to 100 threads.
2. The threads themselves (comments, reviews, review-thread comments, cross-references),
   fetched only where something is there to read and the thread changed since
   data/cache/threads.json was written (its updatedAt differs), or the cached copy is
   older than its time to live. Up to BATCH threads share one query as aliases, and every
   nested connection asks for exactly as many nodes as the listing counted, so the cost
   tracks the data that is actually read.

Every query asks for rateLimit { cost remaining }; the total lands in raw["api"].
"""

from __future__ import annotations

import datetime as dt
import json
from collections import defaultdict
from pathlib import Path

from .github import GhError, gh_graphql, gh_rest

THREADS_FILE = "threads.json"
THREADS_VERSION = 1
BATCH = 25  # threads per query
BATCH_NODES = 1200  # and at most this many requested nodes per query
TTL_HOURS = 24  # a cached thread is read again after 24 to 47 hours, spread by number
REVIEW_THREAD_COMMENTS = 50
PAGE = 100

COMMENT = "body url createdAt author { login __typename }"
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

LIST_QUERY = """
query($owner: String!, $name: String!, $cursor: String, $states: [%s!]) {
  repository(owner: $owner, name: $name) {
    %s(first: 100, after: $cursor, states: $states, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes { %s }
    }
  }
  rateLimit { cost remaining }
}
"""
ISSUES_QUERY = LIST_QUERY % ("IssueState", "issues", ISSUE_FIELDS)
PRS_QUERY = LIST_QUERY % ("PullRequestState", "pullRequests", PR_FIELDS)

MORE_QUERY = """
query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    thread: %s(number: $number) { %s }
  }
  rateLimit { cost remaining }
}
"""


class Api:
    """GraphQL and REST calls with the GraphQL cost added up (tests pass fakes in)."""

    def __init__(self, graphql=gh_graphql, rest=gh_rest):
        self._graphql, self.rest = graphql, rest
        self.queries = 0
        self.cost = 0
        self.remaining = None

    def graphql(self, query: str, variables: dict | None = None) -> dict:
        data = self._graphql(query, variables or {})
        self.queries += 1
        rl = data.get("rateLimit") or {}
        self.cost += rl.get("cost") or 0
        if rl.get("remaining") is not None:
            self.remaining = rl["remaining"]
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


# -- pass 1: listings ---------------------------------------------------------


def _paged(api: Api, query: str, key: str, owner: str, name: str, states: list[str], cutoff: str | None, log):
    out, cursor, cost = [], None, api.cost
    while True:
        data = api.graphql(query, {"owner": owner, "name": name, "cursor": cursor, "states": states})
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
    log(f"  {key} {','.join(states)}: {len(out)} (graphql cost {api.cost - cost})")
    return out


# -- pass 2: threads ----------------------------------------------------------


def counts_of(kind: str, node: dict) -> dict[str, int]:
    out = {"comments": node.get("comment_count", 0), "xrefs": node.get("xref_count", 0)}
    if kind == "pr":
        out.update(reviews=node.get("review_count", 0), threads=node.get("thread_count", 0))
    return out


def thread_fields(kind: str, counts: dict[str, int]) -> str:
    """The nested connections one thread needs, each sized to what the listing counted."""
    parts = ["number updatedAt"]
    if counts.get("comments"):
        n = min(PAGE, counts["comments"])
        parts.append(f"comments(first: {n}) {{ pageInfo {{ hasNextPage endCursor }} nodes {{ {COMMENT} }} }}")
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


def _requested(counts: dict[str, int]) -> int:
    threads = min(PAGE, counts.get("threads", 0))
    return sum(min(PAGE, v) for v in counts.values()) + threads * REVIEW_THREAD_COMMENTS


def batches(wanted: list[tuple[str, int, dict]]) -> list[list[tuple[str, int, dict]]]:
    out, cur, nodes = [], [], 0
    for item in wanted:
        need = _requested(item[2])
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
        field = "issue" if kind == "issue" else "pullRequest"
        fields.append(f"{kind[0]}{number}: {field}(number: {number}) {{ {thread_fields(kind, counts)} }}")
    return (
        "query($owner: String!, $name: String!) { repository(owner: $owner, name: $name) { "
        + " ".join(fields)
        + " } rateLimit { cost remaining } }"
    )


def _more(api: Api, owner: str, name: str, kind: str, number: int, conn: str, cursor: str) -> list[dict]:
    """Further pages of one connection of one thread (more than PAGE comments or references)."""
    field = "issue" if kind == "issue" else "pullRequest"
    if conn == "comments":
        sel = (
            f"comments(first: {PAGE}, after: $cursor) {{ pageInfo {{ hasNextPage endCursor }} nodes {{ {COMMENT} }} }}"
        )
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
    empty = {"version": THREADS_VERSION, "issue": {}, "pr": {}}
    path = cache_dir / THREADS_FILE if cache_dir else None
    if not path or not path.exists():
        return empty
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty
    return data if data.get("version") == THREADS_VERSION else empty


def save_threads(cache_dir: Path | None, threads: dict) -> None:
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / THREADS_FILE).write_text(json.dumps(threads), encoding="utf-8")


def fetch_threads(api: Api, owner: str, name: str, items: dict[str, list[dict]], threads: dict, now, log) -> dict:
    """Bring threads.json up to date for the listed issues and PRs; returns what was read."""
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    wanted, empty, cached = [], 0, 0
    for kind, nodes in items.items():
        for node in nodes:
            key = str(node["number"])
            counts = counts_of(kind, node)
            entry = threads[kind].get(key)
            if not _stale(entry, node["number"], node["updatedAt"], now):
                cached += 1
            elif not any(counts.values()):
                threads[kind][key] = thread_entry(kind, {"updatedAt": node["updatedAt"]}, stamp)
                empty += 1
            else:
                wanted.append((kind, node["number"], counts))
    cost = api.cost
    for batch in batches(wanted):
        data = api.graphql(threads_query(batch), {"owner": owner, "name": name})
        for kind, number, _ in batch:
            node = data["repository"].get(f"{kind[0]}{number}")
            if not node:
                continue

            def more(conn, cursor, kind=kind, number=number):
                return _more(api, owner, name, kind, number, conn, cursor)

            threads[kind][str(number)] = thread_entry(kind, node, stamp, more)
    log(
        f"  threads: {len(wanted)} read in {len(batches(wanted))} queries (graphql cost {api.cost - cost}), "
        f"{cached} unchanged from the cache, {empty} without comments or references"
    )
    return {"read": len(wanted), "cached": cached, "empty": empty, "cost": api.cost - cost}


def merge_threads(kind: str, node: dict, entry: dict | None) -> dict:
    entry = entry or {}
    node["comments"] = entry.get("comments", [])
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
) -> dict:
    owner, name = repo.split("/")
    api = api or Api()
    now = now or dt.datetime.now(dt.UTC)
    issues = _paged(api, ISSUES_QUERY, "issues", owner, name, ["OPEN"], None, log)
    issues += _paged(api, ISSUES_QUERY, "issues", owner, name, ["CLOSED"], cutoff, log)
    issues = [_flatten_issue(i) for i in issues]
    prs = _paged(api, PRS_QUERY, "pullRequests", owner, name, ["OPEN"], None, log)
    prs += _paged(api, PRS_QUERY, "pullRequests", owner, name, ["CLOSED", "MERGED"], cutoff, log)
    prs = [_flatten_pr(p) for p in prs]

    threads = {"version": THREADS_VERSION, "issue": {}, "pr": {}} if refresh else load_threads(cache_dir)
    read = fetch_threads(api, owner, name, {"issue": issues, "pr": prs}, threads, now, log)
    issues = [merge_threads("issue", i, threads["issue"].get(str(i["number"]))) for i in issues]
    prs = [merge_threads("pr", p, threads["pr"].get(str(p["number"]))) for p in prs]
    truncated = [f"PR #{n}: {t}" for n, e in threads["pr"].items() for t in e.get("truncated", [])]
    save_threads(cache_dir, threads)

    # GitHub-native "blocked by" dependencies. The summary comes with the listing;
    # the REST endpoint is called only where the summary is non-zero and for
    # curated blocker issues, and 404s are tolerated.
    deps: dict[str, list] = {}
    curated_issue_numbers = {b["issue"] for b in curated.get("blockers", []) if b.get("issue")}
    for issue in issues:
        summary = issue.get("issueDependenciesSummary") or {}
        if not summary.get("totalBlockedBy") and issue["number"] not in curated_issue_numbers:
            continue
        if issue["state"] != "OPEN" and not summary.get("totalBlockedBy"):
            continue
        try:
            rows = api.rest(f"repos/{repo}/issues/{issue['number']}/dependencies/blocked_by?per_page=100")
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
        except GhError as e:
            if e.status not in (404, 410):
                raise
            deps[str(issue["number"])] = []
    log(f"  dependencies queried for {len(deps)} issues")

    # PRs outside the upstream repo (fork PRs) named in the curated file.
    external = collect_external_prs(api, repo, curated, issues, log)
    log(f"  graphql: {api.queries} queries, cost {api.cost}, remaining {api.remaining}")
    return {
        "fetched_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": repo,
        "cutoff": cutoff,
        "issues": issues,
        "prs": prs,
        "dependencies": deps,
        "external_prs": external,
        # GraphQL's own rateLimit; the REST /rate_limit view of the graphql bucket lags behind it
        "rate_limit": {"graphql": {"cost": api.cost, "remaining": api.remaining}},
        "api": {
            "graphql_queries": api.queries,
            "graphql_cost": api.cost,
            "graphql_remaining": api.remaining,
            "threads_read": read["read"],
            "threads_from_cache": read["cached"],
            "threads_without_text": read["empty"],
            "thread_cost": read["cost"],
        },
        "truncated": truncated,
    }


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
                f'query {{ repository(owner: "{owner}", name: "{name}") {{ {fields} }} rateLimit {{ cost remaining }} }}'
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
