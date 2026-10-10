"""Collect upstream issues and PRs over GraphQL into the raw cache (data/cache)."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict

from .github import GhError, gh_graphql, gh_rest, rate_limit


ISSUE_FIELDS = """
number title body url state stateReason createdAt updatedAt closedAt
author { login }
assignees(first: 5) { nodes { login } }
labels(first: 20) { nodes { name } }
comments(first: 100) { totalCount pageInfo { hasNextPage endCursor } nodes { body url createdAt author { login } } }
issueDependenciesSummary { blockedBy totalBlockedBy blocking totalBlocking }
closedByPullRequestsReferences(first: 10, includeClosedPrs: true) { nodes { number title url state merged updatedAt repository { nameWithOwner } } }
timelineItems(first: 100, itemTypes: [CROSS_REFERENCED_EVENT, CONNECTED_EVENT]) {
  nodes {
    __typename
    ... on CrossReferencedEvent { createdAt willCloseTarget source { __typename
      ... on PullRequest { number title url state merged updatedAt isDraft repository { nameWithOwner } }
      ... on Issue { number title url state repository { nameWithOwner } } } }
    ... on ConnectedEvent { createdAt subject { __typename
      ... on PullRequest { number title url state merged updatedAt isDraft repository { nameWithOwner } } } }
  }
}
"""

ISSUES_QUERY = """
query($owner: String!, $name: String!, $cursor: String, $states: [IssueState!]) {
  repository(owner: $owner, name: $name) {
    issues(first: 40, after: $cursor, states: $states, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes { %s }
    }
  }
  rateLimit { cost remaining }
}
""" % ISSUE_FIELDS

PR_FIELDS = """
number title body url state merged mergedAt closedAt createdAt updatedAt isDraft
author { login }
labels(first: 20) { nodes { name } }
closingIssuesReferences(first: 10) { nodes { number repository { nameWithOwner } } }
comments { totalCount }
"""

PRS_QUERY = """
query($owner: String!, $name: String!, $cursor: String, $states: [PullRequestState!]) {
  repository(owner: $owner, name: $name) {
    pullRequests(first: 100, after: $cursor, states: $states, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes { %s }
    }
  }
  rateLimit { cost remaining }
}
""" % PR_FIELDS

COMMENTS_QUERY = """
query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) {
      comments(first: 100, after: $cursor) { pageInfo { hasNextPage endCursor } nodes { body url createdAt author { login } } }
    }
  }
}
"""


def _flatten_issue(node: dict) -> dict:
    node["labels"] = [l["name"] for l in node.get("labels", {}).get("nodes", [])]
    node["author"] = (node.get("author") or {}).get("login")
    node["assignees"] = [a["login"] for a in (node.get("assignees") or {}).get("nodes", [])]
    comments = node.get("comments") or {}
    node["comment_count"] = comments.get("totalCount", 0)
    node["comments"] = [
        {"body": c.get("body") or "", "url": c["url"], "createdAt": c["createdAt"], "author": (c.get("author") or {}).get("login")}
        for c in comments.get("nodes", [])
    ]
    node["_comments_page"] = comments.get("pageInfo", {})
    refs = []
    for ev in (node.pop("timelineItems", None) or {}).get("nodes", []):
        src = ev.get("source") or ev.get("subject")
        if not src or "number" not in src:
            continue
        refs.append({
            "kind": "pr" if src.get("__typename") == "PullRequest" else "issue",
            "repo": src["repository"]["nameWithOwner"],
            "number": src["number"], "title": src.get("title"), "url": src.get("url"),
            "state": src.get("state"), "merged": src.get("merged"), "draft": src.get("isDraft"),
            "updatedAt": src.get("updatedAt"), "event": ev["__typename"], "createdAt": ev.get("createdAt"),
            "willClose": ev.get("willCloseTarget", False) or ev["__typename"] == "ConnectedEvent",
        })
    node["xrefs"] = refs
    node["closed_by"] = [
        {"repo": p["repository"]["nameWithOwner"], "number": p["number"], "title": p.get("title"), "url": p["url"],
         "state": p["state"], "merged": p.get("merged"), "updatedAt": p.get("updatedAt")}
        for p in (node.pop("closedByPullRequestsReferences", None) or {}).get("nodes", [])
    ]
    return node


def _flatten_pr(node: dict) -> dict:
    node["labels"] = [l["name"] for l in node.get("labels", {}).get("nodes", [])]
    node["author"] = (node.get("author") or {}).get("login")
    node["closes"] = [
        {"repo": n["repository"]["nameWithOwner"], "number": n["number"]}
        for n in (node.pop("closingIssuesReferences", None) or {}).get("nodes", [])
    ]
    node["comment_count"] = (node.get("comments") or {}).get("totalCount", 0)
    node.pop("comments", None)
    return node


def _paged(query: str, key: str, owner: str, name: str, states: list[str], cutoff: str | None, log) -> list[dict]:
    out, cursor, cost = [], None, 0
    while True:
        data = gh_graphql(query, {"owner": owner, "name": name, "cursor": cursor, "states": states})
        cost += data.get("rateLimit", {}).get("cost", 0)
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
    log(f"  {key} {','.join(states)}: {len(out)} (graphql cost {cost})")
    return out


def collect(repo: str, cutoff: str, curated: dict, log) -> dict:
    owner, name = repo.split("/")
    before = rate_limit()
    issues = _paged(ISSUES_QUERY, "issues", owner, name, ["OPEN"], None, log)
    issues += _paged(ISSUES_QUERY, "issues", owner, name, ["CLOSED"], cutoff, log)
    issues = [_flatten_issue(i) for i in issues]
    for issue in issues:
        page = issue.pop("_comments_page", {})
        cursor = page.get("endCursor")
        while page.get("hasNextPage"):
            data = gh_graphql(COMMENTS_QUERY, {"owner": owner, "name": name, "number": issue["number"], "cursor": cursor})
            conn = data["repository"]["issue"]["comments"]
            issue["comments"] += [
                {"body": c.get("body") or "", "url": c["url"], "createdAt": c["createdAt"], "author": (c.get("author") or {}).get("login")}
                for c in conn["nodes"]
            ]
            page, cursor = conn["pageInfo"], conn["pageInfo"]["endCursor"]
    prs = _paged(PRS_QUERY, "pullRequests", owner, name, ["OPEN"], None, log)
    prs += _paged(PRS_QUERY, "pullRequests", owner, name, ["CLOSED", "MERGED"], cutoff, log)
    prs = [_flatten_pr(p) for p in prs]

    # GitHub-native "blocked by" dependencies. The summary comes with the bulk
    # query; the REST endpoint is called only where the summary is non-zero
    # and for curated blocker issues, and 404s are tolerated.
    deps: dict[str, list] = {}
    curated_issue_numbers = {b["issue"] for b in curated.get("blockers", []) if b.get("issue")}
    for issue in issues:
        summary = issue.get("issueDependenciesSummary") or {}
        if not summary.get("totalBlockedBy") and issue["number"] not in curated_issue_numbers:
            continue
        if issue["state"] != "OPEN" and not summary.get("totalBlockedBy"):
            continue
        try:
            rows = gh_rest(f"repos/{repo}/issues/{issue['number']}/dependencies/blocked_by?per_page=100")
            deps[str(issue["number"])] = [
                {"number": r["number"], "url": r.get("html_url"), "state": r.get("state"), "title": r.get("title"),
                 "repo": (r.get("repository_url") or "").split("/repos/")[-1] or repo}
                for r in rows
            ]
        except GhError as e:
            if e.status not in (404, 410):
                raise
            deps[str(issue["number"])] = []
    log(f"  dependencies queried for {len(deps)} issues")

    # PRs outside the upstream repo (fork PRs) named in the curated file.
    external = collect_external_prs(repo, curated, issues, log)
    after = rate_limit()
    return {
        "fetched_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": repo, "cutoff": cutoff,
        "issues": issues, "prs": prs, "dependencies": deps, "external_prs": external,
        "rate_limit": {"before": before, "after": after},
    }


def collect_external_prs(repo: str, curated: dict, issues: list[dict], log) -> dict:
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
    out = {k: {"repo": v["repo"], "number": v["number"], "title": v.get("title"), "url": v.get("url"), "state": v.get("state"),
               "merged": v.get("merged"), "draft": v.get("draft"), "updatedAt": v.get("updatedAt")} for k, v in known.items()}
    for r, numbers in by_repo.items():
        owner, name = r.split("/")
        fields = " ".join(
            f'p{n}: pullRequest(number: {n}) {{ number title url state merged isDraft updatedAt }}' for n in numbers)
        try:
            data = gh_graphql(f'query {{ repository(owner: "{owner}", name: "{name}") {{ {fields} }} }}', {})
        except GhError as e:
            log(f"  warning: could not read PRs from {r}: {e}")
            continue
        for n in numbers:
            p = (data.get("repository") or {}).get(f"p{n}")
            if p:
                out[f"{r}#{n}"] = {"repo": r, "number": n, "title": p["title"], "url": p["url"], "state": p["state"],
                                   "merged": p["merged"], "draft": p["isDraft"], "updatedAt": p["updatedAt"]}
    log(f"  external PRs: {len(out)}")
    return out
