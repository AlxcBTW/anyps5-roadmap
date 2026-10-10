#!/usr/bin/env python3
"""Technical roadmap / blocker map generator for AnyPS5 (community prototype).

Collects upstream issues and PRs through `gh api`, merges them with the curated
facts in data/blockers.json, measures HLE / RDNA ISA / PM4 coverage and writes
site/roadmap.json, site/ROADMAP.md, site/index.html, site/llms.txt and
site/AGENTS.md.

Standard library only. Needs the GitHub CLI (`gh`) on PATH; in Actions it reads
GH_TOKEN / GITHUB_TOKEN from the environment.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

SCHEMA_VERSION = 1
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
CURATED = DATA / "blockers.json"
CACHE = DATA / "cache" / "raw.json"

UPSTREAM = "boykopovar/AnyPS5"
WINDOW_DAYS = 60
PROGRESS_URL = "https://boykopovar.github.io/AnyPS5/progress.json"
PM4_HEADER = "core/libs/prx/libSceAgcDriver/Execution/include/Pm4Opcodes.hpp"
PM4_SOURCE = "core/libs/prx/libSceAgcDriver/Execution/src/Pm4.cpp"
DRIVER_DIR = "core/libs/prx/libSceAgcDriver"
RAW_URL = "https://raw.githubusercontent.com/{repo}/main/{path}"

STAGES = ["Converts", "Loads", "Starts", "First draw", "Presents", "Menus", "Ingame", "Playable"]
STAGE_HELP = {
    "Converts": "The package unpacks and the relinker converts the executable.",
    "Loads": "All imports resolve and the ELF loads.",
    "Starts": "Guest code runs past startup.",
    "First draw": "The first GPU draw or dispatch executes.",
    "Presents": "Frames reach the screen (loading screens and black frames count).",
    "Menus": "A menu or title screen renders and responds.",
    "Ingame": "Gameplay is reached.",
    "Playable": "Playable from start to finish with minor issues.",
}


# --------------------------------------------------------------------------
# GitHub access through the gh CLI
# --------------------------------------------------------------------------

class GhError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _gh(args: list[str], stdin: str | None = None, attempts: int = 4) -> str:
    delay = 2.0
    for attempt in range(attempts):
        proc = subprocess.run(["gh", *args], input=stdin, capture_output=True, text=True, encoding="utf-8")
        if proc.returncode == 0:
            return proc.stdout
        err = (proc.stderr or "") + (proc.stdout or "")
        status = None
        m = re.search(r"HTTP (\d{3})", err)
        if m:
            status = int(m.group(1))
        if status in (404, 410, 422):
            raise GhError(err.strip(), status)
        transient = status in (None, 500, 502, 503, 504) or "secondary rate limit" in err.lower() or "timeout" in err.lower()
        if not transient or attempt == attempts - 1:
            raise GhError(err.strip(), status)
        time.sleep(delay)
        delay *= 2
    raise GhError("unreachable")


def gh_graphql(query: str, variables: dict) -> dict:
    out = _gh(["api", "graphql", "--input", "-"], stdin=json.dumps({"query": query, "variables": variables}))
    data = json.loads(out)
    if data.get("errors"):
        raise GhError(json.dumps(data["errors"])[:800])
    return data["data"]


def gh_rest(path: str) -> object:
    return json.loads(_gh(["api", "-H", "Accept: application/vnd.github+json", path]))


def rate_limit() -> dict:
    try:
        data = gh_rest("rate_limit")
        res = data.get("resources", {})
        return {k: {"remaining": res[k]["remaining"], "limit": res[k]["limit"]} for k in ("core", "graphql", "search") if k in res}
    except GhError:
        return {}


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


# --------------------------------------------------------------------------
# Upstream sources: progress.json, PM4 opcode table, driver sources
# --------------------------------------------------------------------------

def http_get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "anyps5-roadmap"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


class Upstream:
    """Reads upstream files from a local checkout at a fixed ref (git show)."""

    def __init__(self, checkout: Path | None, ref: str, repo: str, fetch: bool, log):
        self.checkout, self.ref, self.repo, self.log = checkout, ref, repo, log
        self.commit = None
        if checkout:
            if fetch:
                subprocess.run(["git", "-C", str(checkout), "fetch", "-q", "origin"], check=False)
            proc = subprocess.run(["git", "-C", str(checkout), "rev-parse", ref], capture_output=True, text=True)
            if proc.returncode == 0:
                self.commit = proc.stdout.strip()

    def show(self, path: str) -> str | None:
        if not self.checkout:
            return None
        proc = subprocess.run(["git", "-C", str(self.checkout), "show", f"{self.ref}:{path}"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        return proc.stdout if proc.returncode == 0 else None

    def files(self, prefix: str) -> list[str]:
        if not self.checkout:
            return []
        proc = subprocess.run(["git", "-C", str(self.checkout), "ls-tree", "-r", "--name-only", self.ref, "--", prefix],
                              capture_output=True, text=True, encoding="utf-8")
        return proc.stdout.split() if proc.returncode == 0 else []

    def grep(self, pattern: str, prefix: str) -> dict[str, int]:
        """Return {path: match count} for an extended regex under prefix at ref."""
        if not self.checkout:
            return {}
        proc = subprocess.run(["git", "-C", str(self.checkout), "grep", "-c", "-E", "-i", pattern, self.ref, "--", prefix],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = {}
        for line in proc.stdout.splitlines():
            parts = line.rsplit(":", 1)
            if len(parts) == 2 and parts[1].isdigit():
                out[parts[0].split(":", 1)[-1]] = int(parts[1])
        return out

    def raw(self, path: str) -> str | None:
        """Fetch a file raw from GitHub main; fall back to the checkout."""
        try:
            return http_get(RAW_URL.format(repo=self.repo, path=path)).decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as e:
            self.log(f"  raw fetch failed for {path}: {e}; using checkout")
            return self.show(path)


# --------------------------------------------------------------------------
# Text mining: title IDs, names, engines, stages, error signatures, links
# --------------------------------------------------------------------------

TITLE_RE = re.compile(r"\bPPSA\d{5}\b")
MD_NOISE = re.compile(r"[*_`\[\]]|\]\([^)]*\)")
NAME_TOKEN = re.compile(r"[A-Z0-9À-ɏ][\w'’&.!:+\-]*")
NAME_CONNECT = {"of", "the", "and", "&", "a", "in", "for", "to", "de", "-", "–", ":", "vs.", "x"}
NAME_LABELS = {"title", "game", "titles", "another", "also", "tested", "with", "on", "in", "and", "from", "see"}
NAME_REJECT = {
    "windows", "linux", "macos", "nvidia", "amd", "intel", "ue4", "ue5", "unity", "rtx", "gtx", "rx", "main", "the",
    "title", "game", "id", "release", "build", "ps5", "ps4", "anyps5", "fps", "log", "logs", "with", "on", "and", "or",
    "pr", "issue", "retail", "homebrew", "app", "a", "an", "it", "this", "that", "note", "update", "result", "fix", "tested",
}
NAME_REJECT_FIRST = {"unblocks", "unblock", "fixes", "fix", "blocks", "needs", "needed", "affects", "stops", "tested", "with",
                     "without", "from", "for", "after", "before", "both", "all", "same", "unreal", "unity", "runmultipleframes:"}
NAME_REJECT_ANY = re.compile(r"\b(?:RTX|GTX|GPU|CPU|Radeon|Laptop|Engine \d|NVIDIA|AMD|Vulkan)\b|PPSA\d{5}|0x[0-9a-f]", re.I)
ENGINE_RULES = [
    (re.compile(r"\bUE ?5\b|Unreal Engine 5"), "Unreal Engine 5"),
    (re.compile(r"\bUE ?4\b|Unreal Engine 4"), "Unreal Engine 4"),
    (re.compile(r"\bUE\b|\bUnreal\b"), "Unreal Engine"),
    (re.compile(r"\bUnity\b"), "Unity"),
    (re.compile(r"NativeAOT"), ".NET NativeAOT"),
    (re.compile(r"\bGameMaker\b"), "GameMaker"),
    (re.compile(r"\bGodot\b"), "Godot"),
    (re.compile(r"\bConstruct\b"), "Construct"),
    (re.compile(r"ps5-opengl"), "Mesa (OpenGL)"),
    (re.compile(r"\bDecima\b"), "Decima"),
]
OS_RULES = [
    (re.compile(r"\bWindows\b|MinGW|MSVC"), "Windows"),
    (re.compile(r"\bLinux\b|CachyOS|Fedora|Ubuntu|Arch Linux|bubblewrap|RADV"), "Linux"),
    (re.compile(r"\bmacOS\b|MoltenVK"), "macOS"),
]
GPU_RULES = [
    (re.compile(r"\bRTX\b|\bGTX\b|NVIDIA|GeForce"), "NVIDIA"),
    (re.compile(r"\bRX ?\d{3,4}\b|Radeon|RADV|\bAMD\b(?! RDNA)|gfx1[01]\d\d\b"), "AMD"),
    (re.compile(r"Intel Arc|\bArc\b|\bIris\b|UHD Graphics|HD Graphics|\bIntel\b"), "Intel"),
    (re.compile(r"lavapipe|llvmpipe"), "software"),
]
NEGATION = re.compile(r"\b(?:never|not|no|without|cannot|can't|doesn't|does not|didn't|fails? to|before|instead of|until)\b[^.;]{0,30}$", re.I)
STOP_WORDS = re.compile(r"\b(?:stops?|stopped|stuck|hangs?|halts?|freezes|crash(?:es|ed)?|aborts?|dies|faults?|segfaults?|fails?|failed|same (?:error|stop|crash|message)|refused|throws?)\b", re.I)
REPORT_FIELD = re.compile(r"\s*[-*]?\s*(?:title id|title|game|titles? tested|tested title)\s*:", re.I)
STAGE_RULES = [
    ("Playable", re.compile(r"(?<!un)(?<!not )\bplayable\b", re.I)),
    ("Ingame", re.compile(r"\bin-game\b|\bingame\b|\bgameplay\b|\bstory mode\b|\b(?:first|tutorial) level\b|\bminutes of play\b", re.I)),
    ("Menus", re.compile(r"\b(?:main|title|start|pause|home) (?:menu|screen)\b|\bmenus?\b", re.I)),
    ("Presents", re.compile(r"\bloading screen\b|\bblack (?:screen|frames?)\b|\bintro (?:video|movie)\b|\bsplash\b|\brenders?\b|\bdraws? (?:its|the) (?:full |complete )?(?:ui|screen|frame)|\b\d+ ?fps\b|\bpresents\b", re.I)),
    ("First draw", re.compile(r"\bfirst (?:draw|frame|presentation)\b", re.I)),
    ("Starts", re.compile(r"\bboots?\b|\bstarts up\b", re.I)),
]
PATCHED_BUILD = re.compile(r"\bwith (?:#|PR|AlxcBTW/|the fix|this|these|both|all)|\bplus #|\+ ?#\d|\bon #\d+'s branch|\bthis branch\b|\blocal(?:ly)?\b|\bfork\b|\bhack\b", re.I)

SIG_START = re.compile(
    r"FAIL: unresolved ELF import|Failed to load module:|undefined symbol:|what\(\):|presentation failed:|AGC graphics:|ShaderRecompiler::Recompile:")
SIG_WRAPPER = re.compile(
    r"^(?:what\(\):|presentation failed:|terminate called[^:]*:|(?:compute|pixel|vertex|geometry|hull|domain|mesh|task|export) shader 0x[0-9a-fA-F]+:|"
    r"AGC graphics:|AGC driver:|ShaderRecompiler::Recompile:|shader info collection failed:)\s*", re.I)
SIG_KEEP_PREFIX = ("AGC graphics:", "AGC driver:", "ShaderRecompiler::Recompile:")
IMPORT_RE = re.compile(
    r"FAIL: unresolved ELF import\s+`?(?P<nid>[A-Za-z0-9+\-_]{11})`?(?:\s*\(`?(?P<sym>[\w:]+)`?\))?\s+from\s+`?(?P<lib>[\w.\-]+?)(?:\.s?prx)?`?"
    r"(?=[`'\"\s)|.,;]|$)(?:[`'\"]*\s*\(`(?P<sym2>[\w:]+)`\))?")
MODULE_RE = re.compile(r"Failed to load module:\s*\S*?[\\/]?(?P<lib>[\w.\-]+\.s?prx)")
UNDEF_RE = re.compile(r"undefined symbol:\s*`?(?P<nid>[A-Za-z0-9+\-_]{11})")
QUOTED_RE = re.compile(r"[\"“]([^\"”]{20,160})[\"”]")
SIG_CUT = re.compile(r"`|\s\|\s|\|$|[\"”]|\s\(#\d|\s—\s|\s–\s")

ISSUE_URL_RE = re.compile(r"https://github\.com/(?P<repo>[\w.\-]+/[\w.\-]+)/(?:issues|pull)/(?P<num>\d+)(?![\w/])")
SHORT_REF_RE = re.compile(r"(?<![\w/#&])(?:(?P<repo>[\w.\-]+/[\w.\-]+))?#(?P<num>\d{1,6})\b")
CLOSING_RE = re.compile(r"(?i)\b(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?)\b:?\s+(?P<refs>(?:(?:[\w.\-]+/[\w.\-]+)?#\d+|https://github\.com/[\w.\-]+/[\w.\-]+/issues/\d+)(?:\s*(?:,|and|&)\s*(?:(?:[\w.\-]+/[\w.\-]+)?#\d+|https://github\.com/[\w.\-]+/[\w.\-]+/issues/\d+))*)")
REGISTER_RE = re.compile(r"\b(?:SPI|PA|CB|DB|VGT|SQ|GE|COMPUTE|SX|TA|IA|GRBM|RLC)_[A-Z0-9_]{3,}\b")

TRACKER_TITLES = 7   # an issue naming this many titles is treated as a tracker
LINE_TITLE_LIMIT = 2  # a stop line naming more titles than this is a table summary


def strip_md(text: str) -> str:
    text = re.sub(r"\]\([^)]*\)", "", text)
    return re.sub(r"[*_`\[\]>]", "", text)


def name_before(line: str, pos: int) -> str | None:
    tokens = strip_md(line[:pos]).replace("(", " ( ").split()
    if tokens and tokens[-1] == "(":
        tokens.pop()
    out: list[str] = []
    for tok in reversed(tokens):
        if tok == "(" or tok.endswith(",") or tok.endswith(";") or tok.endswith("."):
            break
        low = tok.lower().rstrip(":")
        if tok.endswith(":") and low in NAME_LABELS | {"title id", "id"}:
            break
        if NAME_TOKEN.fullmatch(tok) or tok.lower() in NAME_CONNECT:
            out.append(tok)
            if len(out) >= 7:
                break
        else:
            break
    while out and (out[-1].lower() in NAME_CONNECT or out[-1].lower().rstrip(":") in NAME_LABELS):
        out.pop()
    while out and out[0].lower() in NAME_CONNECT:
        out.pop(0)
    return clean_name(" ".join(reversed(out)))


def name_after(line: str, end: int) -> str | None:
    rest = strip_md(line[end:])
    m = re.match(r"\s*\(([^,;)]{2,48})[,;)]", rest)
    if m:
        cand = m.group(1).strip()
        if not re.match(r"v?\d+\.\d+|0x|UE\d|\d+ ?(?:fps|s)\b", cand, re.I):
            return clean_name(cand)
        return None
    tokens = rest.split()
    out = []
    for tok in tokens:
        bare = tok.rstrip(",.;:)")
        if NAME_TOKEN.fullmatch(bare) or (out and bare.lower() in NAME_CONNECT):
            out.append(bare)
            if bare != tok or len(out) >= 6:
                break
        else:
            break
    while out and out[-1].lower() in NAME_CONNECT:
        out.pop()
    return clean_name(" ".join(out))


def clean_name(name: str | None) -> str | None:
    if not name:
        return None
    name = name.strip(" :-–—,()")
    words = name.split()
    if not words or not re.search(r"[A-Za-z]{2}", name) or len(name) < 3 or len(name) > 60:
        return None
    if all(w.lower().rstrip(":") in NAME_REJECT for w in words):
        return None
    if words[0].lower() in NAME_REJECT_FIRST or NAME_REJECT_ANY.search(name) or not re.match(r"[A-Z0-9À-ɏ]", name):
        return None
    if words[0].lower() in NAME_REJECT and len(words) == 1:
        return None
    if re.fullmatch(r"v?\d[\d.]*", words[0]) and len(words) == 1:
        return None
    return name


def title_context(line: str, pos: int, length: int) -> str:
    """The parenthesis that encloses the title ID, or the one right after it."""
    open_ = line.rfind("(", 0, pos)
    close_before = line.rfind(")", 0, pos)
    if open_ > close_before:
        end = line.find(")", pos)
        return line[open_:end + 1 if end >= 0 else len(line)]
    m = re.match(r"\s*\*{0,2}\s*\(([^)]*)\)", line[pos + length:])
    return m.group(1) if m else ""


def classify(rules, text: str) -> str | None:
    for rx, value in rules:
        if rx.search(text):
            return value
    return None


def normalise_message(msg: str) -> str:
    msg = re.sub(r"0x[0-9a-fA-F]{4,}", "0x…", msg)
    msg = re.sub(r"(?<![\w.])\d{4,}(?![\w.])", "N", msg)
    msg = re.sub(r"\s+", " ", msg).strip()
    while msg and msg[-1] in ".,;:'\"`":
        msg = msg[:-1].rstrip()
    while msg.endswith(")") and msg.count(")") > msg.count("("):
        msg = msg[:-1].rstrip()
    if len(msg) > 150:
        msg = msg[:150].rsplit(" ", 1)[0] + " …"
    return msg


NID_SUFFIX = bytes.fromhex("518D64A635DED8C1E6B039B1C3E55230")
NID_ALPHABET = str.maketrans("/", "-")


def compute_nid(symbol: str) -> str:
    """PS4/PS5 symbol NID, as core/libs/nid/src/NidCompute.cpp computes it."""
    digest = hashlib.sha1(symbol.encode("utf-8") + NID_SUFFIX).digest()[:8][::-1]
    return base64.b64encode(digest).decode("ascii")[:11].translate(NID_ALPHABET)


def import_signature(nid: str, symbol: str | None, library: str | None) -> dict:
    """Import stops are keyed by NID, so a Linux `undefined symbol` line and a
    Windows `FAIL: unresolved ELF import` line for the same function match."""
    sig = {"family": "import", "key": f"unresolved import {nid}".lower(), "nid": nid, "symbol": symbol, "library": library}
    return name_import(sig)


def name_import(sig: dict) -> dict:
    sym, lib = sig.get("symbol"), sig.get("library")
    sig["display"] = f"unresolved ELF import {sig['nid']}{f' ({sym})' if sym else ''}{f' from {lib}' if lib else ''}"
    return sig


def signature_key(text: str | None) -> str | None:
    """Key for a curated signature string, written either as a log line or as plain text."""
    if not text:
        return None
    sig = signature_from(text)
    if sig:
        return sig["key"]
    rest = text
    while (w := SIG_WRAPPER.match(rest)):
        rest = rest[w.end():]
    return normalise_message(rest).lower() or None


def signature_from(line: str, next_line: str = "") -> dict | None:
    m = SIG_START.search(line)
    if not m:
        return None
    rest = line[m.start():]
    im = IMPORT_RE.match(rest)
    if im:
        sym = im.group("sym") or im.group("sym2")
        return import_signature(im.group("nid"), sym, im.group("lib"))
    mm = MODULE_RE.match(rest)
    if mm:
        lib = mm.group("lib")
        return {"family": "import", "key": f"missing module {lib}".lower(), "display": f"Failed to load module {lib}", "library": lib}
    um = UNDEF_RE.match(rest)
    if um:
        return import_signature(um.group("nid"), None, None)
    families, kept = [], ""
    while True:
        w = SIG_WRAPPER.match(rest)
        if not w:
            break
        tag = w.group(0).strip()
        families.append(tag.split()[0].rstrip(":").lower())
        for keep in SIG_KEEP_PREFIX:
            if tag.startswith(keep):
                kept = keep
        rest = rest[w.end():]
    if not rest.strip() and next_line:
        rest = next_line.strip()
    cut = SIG_CUT.search(rest)
    if cut:
        rest = rest[:cut.start()]
    core = normalise_message(rest)
    if len(core) < 12 or not re.search(r"[a-z]{3}", core):
        return None
    fam = "recompile" if "shaderrecompiler::recompile" in families else "agc" if "agc" in families else \
        "present" if "presentation" in families else "exception"
    return {"family": fam, "key": core.lower(), "display": (kept + " " + core).strip()}


def signatures_in(text: str) -> list[tuple[int, dict]]:
    lines = text.splitlines()
    out = []
    for idx, line in enumerate(lines):
        if SIG_START.search(line):
            sig = signature_from(line, lines[idx + 1] if idx + 1 < len(lines) else "")
            if sig:
                out.append((idx, sig))
    return out


def sig_match(a: str, b: str) -> bool:
    if not a or not b:
        return False
    short, long_ = sorted((a, b), key=len)
    return len(short) >= 24 and long_.startswith(short)


def refs_in(text: str, default_repo: str) -> list[tuple[str, int]]:
    out = []
    for m in ISSUE_URL_RE.finditer(text):
        out.append((m.group("repo"), int(m.group("num"))))
    scrubbed = ISSUE_URL_RE.sub(" ", text)
    for m in SHORT_REF_RE.finditer(scrubbed):
        out.append((m.group("repo") or default_repo, int(m.group("num"))))
    return out


def closing_refs(text: str, default_repo: str) -> list[tuple[str, int]]:
    out = []
    for m in CLOSING_RE.finditer(text or ""):
        out += refs_in(m.group("refs"), default_repo)
    return out


def stage_in(line: str, title_pos: int) -> tuple[str, str] | None:
    """Highest stage keyword in a line that is not negated; returns (stage, phrase)."""
    best = None
    for stage, rx in STAGE_RULES:
        for m in rx.finditer(line):
            before = line[max(0, m.start() - 40):m.start()]
            if NEGATION.search(before):
                continue
            if abs(m.start() - title_pos) > 220:
                continue
            idx = STAGES.index(stage)
            if STOP_WORDS.search(before) and idx > 0:
                idx -= 1
            if best is None or idx > best[0]:
                best = (idx, m.group(0))
            break
    return (STAGES[best[0]], best[1]) if best else None


# --------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------

def pr_state(state: str | None, merged: bool | None, draft: bool | None) -> str:
    if merged or state == "MERGED":
        return "merged"
    if state == "CLOSED":
        return "closed"
    if draft:
        return "draft"
    return "open" if state == "OPEN" else (state or "unknown").lower()


def key_of(repo: str, number: int) -> str:
    return f"{repo}#{number}"


def short_ref(key: str, upstream: str) -> str:
    repo, num = key.split("#")
    return f"#{num}" if repo == upstream else f"{repo.split('/')[0]}#{num}"


class Model:
    def __init__(self, raw: dict, curated: dict, repo: str, now: dt.datetime, compat_md: str | None = None,
                 progress: dict | None = None):
        self.raw, self.curated, self.repo, self.now = raw, curated, repo, now
        self.issues = {i["number"]: i for i in raw["issues"]}
        self.prs: dict[str, dict] = {}
        self.links: dict[int, dict[str, str]] = defaultdict(dict)   # issue -> {pr key: fixes|mentions}
        self.titles: dict[str, dict] = {}
        self.blockers: dict[str, dict] = {}
        self.issue_info: dict[int, dict] = {}
        self.compat_md = compat_md
        self.gaps: list[str] = []
        self.nid_names = self._nid_index(progress)
        self._index_prs()
        self._link()
        self._mine_issues()
        self._mine_prs()
        self._mine_compat()
        self._apply_curated_titles()
        self._build_blockers()
        self._build_chains()
        self._rank()

    # -- NIDs -----------------------------------------------------------------
    def _nid_index(self, progress: dict | None) -> dict[str, str]:
        """Map NIDs back to names: every identifier in issue/PR text plus the
        function names in progress.json, hashed with the NID algorithm."""
        names: set[str] = set()
        for g in ((progress or {}).get("libraries") or {}).get("groups", []):
            names.update(g.get("done_names", []))
            names.update(g.get("todo_names", []))
        ident = re.compile(r"(?<![\w+\-])[A-Za-z_][A-Za-z0-9_]{2,63}(?![\w+\-])")
        for item in self.raw["issues"] + self.raw["prs"]:
            names.update(ident.findall(item.get("title") or ""))
            names.update(ident.findall(item.get("body") or ""))
            for c in item.get("comments", []) if isinstance(item.get("comments"), list) else []:
                names.update(ident.findall(c.get("body") or ""))
        return {compute_nid(n): n for n in names}

    def resolve_sig(self, sig: dict) -> dict:
        if sig.get("family") == "import" and sig.get("nid") and not sig.get("symbol"):
            name = self.nid_names.get(sig["nid"])
            if name:
                sig["symbol"] = name
                name_import(sig)
        return sig

    # -- PRs and links ------------------------------------------------------
    def _put_pr(self, repo, number, title, url, state, merged, draft, updated, labels=None, author=None):
        key = key_of(repo, number)
        cur = self.prs.get(key, {})
        rec = {
            "key": key, "repo": repo, "number": number, "title": title or cur.get("title"),
            "url": url or cur.get("url") or f"https://github.com/{repo}/pull/{number}",
            "state": pr_state(state, merged, draft) if state else cur.get("state", "unknown"),
            "updated": updated or cur.get("updated"), "labels": labels if labels is not None else cur.get("labels", []),
            "author": author or cur.get("author"),
        }
        self.prs[key] = rec
        return rec

    def _index_prs(self):
        for p in self.raw.get("external_prs", {}).values():
            self._put_pr(p["repo"], p["number"], p.get("title"), p.get("url"), p.get("state"), p.get("merged"), p.get("draft"), p.get("updatedAt"))
        for i in self.raw["issues"]:
            for x in i["xrefs"] + i["closed_by"]:
                if x.get("kind", "pr") == "pr" and key_of(x["repo"], x["number"]) not in self.prs:
                    self._put_pr(x["repo"], x["number"], x.get("title"), x.get("url"), x.get("state"), x.get("merged"), x.get("draft"), x.get("updatedAt"))
        for p in self.raw["prs"]:
            rec = self._put_pr(self.repo, p["number"], p["title"], p["url"], p["state"], p["merged"], p["isDraft"], p["updatedAt"], p["labels"], p.get("author"))
            rec["merged_at"] = p.get("mergedAt")

    def _add_link(self, issue: int, pr_key: str, kind: str):
        if issue not in self.issues or pr_key not in self.prs:
            return
        if self.links[issue].get(pr_key) != "fixes":
            self.links[issue][pr_key] = kind

    def _link(self):
        for i in self.raw["issues"]:
            for x in i["closed_by"]:
                self._add_link(i["number"], key_of(x["repo"], x["number"]), "fixes")
            for x in i["xrefs"]:
                if x["kind"] == "pr":
                    self._add_link(i["number"], key_of(x["repo"], x["number"]), "fixes" if x.get("willClose") else "mentions")
        for p in self.raw["prs"]:
            pk = key_of(self.repo, p["number"])
            text = f"{p['title']}\n{p.get('body') or ''}"
            closing = {(r, n) for r, n in closing_refs(text, self.repo)}
            closing |= {(c["repo"], c["number"]) for c in p.get("closes", [])}
            for r, n in closing:
                if r == self.repo:
                    self._add_link(n, pk, "fixes")
            for r, n in refs_in(text, self.repo):
                if r == self.repo and n != p["number"]:
                    self._add_link(n, pk, "mentions")

    # -- titles -------------------------------------------------------------
    def title(self, tid: str) -> dict:
        if tid not in self.titles:
            self.titles[tid] = {
                "id": tid, "names": Counter(), "engines": Counter(), "kinds": Counter(),
                "evidence": [], "assoc": {}, "mentions": [], "stops": [], "curated": False,
                "name": None, "engine": None, "kind": None, "paths": None, "chain": [], "open_chain": [],
            }
        return self.titles[tid]

    def _associate(self, tid: str, issue: int, level: str, url: str, date: str):
        t = self.title(tid)
        order = ["mention", "report", "stop-line", "signature", "tracker-row", "dependency", "curated"]
        cur = t["assoc"].get(issue)
        if cur is None or order.index(level) > order.index(cur["level"]):
            t["assoc"][issue] = {"level": level, "url": url, "date": date}

    def _sources(self, item: dict, kind: str):
        number = item["number"]
        yield {"kind": kind, "number": number, "url": item["url"], "date": item["createdAt"], "author": item.get("author"),
               "text": f"{item['title']}\n{item.get('body') or ''}", "part": "body"}
        for c in item.get("comments", []) if isinstance(item.get("comments"), list) else []:
            yield {"kind": kind, "number": number, "url": c["url"], "date": c["createdAt"], "author": c.get("author"),
                   "text": c.get("body") or "", "part": "comment"}

    def _mine_text(self, src: dict, info: dict | None):
        text = src["text"]
        lines = text.splitlines()
        src_os = classify(OS_RULES, text)
        src_gpu = classify(GPU_RULES, text)
        for idx, line in enumerate(lines):
            ids = list(dict.fromkeys(TITLE_RE.findall(line)))
            sig = signature_from(line, lines[idx + 1] if idx + 1 < len(lines) else "") if SIG_START.search(line) else None
            if sig:
                self.resolve_sig(sig)
            if not ids:
                continue
            for tid in ids:
                t = self.title(tid)
                pos = line.find(tid)
                n = name_before(line, pos)
                if not n or len(n) < 3:
                    n = name_after(line, pos + len(tid))
                if not n and idx > 0 and re.match(r"\W*title id\W*:", strip_md(line), re.I):
                    # "Game: Silent Hill: The Short Message" on the line before "Title ID: PPSA10112"
                    m = re.match(r"\W*(?:game|title)\W*:\s*(.+)", strip_md(lines[idx - 1]), re.I)
                    n = clean_name(m.group(1).strip()) if m else None
                if n:
                    t["names"][n] += 1
                if len(ids) == 1:
                    # engine and kind only from the parenthesis that holds or follows the ID,
                    # e.g. "Stray (PPSA02100, UE4)" or "PPSA03001 (v01.007.000, Unreal Engine 4)"
                    ctx = title_context(line, pos, len(tid))
                    eng = classify(ENGINE_RULES, ctx)
                    if eng:
                        t["engines"][eng] += 1
                    if re.search(r"\bretail\b", ctx, re.I):
                        t["kinds"]["retail"] += 1
                    if re.search(r"homebrew|github\.com/[\w.\-]+/[\w.\-]+", ctx, re.I) or tid.startswith("PPSA99"):
                        t["kinds"]["homebrew"] += 1
                t["mentions"].append({"kind": src["kind"], "number": src["number"], "url": src["url"], "date": src["date"]})
                if len(ids) <= LINE_TITLE_LIMIT:
                    os_ = classify(OS_RULES, line) or src_os
                    gpu = classify(GPU_RULES, line) or src_gpu
                    build = ("PR #%d" % src["number"]) if src["kind"] == "pr" else ("main + patches" if PATCHED_BUILD.search(line) else "main")
                    st = stage_in(line, pos)
                    if st:
                        t["evidence"].append({"stage": st[0], "os": os_, "gpu": gpu, "build": build, "url": src["url"], "date": src["date"],
                                              "note": f"“{st[1]}”", "origin": "mined"})
                    if sig:
                        floor = "Converts" if sig["family"] == "import" else "Starts"
                        t["evidence"].append({"stage": floor, "os": os_, "gpu": gpu, "build": build, "url": src["url"], "date": src["date"],
                                              "note": "stops at: " + sig["display"], "origin": "mined"})
                        t["stops"].append({"sig": sig, "url": src["url"], "date": src["date"], "issue": src["number"] if src["kind"] == "issue" else None,
                                           "os": os_, "gpu": gpu})
                if info is None:
                    continue
                if info["tracker"]:
                    continue
                # "report": the issue is about this title (ID in the issue title, or a
                # "Title:" / "Game:" field in the body). A bare mention, e.g. a
                # measurement on some title, is kept but does not enter the chain.
                if src["part"] == "body" and (idx == 0 or REPORT_FIELD.match(strip_md(line))):
                    self._associate(tid, src["number"], "report", src["url"], src["date"])
                elif len(ids) <= LINE_TITLE_LIMIT and (sig or STOP_WORDS.search(line)):
                    self._associate(tid, src["number"], "stop-line", src["url"], src["date"])
                else:
                    self._associate(tid, src["number"], "mention", src["url"], src["date"])

    def _mine_issues(self):
        for number, issue in self.issues.items():
            texts = [issue["title"], issue.get("body") or ""] + [c["body"] for c in issue["comments"]]
            all_ids = set()
            for t in texts:
                all_ids.update(TITLE_RE.findall(t))
            head = f"{issue['title']}\n{issue.get('body') or ''}"
            sigs = [self.resolve_sig(s) for _, s in signatures_in(head)]
            for q in QUOTED_RE.findall(issue["title"]):
                core = normalise_message(q)
                if re.search(r"[a-z]{3} [a-z]{3}", core):
                    sigs.insert(0, {"family": "title", "key": core.lower(), "display": core})
            counts = Counter(s["key"] for s in sigs)
            primary = None
            if sigs:
                best = max(counts.values())
                primary = next(s for s in sigs if counts[s["key"]] == best)
                if sigs[0]["family"] == "title":
                    # prefer a full log line that the quoted title fragment belongs to
                    full = next((s for s in sigs[1:] if sig_match(s["key"], sigs[0]["key"]) or sigs[0]["key"] in s["key"]), None)
                    primary = full or sigs[0]
            later = [self.resolve_sig(s) for t in texts[2:] for _, s in signatures_in(t)]
            registers = Counter()
            for t in texts:
                for r in set(REGISTER_RE.findall(t)):
                    registers[r] += 1
            self.issue_info[number] = {
                "titles": sorted(all_ids), "tracker": len(all_ids) >= TRACKER_TITLES,
                "signature": primary, "signatures": list({s["key"]: s for s in sigs + later}.values())[:12],
                "text": "\n".join(texts), "registers": registers,
            }
            for src in self._sources(issue, "issue"):
                self._mine_text(src, self.issue_info[number])

    def _mine_prs(self):
        for p in self.raw["prs"]:
            self._mine_text({"kind": "pr", "number": p["number"], "url": p["url"], "date": p["createdAt"],
                             "author": p.get("author"), "text": f"{p['title']}\n{p.get('body') or ''}", "part": "body"}, None)

    def _mine_compat(self):
        if not self.compat_md:
            return
        header = []
        for line in self.compat_md.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if "ID" in cells and "Game" in cells:
                header = cells
                continue
            ids = TITLE_RE.findall(line)
            if not ids or not header:
                continue
            row = dict(zip(header, cells))
            t = self.title(ids[0])
            if row.get("Game"):
                t["names"][row["Game"]] += 5
            for os_name in ("Windows", "Linux", "macOS"):
                status = row.get(os_name, "")
                st = stage_in(status, 0) if status and status != "?" else None
                if st:
                    t["evidence"].append({"stage": st[0], "os": os_name, "gpu": None, "build": "main",
                                          "url": f"https://github.com/{self.repo}/blob/main/docs/user/COMPATIBILITY.md",
                                          "date": None, "note": f"COMPATIBILITY.md: {status}", "origin": "upstream"})

    def _apply_curated_titles(self):
        for ct in self.curated.get("titles", []):
            t = self.title(ct["id"])
            t["curated"] = True
            for k in ("name", "engine", "kind", "paths"):
                if ct.get(k):
                    t[k] = ct[k]
            for ev in ct.get("evidence", []):
                t["evidence"].append({**{"os": None, "gpu": None, "build": "main", "note": ""}, **ev, "origin": "curated"})
        for t in self.titles.values():
            if not t["name"] and t["names"]:
                top = t["names"].most_common()
                best = max(c for _, c in top)
                t["name"] = max((n for n, c in top if c == best), key=len)
            if not t["engine"] and t["engines"]:
                t["engine"] = t["engines"].most_common(1)[0][0]
            if not t["kind"] and t["kinds"]:
                t["kind"] = t["kinds"].most_common(1)[0][0]

    # -- blockers -----------------------------------------------------------
    def _issue_prs(self, number: int) -> list[dict]:
        out = []
        for key, kind in self.links.get(number, {}).items():
            pr = self.prs[key]
            out.append({"key": key, "ref": short_ref(key, self.repo), "url": pr["url"], "title": pr["title"],
                        "state": pr["state"], "link": kind, "updated": pr["updated"], "origin": "mined"})
        rank = {"open": 0, "draft": 1, "merged": 2, "closed": 3, "unknown": 4}
        out.sort(key=lambda p: (p["link"] != "fixes", rank.get(p["state"], 4), -(int(p["key"].split("#")[1]))))
        return out

    def _area(self, issue: dict | None, prs: list[dict], sig: dict | None) -> str | None:
        votes = Counter()
        for p in prs:
            if p["link"] == "fixes" or p["state"] == "open":
                for label in self.prs[p["key"]]["labels"]:
                    if label in ("shader", "agc", "libkernel", "relinker", "libc", "prx"):
                        votes[label] += 2 if p["link"] == "fixes" else 1
        if votes:
            return votes.most_common(1)[0][0]
        title = (issue or {}).get("title", "")
        for rx, area in [(r"^(Recompiler|Structurizer|Shader|SPIR-V|v_|s_)", "shader"), (r"^(AGC|Layered|Vulkan|NVIDIA|Intel)", "agc"),
                         (r"^Relinker", "relinker"), (r"^(libkernel|Kernel)", "libkernel"), (r"^(libc|LibcInternal)", "libc")]:
            if re.search(rx, title, re.I):
                return area
        if sig:
            if sig["family"] == "recompile":
                return "shader"
            if sig["family"] in ("agc", "present"):
                return "agc"
            if sig["family"] == "import":
                lib = (sig.get("library") or "").lower()
                sym = sig.get("symbol") or ""
                if lib.startswith("libkernel") or (not lib and re.match(r"(pthread_|sig|_umtx|sysctl|sched_|sceKernel|cpuset|_?fstat|kqueue|kevent|mmap|munmap)", sym)):
                    return "libkernel"
                if "libc" in lib or "posix" in lib or (not lib and sym and not sym.startswith("sce")):
                    return "libc"
                return "prx"
        return None

    def _build_blockers(self):
        curated_by_issue = {}
        for cb in self.curated.get("blockers", []):
            bid = str(cb["id"])
            issue = self.issues.get(cb.get("issue")) if cb.get("issue") else None
            if cb.get("issue") and not issue:
                self.gaps.append(f"curated blocker {bid}: issue #{cb['issue']} not in the fetched window")
            prs = []
            for ref in cb.get("fix_prs", []) + cb.get("related_prs", []):
                key = key_of(ref.get("repo", self.repo), int(ref["number"]))
                pr = self.prs.get(key) or self._put_pr(ref.get("repo", self.repo), int(ref["number"]), None, None, None, None, None, None)
                prs.append({"key": key, "ref": short_ref(key, self.repo), "url": pr["url"], "title": pr["title"], "state": pr["state"],
                            "link": "fixes" if ref in cb.get("fix_prs", []) else "related", "updated": pr["updated"],
                            "note": ref.get("note"), "origin": "curated"})
            mined = self._issue_prs(cb["issue"]) if issue else []
            seen = {p["key"] for p in prs}
            prs += [p for p in mined if p["key"] not in seen]
            info = self.issue_info.get(cb.get("issue"), {})
            sig = info.get("signature")
            status = cb.get("status")
            if not status:
                if issue:
                    status = "open" if issue["state"] == "OPEN" else "resolved"
                else:
                    status = "resolved" if any(p["state"] == "merged" and p["link"] == "fixes" and not p.get("note") for p in prs) else "open"
            self.blockers[bid] = {
                "id": bid, "issue": cb.get("issue"), "url": issue["url"] if issue else (prs[0]["url"] if prs else None),
                "title": cb.get("title") or (issue["title"] if issue else bid),
                "signature": cb.get("signature") or (sig["display"] if sig else None),
                "signature_key": signature_key(cb.get("signature")) or (sig["key"] if sig else None),
                "area": cb.get("area") or self._area(issue, prs, sig), "status": status,
                "prs": prs, "next": cb.get("next"), "help_wanted": cb.get("help_wanted"), "notes": cb.get("notes"),
                "owner": cb.get("owner") or (", ".join(issue.get("assignees", [])) if issue else None) or None,
                "origin": "curated", "tracker": info.get("tracker", False),
                "created": issue["createdAt"] if issue else None,
                "last_activity": max([d for d in [issue["updatedAt"] if issue else None] + [p["updated"] for p in prs] if d] or [None], key=lambda d: d or ""),
                "labels": issue["labels"] if issue else [],
            }
            if cb.get("issue"):
                curated_by_issue[cb["issue"]] = bid
        ignored = {int(x["issue"]) for x in self.curated.get("not_blockers", [])}
        self.not_blockers = {int(x["issue"]): x.get("reason", "") for x in self.curated.get("not_blockers", [])}
        for number, issue in self.issues.items():
            if number in curated_by_issue or number in ignored:
                continue
            info = self.issue_info[number]
            has_titles = any(number in t["assoc"] and t["assoc"][number]["level"] != "mention" for t in self.titles.values())
            if not (info["signature"] or has_titles):
                continue
            prs = self._issue_prs(number)
            sig = info["signature"]
            self.blockers[str(number)] = {
                "id": str(number), "issue": number, "url": issue["url"], "title": issue["title"],
                "signature": sig["display"] if sig else None, "signature_key": sig["key"] if sig else None,
                "area": self._area(issue, prs, sig), "status": "open" if issue["state"] == "OPEN" else "resolved",
                "prs": prs, "next": None, "help_wanted": None, "notes": None,
                "owner": ", ".join(issue.get("assignees", [])) or None, "origin": "mined", "tracker": info["tracker"],
                "created": issue["createdAt"],
                "last_activity": max([issue["updatedAt"]] + [p["updated"] for p in prs if p["updated"]]),
                "labels": issue["labels"],
            }
        self.issue_to_blocker = {b["issue"]: bid for bid, b in self.blockers.items() if b["issue"]}

    # -- chains -------------------------------------------------------------
    def _build_chains(self):
        deps = self.raw.get("dependencies", {})
        sig_index = [(b["signature_key"], bid) for bid, b in self.blockers.items()
                     if b["signature_key"] and b["status"] == "open" and not b["tracker"]]
        curated_chains = {ct["id"]: ct.get("blockers", []) for ct in self.curated.get("titles", [])}
        for tid, t in self.titles.items():
            steps: list[dict] = []
            seen: set[str] = set()

            def add(bid, origin, why, scope=None, at=None):
                if bid in seen or bid not in self.blockers:
                    return
                seen.add(bid)
                step = {"blocker": bid, "origin": origin, "why": why, "scope": scope}
                if at is None:
                    steps.append(step)
                else:
                    steps.insert(at, step)

            for step in curated_chains.get(tid, []):
                add(str(step["id"]), "curated", step.get("why", "curated"), step.get("scope"))
            # the latest recorded stop decides which mined blocker comes first
            latest = sorted(t["stops"], key=lambda s: s["date"] or "", reverse=True)
            for stop in latest[:1]:
                hit = next((bid for key, bid in sig_index if sig_match(key, stop["sig"]["key"]) or key == stop["sig"]["key"]), None)
                if hit:
                    add(hit, "mined", "latest recorded stop matches its signature")
                    if self.blockers[hit]["issue"]:
                        t["assoc"].setdefault(self.blockers[hit]["issue"], {"level": "signature", "url": stop["url"], "date": stop["date"]})
                elif stop["issue"] and self.issue_info.get(stop["issue"], {}).get("tracker"):
                    vid = self._virtual_blocker(stop["issue"], stop)
                    sig_index.append((self.blockers[vid]["signature_key"], vid))
                    add(vid, "mined", f"latest recorded stop, listed in tracker #{stop['issue']}")
            strong = sorted(((n, a) for n, a in t["assoc"].items() if a["level"] != "mention"),
                            key=lambda na: self.issues.get(na[0], {}).get("createdAt", ""))
            for number, a in strong:
                bid = self.issue_to_blocker.get(number)
                if not bid:
                    continue
                # GitHub-native dependencies: what blocks this issue comes first
                for dep in deps.get(str(number), []):
                    dbid = self.issue_to_blocker.get(dep["number"]) if dep.get("repo", self.repo) == self.repo else None
                    if dbid:
                        add(dbid, "github", f"#{number} is blocked by #{dep['number']} (GitHub dependency)")
                add(bid, "mined", {"report": "reported on this issue", "stop-line": "a comment names it at this stop",
                                   "signature": "stop signature matches", "tracker-row": "tracker row"}.get(a["level"], a["level"]))
            t["chain"] = steps

    def _virtual_blocker(self, number: int, stop: dict) -> str:
        """A crash site that only lives as a row in a tracker issue becomes its own
        blocker, keyed by signature, so one tracker does not swallow every title."""
        sig = stop["sig"]
        slug = sig.get("symbol") or sig.get("nid") or sig.get("library") or re.sub(r"\W+", "-", sig["key"])[:40].strip("-")
        bid = f"{number}~{slug}"
        if bid in self.blockers:
            return bid
        prs = []
        symbol = sig.get("symbol")
        if symbol and len(symbol) >= 4:
            rx = re.compile(r"(?<![\w])" + re.escape(symbol) + r"(?![\w])")
            for pr in self.prs.values():
                if pr["repo"] == self.repo and pr["title"] and rx.search(pr["title"]):
                    prs.append({"key": pr["key"], "ref": short_ref(pr["key"], self.repo), "url": pr["url"], "title": pr["title"],
                                "state": pr["state"], "link": "related", "updated": pr["updated"], "origin": "mined"})
        rank = {"open": 0, "draft": 1, "merged": 2, "closed": 3}
        prs.sort(key=lambda p: (rank.get(p["state"], 4), -(int(p["key"].split("#")[1]))))
        merged_after = any(p["state"] == "merged" and (self.prs[p["key"]].get("merged_at") or "") > (stop["date"] or "") for p in prs)
        parent = self.issues[number]
        self.blockers[bid] = {
            "id": bid, "issue": None, "parent": number, "url": stop["url"],
            "title": f"{sig['display']} (row in #{number})", "signature": sig["display"], "signature_key": sig["key"],
            "area": self._area(None, prs, sig), "status": "resolved" if merged_after or parent["state"] != "OPEN" else "open",
            "prs": prs[:6], "next": None, "help_wanted": None, "notes": f"Tracked as a row in #{number}: {parent['title']}",
            "owner": None, "origin": "mined", "tracker": False, "created": stop["date"],
            "last_activity": max([stop["date"] or ""] + [p["updated"] or "" for p in prs]) or None, "labels": [],
        }
        return bid

    @staticmethod
    def paths(t: dict) -> dict[str, list[dict]]:
        """Chains per OS/GPU path. A step with a scope applies only to the paths it names."""
        names = t.get("paths") or ["any"]
        return {p: [s for s in t["chain"] if not s.get("scope") or p in s["scope"]] for p in names}

    def best_stage(self, t: dict) -> dict | None:
        """Curated evidence wins over mined evidence; within one origin the highest stage wins."""
        if not t["evidence"]:
            return None
        pool = [e for e in t["evidence"] if e["origin"] == "curated"] or t["evidence"]
        origin_rank = {"curated": 2, "upstream": 1, "mined": 0}
        return max(pool, key=lambda e: (STAGES.index(e["stage"]), origin_rank.get(e["origin"], 0), e.get("date") or ""))

    def _rank(self):
        for b in self.blockers.values():
            b.update({"frontier": 0, "one_fix_away": 0, "total": 0, "titles": [], "frontier_titles": [], "one_fix_titles": []})
        for tid, t in self.titles.items():
            best = self.best_stage(t)
            done = best is not None and best["stage"] == "Playable"
            t["open_chain"] = [s for s in t["chain"] if self.blockers[s["blocker"]]["status"] == "open"]
            listed = set()
            for s in t["open_chain"]:
                b = self.blockers[s["blocker"]]
                if s["blocker"] not in listed:
                    b["total"] += 1
                    b["titles"].append(tid)
                    listed.add(s["blocker"])
            if done:
                continue
            front, single = set(), set()
            for scope, chain in self.paths(t).items():
                open_steps = [s["blocker"] for s in chain if self.blockers[s["blocker"]]["status"] == "open"]
                if open_steps:
                    front.add(open_steps[0])
                    if len(set(open_steps)) == 1:
                        single.add(open_steps[0])
            for bid in front:
                self.blockers[bid]["frontier"] += 1
                self.blockers[bid]["frontier_titles"].append(tid)
            for bid in single:
                self.blockers[bid]["one_fix_away"] += 1
                self.blockers[bid]["one_fix_titles"].append(tid)
        for b in self.blockers.values():
            b["score"] = 3 * b["one_fix_away"] + 2 * b["frontier"] + b["total"]

    def ranking(self) -> list[dict]:
        open_ = [b for b in self.blockers.values() if b["status"] == "open"]
        return sorted(open_, key=lambda b: (-b["score"], -b["total"], b["origin"] != "curated", -(b["issue"] or 0)))


# --------------------------------------------------------------------------
# Coverage: ISA decode, HLE libraries, PM4 packets, registers
# --------------------------------------------------------------------------

def parse_pm4_opcodes(header: str) -> list[dict]:
    return [{"opcode": int(v, 16), "name": n} for v, n in re.findall(r"\{\s*0x([0-9A-Fa-f]+)\s*,\s*\"(\w+)\"\s*\}", header)]


def parse_unsupported_reason(source: str) -> dict:
    """Classify opcodes from Pm4::UnsupportedReason(): {opcode: (status, reason)}.

    A case group that ends in `return {};` is handled; one that ends in a string
    is rejected with that reason; a group with an `if (...) return "..."` before
    `return {};` is handled conditionally. Custom NOP sub-opcodes are returned
    under keys ("custom", n).
    """
    m = re.search(r"UnsupportedReason\([^)]*\)\s*\{", source)
    if not m:
        return {}
    depth, i = 0, m.end() - 1
    for i in range(m.end() - 1, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                break
    body = source[m.end():i]
    out: dict = {}
    custom = re.search(r"if \(opcode == 0x10\)\s*\{(.*?)\n    \}", body, re.S)
    rest = body
    if custom:
        rest = body[:custom.start()] + body[custom.end():]
        for grp in re.finditer(r"((?:case [^:]+:\s*)+)(.*?)(?=case |default:|\}\s*$)", custom.group(1), re.S):
            values = [int(x, 0) for x in re.findall(r"case (0x[0-9a-fA-F]+|\d+):", grp.group(1))]
            status, reason = _classify_case(grp.group(2))
            for v in values:
                out[("custom", v)] = (status, reason)
    for grp in re.finditer(r"((?:case 0x[0-9a-fA-F]+:\s*)+)(.*?)(?=case 0x|default:)", rest, re.S):
        values = [int(x, 16) for x in re.findall(r"case 0x([0-9a-fA-F]+):", grp.group(1))]
        status, reason = _classify_case(grp.group(2))
        for v in values:
            out[v] = (status, reason)
    d = re.search(r"default:\s*return\s*\"([^\"]*)\"", rest)
    out["default"] = ("rejected", d.group(1) if d else None)
    if ("custom", 0) in out:
        out[0x10] = out[("custom", 0)]  # a plain NOP is custom sub-opcode 0
    return out


def _classify_case(code: str) -> tuple[str, str | None]:
    strings = re.findall(r"return\s*\"([^\"]*)\"", code)
    empty = re.search(r"return\s*\{\s*\}", code)
    if empty and strings:
        cond = re.search(r"if\s*\((.+?)\)\s*return", code, re.S)
        return "conditional", (f"rejected only when {cond.group(1).strip()}: " if cond else "") + strings[0]
    if empty:
        return "handled", None
    if strings:
        return "rejected", strings[0]
    return "unknown", None


CUSTOM_PM4 = {0x05: "DRAW_RESET", 0x06: "WAIT_FLIP_DONE", 0x09: "DISPATCH_RESET", 0x0b: "PUSH_MARKER", 0x0c: "POP_MARKER",
              0x14: "ACQUIRE_MEM_CUSTOM", 0x15: "WRITE_DATA_CUSTOM", 0x17: "FLIP", 0x18: "RELEASE_MEM_CUSTOM",
              0x19: "DMA_DATA_CUSTOM", 0x1a: "CONTEXT_STATE"}


NOT_REGISTER = re.compile(r"_BIT$|^SQ_(?:RSRC|SEL|BUF|IMG)_|_FMT_|_TYPE_\d")


def clip(text: str, n: int) -> str:
    """Shorten at a word boundary and mark the cut with an ellipsis."""
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0].rstrip(",;:-–—(")
    return cut + "…"


def mention_count(names: list[str], texts: dict[int, str]) -> dict[str, list[int]]:
    out = {}
    for name in names:
        rx = re.compile(r"(?<![A-Za-z0-9_])(?:IT_|PKT3_)?" + re.escape(name) + r"(?![A-Za-z0-9_])")
        out[name] = sorted(n for n, t in texts.items() if rx.search(t))
    return out


def build_coverage(model: Model, upstream: Upstream, progress: dict | None, log) -> dict:
    texts = {n: info["text"] for n, info in model.issue_info.items()}
    cov: dict = {"isa": None, "hle": None, "pm4": None, "registers": None}
    if progress:
        sh = progress.get("shaders", {})
        cov["isa"] = {"done": sh.get("done"), "total": sh.get("total"), "percent": sh.get("percent"),
                      "groups": [{"encoding": g["name"], "done": g["done"], "todo": g["todo"],
                                  "percent": round(100 * g["done"] / max(1, g["done"] + g["todo"]), 1),
                                  "todo_names": g.get("todo_names", [])} for g in sh.get("groups", [])],
                      "extra": sh.get("extra", []), "source": PROGRESS_URL}
        lib = progress.get("libraries", {})
        groups = []
        for g in lib.get("groups", []):
            todo = g.get("todo_names", [])
            asked = {}
            for name in todo:
                rx = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])")
                hits = sorted(n for n, t in texts.items() if rx.search(t))
                if hits:
                    asked[name] = hits
            groups.append({"library": g["name"], "label": g.get("label"), "done": g["done"], "todo": g["todo"],
                           "percent": round(100 * g["done"] / max(1, g["done"] + g["todo"]), 1),
                           "requested": asked, "todo_names": todo})
        groups.sort(key=lambda g: (-len(g["requested"]), -g["todo"], g["library"]))
        cov["hle"] = {"done": lib.get("done"), "total": lib.get("total"), "percent": lib.get("percent"), "groups": groups, "source": PROGRESS_URL}
    header = upstream.raw(PM4_HEADER)
    source = upstream.show(PM4_SOURCE) or (upstream.raw(PM4_SOURCE) if not upstream.checkout else None)
    if header:
        ops = parse_pm4_opcodes(header)
        reasons = parse_unsupported_reason(source or "")
        exec_files = [f for f in upstream.files(DRIVER_DIR + "/Execution/src") if f.endswith(".cpp")]
        names = [o["name"] for o in ops] + list(CUSTOM_PM4.values())
        mentions = mention_count(names, texts)
        refs = {}
        for o in ops:
            pat = r"(opcode|op) == 0x0*%x\b|case 0x0*%x:" % (o["opcode"], o["opcode"])
            hits = upstream.grep(pat, DRIVER_DIR + "/Execution/src")
            refs[o["opcode"]] = sorted(hits)
        rows = []
        for o in ops:
            status, reason = reasons.get(o["opcode"], reasons.get("default", ("unknown", None))) if reasons else ("unknown", None)
            rows.append({"opcode": o["opcode"], "hex": f"0x{o['opcode']:02X}", "name": o["name"], "kind": "type-3",
                         "status": status, "reason": reason, "source_files": refs.get(o["opcode"], []),
                         "issues": mentions.get(o["name"], [])})
        for sub, name in CUSTOM_PM4.items():
            status, reason = reasons.get(("custom", sub), ("rejected", "custom packet has no implemented contract")) if reasons else ("unknown", None)
            rows.append({"opcode": sub, "hex": f"NOP·0x{sub:02X}", "name": name, "kind": "custom", "status": status,
                         "reason": reason, "source_files": [], "issues": mentions.get(name, [])})
        counts = Counter(r["status"] for r in rows if r["kind"] == "type-3")
        cov["pm4"] = {"rows": rows, "counts": dict(counts), "total": len(ops),
                      "rule": "status from the case groups of Pm4::UnsupportedReason() in " + PM4_SOURCE +
                              "; source_files lists Execution/src files that compare `opcode == 0xNN` or use `case 0xNN:`",
                      "header": PM4_HEADER, "source": PM4_SOURCE, "classified": bool(reasons)}
    reg_counts: Counter = Counter()
    reg_issues: dict[str, list[int]] = defaultdict(list)
    for n, info in model.issue_info.items():
        for r in info["registers"]:
            reg_counts[r] += 1
            reg_issues[r].append(n)
    regs = []
    for name, count in [(n, c) for n, c in reg_counts.most_common() if not NOT_REGISTER.search(n)][:30]:
        hits = upstream.grep(r"\b%s\b" % name, DRIVER_DIR) if upstream.checkout else {}
        regs.append({"name": name, "issue_count": count, "issues": sorted(reg_issues[name]), "source_files": len(hits)})
    cov["registers"] = regs
    return cov


# --------------------------------------------------------------------------
# Focus areas and help wanted
# --------------------------------------------------------------------------

AREA_NAMES = {"shader": "Shader recompiler", "agc": "AGC driver (GPU)", "libkernel": "libkernel", "libc": "libc",
              "relinker": "Relinker", "prx": "HLE modules", None: "Unsorted"}


def focus_areas(model: Model, ranking: list[dict]) -> dict:
    by_area: dict = defaultdict(lambda: {"score": 0, "blockers": [], "titles": set(), "frontier_titles": set(), "open_prs": 0})
    for b in ranking:
        if b["score"] <= 0:
            continue
        a = by_area[b["area"]]
        a["score"] += b["score"]
        a["blockers"].append(b["id"])
        a["titles"].update(b["titles"])
        a["frontier_titles"].update(b["frontier_titles"])
        a["open_prs"] += sum(1 for p in b["prs"] if p["state"] in ("open", "draft") and p["link"] in ("fixes", "related"))
    areas = []
    for area, a in sorted(((k, v) for k, v in by_area.items() if k), key=lambda kv: -kv[1]["score"])[:5]:
        areas.append({"area": area, "name": AREA_NAMES.get(area, area), "score": a["score"], "blockers": a["blockers"][:4],
                      "blocker_count": len(a["blockers"]), "titles": len(a["titles"]), "frontier_titles": len(a["frontier_titles"]),
                      "open_fix_prs": a["open_prs"]})
    help_wanted = []
    for b in ranking:
        has_fix = any(p["state"] in ("open", "draft") and p["link"] in ("fixes", "related") for p in b["prs"])
        reason = None
        if b.get("help_wanted"):
            reason = b["help_wanted"]
        elif "help wanted" in b["labels"] or "good first issue" in b["labels"]:
            reason = "Labelled " + ", ".join(l for l in b["labels"] if l in ("help wanted", "good first issue"))
        elif b["frontier"] > 0 and not has_fix:
            reason = f"First open blocker for {b['frontier']} title{'s' if b['frontier'] != 1 else ''}; no open fix PR"
        if reason:
            help_wanted.append({"blocker": b["id"], "reason": reason})
    return {"areas": areas, "help_wanted": help_wanted[:12]}


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------

def assemble(model: Model, coverage: dict, raw: dict, upstream: Upstream, now: dt.datetime) -> dict:
    ranking = model.ranking()
    focus = focus_areas(model, ranking)
    titles = []
    for tid, t in sorted(model.titles.items()):
        best = model.best_stage(t)
        last = max(t["mentions"] + [{"url": e["url"], "date": e["date"]} for e in t["evidence"] if e.get("date")],
                   key=lambda m: m["date"] or "", default=None)
        titles.append({
            "id": tid, "name": t["name"], "engine": t["engine"], "kind": t["kind"], "curated": t["curated"],
            "best_stage": best, "evidence": sorted(t["evidence"], key=lambda e: (-STAGES.index(e["stage"]), e.get("date") or ""))[:12],
            "open_blockers": [{"id": s["blocker"], "origin": s["origin"], "why": s["why"], "scope": s.get("scope")} for s in t["open_chain"]],
            "resolved_blockers": [s["blocker"] for s in t["chain"] if model.blockers[s["blocker"]]["status"] != "open"],
            "issues": sorted({m["number"] for m in t["mentions"] if m["kind"] == "issue"}),
            "prs": sorted({m["number"] for m in t["mentions"] if m["kind"] == "pr"}),
            "last_evidence": last,
        })
    blockers = []
    for b in sorted(model.blockers.values(), key=lambda b: (b["status"] != "open", -b["score"], -(b["issue"] or 0))):
        blockers.append({k: v for k, v in b.items() if k != "signature_key"})
    rl = raw.get("rate_limit", {})
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fetched_at": raw.get("fetched_at"),
        "upstream": {"repo": model.repo, "ref": upstream.ref, "commit": upstream.commit},
        "window": {"days": WINDOW_DAYS, "since": raw.get("cutoff")},
        "stages": [{"name": s, "rank": i, "meaning": STAGE_HELP[s]} for i, s in enumerate(STAGES)],
        "scoring": {"formula": "3*one_fix_away + 2*frontier + total",
                    "frontier": "titles for which this is the earliest open blocker on at least one OS/GPU path",
                    "one_fix_away": "titles for which this is the only open blocker on at least one path",
                    "total": "titles that list this blocker anywhere in their open chain",
                    "excluded": "titles whose best stage is Playable count only towards total"},
        "stats": {
            "issues_scanned": len(raw["issues"]), "issues_open": sum(1 for i in raw["issues"] if i["state"] == "OPEN"),
            "prs_scanned": len(raw["prs"]), "titles": len(titles),
            "titles_with_open_blockers": sum(1 for t in titles if t["open_blockers"]),
            "titles_with_stage": sum(1 for t in titles if t["best_stage"]),
            "blockers_open": sum(1 for b in blockers if b["status"] == "open"),
            "blockers_ranked": sum(1 for b in blockers if b["status"] == "open" and b["score"] > 0),
            "blockers_curated": sum(1 for b in blockers if b["origin"] == "curated"),
            "rate_limit": rl,
        },
        "ranking": [b["id"] for b in ranking],
        "blockers": blockers,
        "titles": titles,
        "coverage": coverage,
        "focus": focus,
        "not_blockers": [{"issue": n, "reason": r} for n, r in sorted(model.not_blockers.items())],
        "gaps": model.gaps + KNOWN_GAPS,
        "sources": {
            "issues_and_prs": f"https://github.com/{model.repo} via gh api graphql (open + closed in the last {WINDOW_DAYS} days)",
            "dependencies": f"/repos/{model.repo}/issues/{{n}}/dependencies/blocked_by",
            "curated": "data/blockers.json", "progress": PROGRESS_URL,
            "pm4": f"{PM4_HEADER} (raw, main) + {PM4_SOURCE} at {upstream.ref}",
            "compatibility": f"https://github.com/{model.repo}/blob/main/docs/user/COMPATIBILITY.md",
        },
    }


KNOWN_GAPS = [
    "Title names, engines and stages are mined with keyword rules per line; negation and context are handled only roughly.",
    "Mined chain order is a heuristic: the latest recorded stop first, then issues by creation date.",
    "PR comments and review threads are not read; only PR titles and bodies are.",
    "Titles without a PPSA ID (some homebrew) appear only when curated.",
    "Discord reports are invisible unless someone copies them into GitHub or the curated file.",
    "Signatures are matched by prefix after hex addresses and long numbers are masked; reworded messages split into separate keys.",
    "PM4 status reads Pm4::UnsupportedReason(); a packet can pass that check and still be emulated partially.",
]


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def fmt_date(iso: str | None) -> str:
    return iso[:10] if iso else "—"


AREA_LABEL = {"shader": "shader", "agc": "agc", "libkernel": "libkernel", "libc": "libc", "relinker": "relinker", "prx": "prx"}
PR_CHIP = {"merged": ("ok", "merged"), "open": ("active", "open"), "draft": ("idle", "draft"),
           "closed": ("idle", "closed"), "unknown": ("idle", "unknown")}
PM4_CHIP = {"handled": ("ok", "handled"), "conditional": ("active", "conditional"), "rejected": ("bad", "rejected"),
            "unknown": ("idle", "not classified")}

CSS = """
:root {
  color-scheme: light dark;
  --bg: oklch(0.985 0.003 250);
  --surface: oklch(1 0 0);
  --surface-sunken: oklch(0.965 0.005 250);
  --border: oklch(0.89 0.008 250);
  --border-strong: oklch(0.80 0.01 250);
  --text: oklch(0.24 0.015 255);
  --text-muted: oklch(0.47 0.015 255);
  --link: oklch(0.48 0.135 255);
  --focus: oklch(0.55 0.18 255);
  --ok-fg: oklch(0.42 0.11 150); --ok-bg: oklch(0.95 0.045 150); --ok-border: oklch(0.80 0.09 150);
  --active-fg: oklch(0.45 0.09 65); --active-bg: oklch(0.96 0.04 85); --active-border: oklch(0.82 0.08 75);
  --bad-fg: oklch(0.47 0.13 25); --bad-bg: oklch(0.95 0.022 22); --bad-border: oklch(0.82 0.07 25);
  --idle-fg: oklch(0.42 0.012 255); --idle-bg: oklch(0.955 0.005 255); --idle-border: oklch(0.85 0.008 255);
  --pip-on: oklch(0.35 0.02 255); --pip-off: oklch(0.86 0.008 255);
  --bar: oklch(0.55 0.12 150); --bar-track: oklch(0.92 0.006 250);
  --mono: ui-monospace, "Cascadia Mono", "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
  --sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: oklch(0.17 0.008 255);
    --surface: oklch(0.20 0.01 255);
    --surface-sunken: oklch(0.235 0.012 255);
    --border: oklch(0.32 0.012 255);
    --border-strong: oklch(0.42 0.012 255);
    --text: oklch(0.93 0.005 255);
    --text-muted: oklch(0.74 0.012 255);
    --link: oklch(0.78 0.10 255);
    --focus: oklch(0.75 0.11 255);
    --ok-fg: oklch(0.84 0.12 150); --ok-bg: oklch(0.28 0.05 150); --ok-border: oklch(0.42 0.08 150);
    --active-fg: oklch(0.86 0.11 80); --active-bg: oklch(0.29 0.05 75); --active-border: oklch(0.45 0.08 75);
    --bad-fg: oklch(0.83 0.09 25); --bad-bg: oklch(0.28 0.04 25); --bad-border: oklch(0.45 0.08 25);
    --idle-fg: oklch(0.82 0.01 255); --idle-bg: oklch(0.27 0.01 255); --idle-border: oklch(0.40 0.012 255);
    --pip-on: oklch(0.88 0.01 255); --pip-off: oklch(0.38 0.012 255);
    --bar: oklch(0.72 0.13 150); --bar-track: oklch(0.30 0.01 255);
  }
}
*, *::before, *::after { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font: 400 0.875rem/1.5 var(--sans);
  -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;
}
code, .mono { font-family: var(--mono); font-size: 0.92em; }
a { color: var(--link); text-decoration-line: underline; text-decoration-thickness: from-font;
    text-underline-offset: 2px; text-decoration-color: color-mix(in oklch, currentColor 40%, transparent); }
@media (hover: hover) { a:hover { text-decoration-color: currentColor; } }
:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; border-radius: 2px; }
.skip { position: absolute; inset-inline-start: 16px; top: -48px; padding: 8px 12px; background: var(--surface);
        border: 1px solid var(--border-strong); border-radius: 6px; z-index: 10; }
.skip:focus { top: 8px; }
.wrap { max-width: 92rem; margin-inline: auto; padding-inline: 16px; }
@media (min-width: 48rem) { .wrap { padding-inline: 24px; } }
h1, h2, h3 { color: var(--text); text-wrap: balance; margin: 0; }
h1 { font-size: 1.625rem; line-height: 1.15; font-weight: 650; letter-spacing: -0.012em; }
h2 { font-size: 1.25rem; line-height: 1.2; font-weight: 620; letter-spacing: -0.006em; }
h3 { font-size: 0.9375rem; line-height: 1.3; font-weight: 620; }
p { margin: 0; max-width: 78ch; text-wrap: pretty; }
.muted { color: var(--text-muted); }

header.site { border-bottom: 1px solid var(--border); background: var(--surface); }
header.site .wrap { padding-block: 24px 16px; display: grid; gap: 12px; }
.title-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; }
.lede { color: var(--text-muted); font-size: 0.9375rem; }
.facts { display: flex; flex-wrap: wrap; gap: 8px 28px; margin: 4px 0 0; }
.facts div { display: grid; gap: 0; }
.facts dt { font-size: 0.75rem; color: var(--text-muted); }
.facts dd { margin: 0; font-weight: 600; font-variant-numeric: tabular-nums; }
nav.sections ul { list-style: none; margin: 4px 0 0; padding: 0; display: flex; flex-wrap: wrap; gap: 4px 20px; }
nav.sections a { display: inline-block; padding-block: 4px; font-weight: 500; }

main { padding-block: 8px 64px; }
section { padding-top: 40px; scroll-margin-top: 16px; }
.section-head { display: grid; gap: 6px; margin-bottom: 12px; }
.section-head p { color: var(--text-muted); }
.sub { margin-top: 28px; }
.sub > h3 { margin-bottom: 8px; }
.sub > p { margin-bottom: 8px; color: var(--text-muted); }

.table-scroll { overflow: auto; max-height: min(80vh, 60rem); border: 1px solid var(--border); border-radius: 8px;
                background: var(--surface); overscroll-behavior-x: contain; }
.table-scroll.short { max-height: none; }
.scroll-hint { display: none; font-size: 0.75rem; color: var(--text-muted); margin: 0 0 6px; }
@media (max-width: 60rem) { .scroll-hint { display: block; } }
table.data { border-collapse: separate; border-spacing: 0; width: 100%; font-size: 0.8125rem; font-variant-numeric: tabular-nums; }
.data th, .data td { padding: 7px 10px; border-bottom: 1px solid var(--border); text-align: start; vertical-align: top; }
.data thead th { position: sticky; top: 0; z-index: 1; background: var(--surface-sunken); color: var(--text-muted);
                 font-size: 0.75rem; font-weight: 600; line-height: 1.3; border-bottom: 0;
                 box-shadow: inset 0 -1px 0 var(--border-strong); vertical-align: bottom; }
.data tbody tr:last-child > * { border-bottom: 0; }
.data tbody th { font-weight: 400; }
.data .num { text-align: end; white-space: nowrap; }
.data thead th.num { text-align: end; }
.data .strong { font-weight: 650; color: var(--text); }
.data .nowrap { white-space: nowrap; }
.data ul, .data ol { margin: 0; padding: 0; list-style: none; display: grid; gap: 3px; }
.data ol.chain { counter-reset: step; }
.data ol.chain li { counter-increment: step; display: flex; gap: 6px; align-items: baseline; }
.data ol.chain li::before { content: counter(step); color: var(--text-muted); font-size: 0.6875rem; min-width: 1ch; }
.b-cell { min-width: 17rem; max-width: 30rem; }
.b-title { display: block; color: var(--text); font-weight: 550; overflow-wrap: anywhere; }
.b-meta { display: flex; flex-wrap: wrap; gap: 4px 8px; margin-top: 3px; color: var(--text-muted); font-size: 0.75rem; }
.b-next { margin-top: 4px; font-size: 0.75rem; color: var(--text-muted); max-width: 60ch; }
.sig { min-width: 14rem; max-width: 24rem; }
.sig code { font-size: 0.75rem; overflow-wrap: anywhere; color: var(--text); }
.prs { min-width: 11rem; }
.prs li { display: flex; flex-wrap: wrap; align-items: baseline; gap: 2px 6px; }
.title-name { color: var(--text); font-weight: 550; }
.title-sub { color: var(--text-muted); font-size: 0.75rem; }
.ev { font-size: 0.75rem; color: var(--text-muted); margin-top: 2px; max-width: 40ch; }

.chip { display: inline-flex; align-items: center; padding: 0 6px; border-radius: 999px; border: 1px solid var(--idle-border);
        background: var(--idle-bg); color: var(--idle-fg); font-size: 0.6875rem; line-height: 1.125rem; font-weight: 550;
        white-space: nowrap; letter-spacing: 0.01em; }
.chip.ok { color: var(--ok-fg); background: var(--ok-bg); border-color: var(--ok-border); }
.chip.active { color: var(--active-fg); background: var(--active-bg); border-color: var(--active-border); }
.chip.bad { color: var(--bad-fg); background: var(--bad-bg); border-color: var(--bad-border); }
.chip.plain { background: transparent; }

.stage { display: inline-flex; align-items: center; gap: 8px; white-space: nowrap; }
.pips { display: inline-grid; grid-auto-flow: column; gap: 2px; }
.pips i { display: block; width: 5px; height: 11px; border-radius: 1.5px; background: var(--pip-off); }
.pips i.on { background: var(--pip-on); }
.stage-name { font-weight: 600; color: var(--text); }
.bar { display: inline-block; vertical-align: middle; width: 6rem; height: 6px; border-radius: 3px; background: var(--bar-track); overflow: hidden; }
.bar > span { display: block; height: 100%; background: var(--bar); border-radius: 3px; }
@media (forced-colors: active) {
  .pips i { background: GrayText; } .pips i.on { background: CanvasText; }
  .bar { border: 1px solid CanvasText; } .bar > span { background: CanvasText; }
}

.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); gap: 12px; margin-bottom: 8px; }
.stat { border: 1px solid var(--border); border-radius: 8px; background: var(--surface); padding: 12px 14px; display: grid; gap: 4px; }
.stat .label { font-size: 0.75rem; color: var(--text-muted); }
.stat .value { font-size: 1.25rem; font-weight: 650; font-variant-numeric: tabular-nums; }
.stat .value small { font-size: 0.8125rem; font-weight: 500; color: var(--text-muted); }

.areas { display: grid; grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr)); gap: 12px; }
.area { border: 1px solid var(--border); border-radius: 8px; background: var(--surface); padding: 14px 16px; display: grid; gap: 8px; align-content: start; }
.area-head { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
.area-head .score { color: var(--text-muted); font-size: 0.75rem; font-variant-numeric: tabular-nums; white-space: nowrap; }
.area p { color: var(--text-muted); font-size: 0.8125rem; }
.area ol { margin: 0; padding-inline-start: 18px; display: grid; gap: 4px; font-size: 0.8125rem; }
.help { margin: 0; padding: 0; list-style: none; display: grid; gap: 8px; }
.help li { display: grid; gap: 2px; padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); }
.help li > * { min-width: 0; overflow-wrap: anywhere; }
.area > * { min-width: 0; overflow-wrap: anywhere; }
.help .why { color: var(--text-muted); font-size: 0.8125rem; }

details { margin-top: 12px; }
details > summary { cursor: pointer; color: var(--text); font-weight: 550; padding-block: 4px; width: fit-content; }
details[open] > summary { margin-bottom: 8px; }
.prose { display: grid; gap: 10px; }
.prose ul { margin: 0; padding-inline-start: 20px; display: grid; gap: 4px; max-width: 78ch; }
.prose dl { margin: 0; display: grid; grid-template-columns: max-content 1fr; gap: 4px 16px; max-width: 78ch; }
.prose dt { font-weight: 600; }
.prose dd { margin: 0; color: var(--text-muted); }
.disclaimer { border: 1px solid var(--active-border); background: var(--active-bg); color: var(--text);
              border-radius: 8px; padding: 12px 14px; max-width: 78ch; }
footer { border-top: 1px solid var(--border); padding-block: 16px 32px; color: var(--text-muted); font-size: 0.8125rem; }
"""


def chip(text: str, kind: str = "", title: str | None = None) -> str:
    t = f' title="{esc(title)}"' if title else ""
    return f'<span class="chip {kind}"{t}>{esc(text)}</span>'


def pips(stage: str | None) -> str:
    n = STAGES.index(stage) + 1 if stage in STAGES else 0
    cells = "".join('<i class="on"></i>' if i < n else "<i></i>" for i in range(len(STAGES)))
    return f'<span class="pips" aria-hidden="true">{cells}</span>'


def pr_item(p: dict) -> str:
    kind, label = PR_CHIP.get(p["state"], ("idle", p["state"]))
    role = {"fixes": "fix", "related": "related", "mentions": "mentions"}.get(p.get("link"), "")
    tip = (p.get("title") or "") + (f" — {p['note']}" if p.get("note") else "")
    return (f'<li><a href="{esc(p["url"])}" title="{esc(tip)}">{esc(p["ref"])}</a>{chip(label, kind)}'
            f'<span class="muted">{esc(role)}</span></li>')


def blocker_link(b: dict, upstream: str) -> str:
    if b.get("issue"):
        return f'<a href="{esc(b["url"])}">#{b["issue"]}</a>'
    if b.get("parent"):
        return f'<a href="{esc(b["url"])}">row in #{b["parent"]}</a>'
    label = f'PR #{b["id"][3:]}' if re.fullmatch(r"pr-\d+", b["id"]) else b["id"]
    return f'<a href="{esc(b["url"])}">{esc(label)}</a>' if b.get("url") else esc(label)


def title_label(t: dict | None, tid: str) -> str:
    return (t or {}).get("name") or tid


def render_html(doc: dict) -> str:
    repo = doc["upstream"]["repo"]
    B = {b["id"]: b for b in doc["blockers"]}
    T = {t["id"]: t for t in doc["titles"]}
    s = doc["stats"]
    commit = doc["upstream"].get("commit")
    gen = doc["generated_at"].replace("T", " ").replace("Z", " UTC")
    out: list[str] = []
    w = out.append

    w('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
      '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
      '<title>AnyPS5 blocker map</title>\n'
      '<meta name="description" content="Generated technical roadmap for the AnyPS5 PS5 emulator: open blockers ranked by the titles a fix would move, title stages, and HLE, ISA and PM4 coverage. Community prototype.">\n'
      '<meta name="color-scheme" content="light dark">\n'
      '<link rel="alternate" type="application/json" href="roadmap.json" title="roadmap.json">\n'
      '<link rel="alternate" type="text/markdown" href="ROADMAP.md" title="ROADMAP.md">\n'
      f'<style>{CSS}</style>\n</head>\n<body>\n'
      '<a class="skip" href="#main">Skip to content</a>\n')

    # header
    w('<header class="site"><div class="wrap">')
    w(f'<div class="title-row"><h1>AnyPS5 blocker map</h1>{chip("Community prototype", "active")}</div>')
    w('<p class="lede">Open issues that stop PS5 titles from reaching their next stage, ranked by how many titles '
      'a fix would move. Generated from public GitHub data; not an official AnyPS5 page.</p>')
    commit_html = (f'<a href="https://github.com/{esc(repo)}/commit/{esc(commit)}"><code>{esc(commit[:8])}</code></a>' if commit else "—")
    facts = [("Generated", f'<time datetime="{esc(doc["generated_at"])}">{esc(gen)}</time>'),
             ("Upstream main", commit_html),
             ("Issues read", f'{s["issues_scanned"]:,}'), ("PRs read", f'{s["prs_scanned"]:,}'),
             ("Titles", f'{s["titles"]:,}'), ("Open blockers", f'{s["blockers_open"]:,}'),
             ("Curated entries", f'{s["blockers_curated"]:,}')]
    w('<dl class="facts">' + "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in facts) + "</dl>")
    w('<nav class="sections" aria-label="Sections"><ul>'
      '<li><a href="#ranking">Blocker ranking</a></li><li><a href="#titles">Titles</a></li>'
      '<li><a href="#coverage">Coverage</a></li><li><a href="#focus">Focus areas</a></li>'
      '<li><a href="#about">About this data</a></li></ul></nav>')
    w("</div></header>\n<main id=\"main\" class=\"wrap\">")

    # (1) ranking
    ranked = [B[i] for i in doc["ranking"] if B[i]["score"] > 0]
    unranked = [B[i] for i in doc["ranking"] if B[i]["score"] == 0]
    w('<section id="ranking" aria-labelledby="ranking-h"><div class="section-head">'
      '<h2 id="ranking-h">Blocker ranking</h2>'
      f'<p>{len(ranked)} open blockers stop at least one title. Score = 3 × one fix away + 2 × frontier + total. '
      '<b>Frontier</b>: titles for which this is the first open blocker. <b>One fix away</b>: titles for which it is the only one. '
      '<b>Total</b>: titles that list it anywhere. Titles already playable count only toward the total.</p></div>')
    w('<p class="scroll-hint">Scroll the table sideways for more columns.</p>')
    w('<div class="table-scroll" role="region" aria-labelledby="ranking-h" tabindex="0"><table class="data">'
      '<thead><tr><th scope="col" class="num">#</th><th scope="col">Blocker</th>'
      '<th scope="col" class="num">Frontier</th><th scope="col" class="num">One fix away</th>'
      '<th scope="col" class="num">Total</th><th scope="col" class="num">Score</th>'
      '<th scope="col">Signature</th><th scope="col">Area</th><th scope="col">PRs</th>'
      '<th scope="col">Last activity</th></tr></thead><tbody>')
    for rank, b in enumerate(ranked, 1):
        titles = b["titles"]
        tl = ", ".join(f'<a href="#t-{esc(t)}">{esc(title_label(T.get(t), t))}</a>' for t in titles[:4])
        more = f' <span class="muted">+{len(titles) - 4} more</span>' if len(titles) > 4 else ""
        meta = [chip(b["origin"], "plain", "Curated in data/blockers.json" if b["origin"] == "curated" else "Mined from issue text")]
        if b.get("tracker"):
            meta.append(chip("tracker", "plain", "This issue tracks many titles"))
        meta.append(f"<span>Blocks {tl}{more}</span>")
        nxt = f'<div class="b-next">Next: {esc(b["next"])}</div>' if b.get("next") else ""
        prs = b["prs"][:5]
        pr_html = ("<ul>" + "".join(pr_item(p) for p in prs) + "</ul>" +
                   (f'<span class="muted">+{len(b["prs"]) - 5} more</span>' if len(b["prs"]) > 5 else "")) if prs else '<span class="muted">none</span>'
        sig = f'<code>{esc(b["signature"])}</code>' if b.get("signature") else '<span class="muted">—</span>'
        w(f'<tr id="b-{esc(b["id"])}"><td class="num muted">{rank}</td>'
          f'<th scope="row" class="b-cell">{blocker_link(b, repo)} <span class="b-title">{esc(b["title"])}</span>'
          f'<div class="b-meta">{"".join(meta)}</div>{nxt}</th>'
          f'<td class="num">{b["frontier"]}</td><td class="num">{b["one_fix_away"]}</td><td class="num">{b["total"]}</td>'
          f'<td class="num strong">{b["score"]}</td><td class="sig">{sig}</td>'
          f'<td class="nowrap">{esc(AREA_LABEL.get(b["area"], "—") if b["area"] else "—")}</td>'
          f'<td class="prs">{pr_html}</td><td class="nowrap">{esc(fmt_date(b.get("last_activity")))}</td></tr>')
    w("</tbody></table></div>")
    if unranked:
        w(f'<details><summary>Open crash sites with no title attached ({len(unranked)})</summary>'
          '<div class="table-scroll" role="region" aria-label="Open crash sites with no title attached" tabindex="0">'
          '<table class="data"><thead><tr><th scope="col">Issue</th><th scope="col">Signature</th><th scope="col">Area</th>'
          '<th scope="col">PRs</th><th scope="col">Last activity</th></tr></thead><tbody>')
        for b in unranked:
            sig = f'<code>{esc(b["signature"])}</code>' if b.get("signature") else '<span class="muted">—</span>'
            pr_html = "<ul>" + "".join(pr_item(p) for p in b["prs"][:3]) + "</ul>" if b["prs"] else '<span class="muted">none</span>'
            w(f'<tr id="b-{esc(b["id"])}"><th scope="row" class="b-cell">{blocker_link(b, repo)} <span class="b-title">{esc(b["title"])}</span></th>'
              f'<td class="sig">{sig}</td><td class="nowrap">{esc(b["area"] or "—")}</td><td class="prs">{pr_html}</td>'
              f'<td class="nowrap">{esc(fmt_date(b.get("last_activity")))}</td></tr>')
        w("</tbody></table></div></details>")
    w("</section>")

    # (2) titles
    shown = [t for t in doc["titles"] if t["best_stage"] or t["open_blockers"]]
    hidden = [t for t in doc["titles"] if not (t["best_stage"] or t["open_blockers"])]
    shown.sort(key=lambda t: (-(STAGES.index(t["best_stage"]["stage"]) if t["best_stage"] else -1), len(t["open_blockers"]),
                              (t["name"] or t["id"]).lower()))
    w('<section id="titles" aria-labelledby="titles-h"><div class="section-head"><h2 id="titles-h">Titles</h2>'
      f'<p>{len(shown)} titles with a recorded stage or an open blocker, highest stage first. The stage is the best one reported, '
      'with the OS, GPU and build it was reported on. Curated evidence wins over mined evidence.</p></div>')
    w('<details><summary>Stage definitions</summary><div class="prose"><dl>' +
      "".join(f"<dt>{esc(st['name'])}</dt><dd>{esc(st['meaning'])}</dd>" for st in doc["stages"]) + "</dl></div></details>")
    w('<p class="scroll-hint">Scroll the table sideways for more columns.</p>')
    w('<div class="table-scroll" role="region" aria-labelledby="titles-h" tabindex="0"><table class="data">'
      '<thead><tr><th scope="col">ID</th><th scope="col">Title</th><th scope="col">Best stage</th>'
      '<th scope="col">Open blockers, in order</th><th scope="col">Last evidence</th></tr></thead><tbody>')
    for t in shown:
        best = t["best_stage"]
        if best:
            where = " · ".join(x for x in [best.get("os"), best.get("gpu"), best.get("build")] if x)
            src = f'<a href="{esc(best["url"])}">source</a>' if best.get("url") else "no public link"
            stage_html = (f'<span class="stage">{pips(best["stage"])}<span class="stage-name">{esc(best["stage"])}</span>'
                          f'{chip(best["origin"], "plain")}</span>'
                          f'<div class="ev">{esc(where)}{" — " if where else ""}{esc(best.get("note") or "")} ({src})</div>')
        else:
            stage_html = f'<span class="stage">{pips(None)}<span class="muted">No report</span></span>'
        chain = []
        for step in t["open_blockers"][:6]:
            b = B.get(step["id"])
            if not b:
                continue
            scope = "".join(chip(sc, "plain") for sc in (step.get("scope") or []))
            label = f"#{b['issue']}" if b.get("issue") else (f"row in #{b['parent']}" if b.get("parent") else
                                                             f"PR #{b['id'][3:]}" if re.fullmatch(r"pr-\d+", b["id"]) else b["id"])
            tip = b["title"] + (f" — {step['why']}" if step.get("why") else "")
            chain.append(f'<li><a href="#b-{esc(b["id"])}" title="{esc(tip)}">{esc(label)}</a>'
                         f'<span class="muted">{esc(clip(b["title"], 64))}</span>{scope}</li>')
        more = len(t["open_blockers"]) - 6
        chain_html = (f'<ol class="chain">{"".join(chain)}</ol>' + (f'<span class="muted">+{more} more</span>' if more > 0 else "")) \
            if chain else '<span class="muted">none recorded</span>'
        sub = " · ".join(x for x in [t.get("engine"), t.get("kind")] if x)
        name = esc(t["name"]) if t["name"] else '<span class="muted">Unnamed</span>'
        last = t.get("last_evidence")
        last_html = (f'<a href="{esc(last["url"])}">{esc(evidence_label(last["url"], repo))}</a><div class="title-sub">{esc(fmt_date(last.get("date")))}</div>'
                     if last and last.get("url") else '<span class="muted">—</span>')
        w(f'<tr id="t-{esc(t["id"])}"><td class="nowrap"><code>{esc(t["id"])}</code></td>'
          f'<th scope="row"><span class="title-name">{name}</span>'
          f'{"<div class=title-sub>" + esc(sub) + "</div>" if sub else ""}</th>'
          f'<td>{stage_html}</td><td>{chain_html}</td><td class="nowrap">{last_html}</td></tr>')
    w("</tbody></table></div>")
    if hidden:
        items = ", ".join(f'<code>{esc(t["id"])}</code>{(" " + esc(t["name"])) if t["name"] else ""}' for t in hidden)
        w(f'<details><summary>Mentioned without a stage or blocker ({len(hidden)})</summary><p>{items}</p></details>')
    w("</section>")

    # (3) coverage
    cov = doc["coverage"]
    w('<section id="coverage" aria-labelledby="coverage-h"><div class="section-head"><h2 id="coverage-h">Coverage</h2>'
      '<p>What the emulator implements, measured from upstream sources, next to how often issues ask for it.</p></div>')
    stats = []
    if cov.get("isa"):
        i = cov["isa"]
        stats.append(("RDNA ISA decode", f'{i["percent"]:.1f}%', f'{i["done"]:,} of {i["total"]:,} opcodes'))
    if cov.get("hle"):
        h = cov["hle"]
        stats.append(("HLE functions", f'{h["percent"]:.1f}%', f'{h["done"]:,} of {h["total"]:,} in {len(h["groups"])} libraries'))
    if cov.get("pm4"):
        c = cov["pm4"]["counts"]
        stats.append(("PM4 packets accepted", f'{c.get("handled", 0) + c.get("conditional", 0)} of {cov["pm4"]["total"]}',
                      f'{c.get("rejected", 0)} rejected, {c.get("conditional", 0)} conditional'))
    w('<div class="stats">' + "".join(
        f'<div class="stat"><span class="label">{esc(a)}</span><span class="value">{esc(b)}</span><span class="muted">{esc(c)}</span></div>'
        for a, b, c in stats) + "</div>")

    if cov.get("pm4"):
        p = cov["pm4"]
        w('<div class="sub"><h3 id="pm4-h">PM4 packets</h3>'
          f'<p>Status comes from <code>Pm4::UnsupportedReason()</code> in <a href="https://github.com/{esc(repo)}/blob/main/{esc(p["source"])}">{esc(p["source"].rsplit("/", 1)[-1])}</a>; '
          f'opcode names from <a href="https://github.com/{esc(repo)}/blob/main/{esc(p["header"])}">{esc(p["header"].rsplit("/", 1)[-1])}</a>. '
          'Source files count Execution/src files that compare the opcode. Issues count mentions of the packet name.</p>')
        w('<div class="table-scroll" role="region" aria-labelledby="pm4-h" tabindex="0"><table class="data">'
          '<thead><tr><th scope="col">Opcode</th><th scope="col">Packet</th><th scope="col">Status</th><th scope="col">Reason</th>'
          '<th scope="col" class="num">Source files</th><th scope="col">Issues</th></tr></thead><tbody>')
        order = {"rejected": 0, "conditional": 1, "unknown": 2, "handled": 3}
        for r in sorted(p["rows"], key=lambda r: (order.get(r["status"], 4), -len(r["issues"]), r["kind"] != "type-3", r["opcode"])):
            kind, label = PM4_CHIP.get(r["status"], ("idle", r["status"]))
            iss = " ".join(f'<a href="https://github.com/{esc(repo)}/issues/{n}">#{n}</a>' for n in r["issues"][:6])
            iss += f' <span class="muted">+{len(r["issues"]) - 6}</span>' if len(r["issues"]) > 6 else ""
            w(f'<tr><td class="nowrap"><code>{esc(r["hex"])}</code></td><th scope="row"><code>{esc(r["name"])}</code></th>'
              f'<td>{chip(label, kind)}</td><td class="muted">{esc(r["reason"] or "")}</td>'
              f'<td class="num">{len(r["source_files"]) if r["kind"] == "type-3" else "—"}</td>'
              f'<td>{iss or "<span class=muted>0</span>"}</td></tr>')
        w("</tbody></table></div></div>")

    if cov.get("hle"):
        h = cov["hle"]
        gaps_ = [g for g in h["groups"] if g["todo"] > 0]
        full = [g for g in h["groups"] if g["todo"] == 0]
        w('<div class="sub"><h3 id="hle-h">HLE libraries</h3>'
          f'<p>From <a href="{esc(h["source"])}">progress.json</a>. Libraries with missing functions, those that issues ask for first. '
          'The last column lists missing functions that issue text names.</p>')
        w('<div class="table-scroll" role="region" aria-labelledby="hle-h" tabindex="0"><table class="data">'
          '<thead><tr><th scope="col">Library</th><th scope="col" class="num">Done</th><th scope="col" class="num">Missing</th>'
          '<th scope="col">Coverage</th><th scope="col">Missing, named in issues</th></tr></thead><tbody>')
        for g in gaps_:
            asked = []
            for name, nums in list(g["requested"].items())[:4]:
                links = " ".join(f'<a href="https://github.com/{esc(repo)}/issues/{n}">#{n}</a>' for n in nums[:3])
                asked.append(f"<li><code>{esc(name)}</code> {links}</li>")
            asked_html = f'<ul>{"".join(asked)}</ul>' if asked else '<span class="muted">—</span>'
            if len(g["requested"]) > 4:
                asked_html += f'<span class="muted">+{len(g["requested"]) - 4} more</span>'
            w(f'<tr><th scope="row"><code>{esc(g["library"])}</code></th><td class="num">{g["done"]}</td><td class="num">{g["todo"]}</td>'
              f'<td class="nowrap"><span class="bar" aria-hidden="true"><span style="width:{g["percent"]}%"></span></span> {g["percent"]:.1f}%</td>'
              f'<td>{asked_html}</td></tr>')
        w("</tbody></table></div>")
        if full:
            w(f'<details><summary>Complete libraries ({len(full)})</summary><p>' +
              ", ".join(f'<code>{esc(g["library"])}</code>' for g in full) + "</p></details>")
        w("</div>")

    if cov.get("isa"):
        i = cov["isa"]
        complete = all(g["todo"] == 0 for g in i["groups"])
        w('<div class="sub"><h3 id="isa-h">RDNA ISA decode</h3>'
          f'<p>Decoder coverage per encoding from <a href="{esc(i["source"])}">progress.json</a>. '
          + (f'All {len(i["groups"])} encodings decode every listed opcode. ' if complete else "")
          + 'Decoding is not the same as correct translation; the ranking above is where translation still fails.</p>')
        if complete:
            w(f'<details><summary>Opcodes per encoding ({len(i["groups"])})</summary>')
        w('<div class="table-scroll short" role="region" aria-labelledby="isa-h" tabindex="0"><table class="data">'
          '<thead><tr><th scope="col">Encoding</th><th scope="col" class="num">Decoded</th><th scope="col" class="num">Missing</th>'
          '<th scope="col">Coverage</th></tr></thead><tbody>')
        for g in i["groups"]:
            w(f'<tr><th scope="row"><code>{esc(g["encoding"])}</code></th><td class="num">{g["done"]}</td><td class="num">{g["todo"]}</td>'
              f'<td class="nowrap"><span class="bar" aria-hidden="true"><span style="width:{g["percent"]}%"></span></span> {g["percent"]:.1f}%</td></tr>')
        w("</tbody></table></div>" + ("</details>" if complete else "") + "</div>")

    if cov.get("registers"):
        w('<div class="sub"><h3 id="reg-h">Registers named in issues</h3>'
          '<p>GPU register names that issues mention most, and how many driver source files name them. '
          'The driver mostly addresses registers by offset, so a zero here does not mean unhandled.</p>')
        w('<div class="table-scroll" role="region" aria-labelledby="reg-h" tabindex="0"><table class="data">'
          '<thead><tr><th scope="col">Register</th><th scope="col" class="num">Issues</th><th scope="col">Where</th>'
          '<th scope="col" class="num">Driver files naming it</th></tr></thead><tbody>')
        for r in cov["registers"][:20]:
            iss = " ".join(f'<a href="https://github.com/{esc(repo)}/issues/{n}">#{n}</a>' for n in r["issues"][:5])
            w(f'<tr><th scope="row"><code>{esc(r["name"])}</code></th><td class="num">{r["issue_count"]}</td><td>{iss}</td>'
              f'<td class="num">{r["source_files"]}</td></tr>')
        w("</tbody></table></div></div>")
    w("</section>")

    # (4) focus areas
    f = doc["focus"]
    w('<section id="focus" aria-labelledby="focus-h"><div class="section-head"><h2 id="focus-h">Focus areas</h2>'
      '<p>Areas whose ranked blockers carry the most score. Computed from the ranking above, not set by the maintainers.</p></div>')
    w('<div class="areas">')
    for a in f["areas"]:
        items = "".join(
            f'<li>{blocker_link(B[bid], repo)} {esc(clip(B[bid]["title"], 72))} <span class="muted">({B[bid]["score"]})</span></li>'
            for bid in a["blockers"])
        w(f'<article class="area" aria-labelledby="area-{esc(a["area"] or "none")}">'
          f'<div class="area-head"><h3 id="area-{esc(a["area"] or "none")}">{esc(a["name"])}</h3><span class="score">score {a["score"]}</span></div>'
          f'<p>{a["blocker_count"]} ranked blocker{"s" if a["blocker_count"] != 1 else ""} on {a["titles"]} title{"s" if a["titles"] != 1 else ""}; '
          f'first stop for {a["frontier_titles"]}. Open fix PRs: {a["open_fix_prs"]}.</p><ol>{items}</ol></article>')
    w("</div>")
    if f["help_wanted"]:
        w('<div class="sub"><h3 id="help-h">Help wanted</h3>'
          '<p>Ranked blockers with no open fix PR, explicit asks from the curated file, and issues labelled for help.</p><ul class="help">')
        for hw in f["help_wanted"]:
            b = B[hw["blocker"]]
            w(f'<li><span>{blocker_link(b, repo)} {esc(b["title"])}</span><span class="why">{esc(hw["reason"])}</span></li>')
        w("</ul></div>")
    w("</section>")

    # (5) about / disclaimer
    w('<section id="about" aria-labelledby="about-h"><div class="section-head"><h2 id="about-h">About this data</h2></div><div class="prose">')
    w('<p class="disclaimer"><b>Generated data, community prototype, not official.</b> This page is built by a script from public '
      f'GitHub issues and PRs of <a href="https://github.com/{esc(repo)}">{esc(repo)}</a> plus a small curated file. '
      'The maintainers have not reviewed it. Mined entries can be wrong; check the linked source before you act on one.</p>')
    w(f'<p>Issues and PRs come from the GitHub API: all open ones and those closed in the last {doc["window"]["days"]} days. '
      'Title IDs, names, stages and error signatures are mined from issue and PR text. GitHub “blocked by” links are used where they exist. '
      'Entries marked <b>curated</b> come from <code>data/blockers.json</code> and win over mined ones.</p>')
    w('<ul><li><a href="roadmap.json">roadmap.json</a>: everything on this page, with a schema version</li>'
      '<li><a href="ROADMAP.md">ROADMAP.md</a>: the same as Markdown</li>'
      '<li><a href="llms.txt">llms.txt</a>: a guide to these files for AI agents</li>'
      '<li><a href="AGENTS.md">AGENTS.md</a>: how to curate <code>blockers.json</code></li></ul>')
    w('<details><summary>Known gaps in the mining</summary><ul>' + "".join(f"<li>{esc(g)}</li>" for g in doc["gaps"]) + "</ul></details>")
    w("</div></section>")
    w("</main>")
    w(f'<footer><div class="wrap">Generated {esc(gen)} from <a href="https://github.com/{esc(repo)}">{esc(repo)}</a>. '
      'Not affiliated with the AnyPS5 maintainers or Sony.</div></footer>\n</body>\n</html>\n')
    return "\n".join(out)


def evidence_label(url: str, repo: str) -> str:
    m = re.search(r"/(issues|pull)/(\d+)(#issuecomment-\d+)?", url or "")
    if not m:
        return "COMPATIBILITY.md" if url and "COMPATIBILITY" in url else "source"
    return f"#{m.group(2)}" + (" comment" if m.group(3) else "")


def md_cell(text) -> str:
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ")


def render_markdown(doc: dict) -> str:
    repo = doc["upstream"]["repo"]
    B = {b["id"]: b for b in doc["blockers"]}
    T = {t["id"]: t for t in doc["titles"]}
    s = doc["stats"]
    L = []
    a = L.append
    a("# AnyPS5 blocker map\n")
    a(f"> Generated data, community prototype, not official. Built {doc['generated_at']} from public GitHub data of "
      f"[{repo}](https://github.com/{repo}) at `{(doc['upstream'].get('commit') or '?')[:8]}` plus `data/blockers.json`.\n")
    a(f"Issues read: {s['issues_scanned']} · PRs read: {s['prs_scanned']} · titles: {s['titles']} · open blockers: {s['blockers_open']} "
      f"({s['blockers_ranked']} block at least one title) · curated blockers: {s['blockers_curated']}\n")
    a("Score = 3 × one_fix_away + 2 × frontier + total. Frontier: titles for which the blocker is the first open one. "
      "One fix away: titles for which it is the only open one.\n")
    a("## Focus areas\n")
    for i, ar in enumerate(doc["focus"]["areas"], 1):
        tops = ", ".join(md_ref(B[b]) for b in ar["blockers"])
        a(f"{i}. **{ar['name']}** (score {ar['score']}): {ar['blocker_count']} blockers on {ar['titles']} titles, "
          f"first stop for {ar['frontier_titles']}; open fix PRs {ar['open_fix_prs']}. Top: {tops}")
    a("")
    a("## Blocker ranking\n")
    a("| # | Blocker | Frontier | One fix away | Total | Score | Area | PRs | Last activity |")
    a("|--:|---|--:|--:|--:|--:|---|---|---|")
    ranked = [B[i] for i in doc["ranking"] if B[i]["score"] > 0]
    for n, b in enumerate(ranked, 1):
        prs = ", ".join(f"[{p['ref']}]({p['url']}) {p['state']}" for p in b["prs"][:4]) or "none"
        a(f"| {n} | {md_ref(b)} {md_cell(b['title'])} ({b['origin']}) | {b['frontier']} | {b['one_fix_away']} | {b['total']} | "
          f"**{b['score']}** | {b['area'] or '—'} | {md_cell(prs)} | {fmt_date(b.get('last_activity'))} |")
    a("")
    a("## Titles\n")
    a("| ID | Title | Best stage | Where | Open blockers, in order |")
    a("|---|---|---|---|---|")
    shown = [t for t in doc["titles"] if t["best_stage"] or t["open_blockers"]]
    shown.sort(key=lambda t: (-(STAGES.index(t["best_stage"]["stage"]) if t["best_stage"] else -1), len(t["open_blockers"]), (t["name"] or t["id"]).lower()))
    for t in shown:
        best = t["best_stage"]
        stage = f"{best['stage']} ({best['origin']})" if best else "—"
        where = " · ".join(x for x in [best.get("os"), best.get("gpu"), best.get("build")] if x) if best else ""
        chain = " → ".join(md_ref(B[st["id"]]) + (f" ({'/'.join(st['scope'])})" if st.get("scope") else "") for st in t["open_blockers"][:6] if st["id"] in B)
        a(f"| `{t['id']}` | {md_cell(t['name'] or '')} | {stage} | {md_cell(where)} | {chain or '—'} |")
    a("")
    cov = doc["coverage"]
    a("## Coverage\n")
    if cov.get("isa"):
        a(f"- RDNA ISA decode: {cov['isa']['done']} of {cov['isa']['total']} ({cov['isa']['percent']}%)")
    if cov.get("hle"):
        a(f"- HLE functions: {cov['hle']['done']} of {cov['hle']['total']} ({cov['hle']['percent']}%)")
    if cov.get("pm4"):
        c = cov["pm4"]["counts"]
        a(f"- PM4 type-3 packets: {c.get('handled', 0)} handled, {c.get('conditional', 0)} conditional, {c.get('rejected', 0)} rejected of {cov['pm4']['total']}")
        a("\n| Opcode | Packet | Status | Reason | Issues |\n|---|---|---|---|---|")
        for r in cov["pm4"]["rows"]:
            if r["status"] != "handled":
                a(f"| `{r['hex']}` | `{r['name']}` | {r['status']} | {md_cell(r['reason'] or '')} | {', '.join('#%d' % n for n in r['issues'][:5])} |")
    if cov.get("hle"):
        asked = [(g["library"], n, nums) for g in cov["hle"]["groups"] for n, nums in g["requested"].items()]
        if asked:
            a("\nMissing HLE functions named in issues:\n")
            for lib, name, nums in asked[:30]:
                a(f"- `{lib}`: `{name}` ({', '.join('#%d' % n for n in nums[:4])})")
    a("")
    a("## Help wanted\n")
    for hw in doc["focus"]["help_wanted"]:
        b = B[hw["blocker"]]
        a(f"- {md_ref(b)} {md_cell(b['title'])}: {hw['reason']}")
    a("")
    a("## Known gaps\n")
    for g in doc["gaps"]:
        a(f"- {g}")
    a("")
    return "\n".join(L) + "\n"


def md_ref(b: dict) -> str:
    if b.get("issue"):
        return f"[#{b['issue']}]({b['url']})"
    if b.get("parent"):
        return f"[row in #{b['parent']}]({b['url']})"
    return f"[{b['id']}]({b['url']})" if b.get("url") else f"`{b['id']}`"


def render_llms(doc: dict) -> str:
    repo = doc["upstream"]["repo"]
    B = {b["id"]: b for b in doc["blockers"]}
    top = [B[i] for i in doc["ranking"][:5]]
    L = [
        "# AnyPS5 blocker map",
        "",
        f"> Generated technical roadmap for the AnyPS5 PS5 emulator (https://github.com/{repo}): which open issues block which PS5 "
        "titles, ranked by how many titles a fix would move, plus HLE, RDNA ISA and PM4 coverage. Community prototype, not official; "
        "regenerated from GitHub data by roadmap.py.",
        "",
        f"Snapshot {doc['generated_at']}, upstream commit {(doc['upstream'].get('commit') or '?')[:8]}. "
        f"{doc['stats']['blockers_open']} open blockers, {doc['stats']['titles']} titles. Top of the ranking:",
        "",
    ]
    for b in top:
        L.append(f"- {md_ref(b)} {b['title']} (score {b['score']}: frontier {b['frontier']}, one fix away {b['one_fix_away']}, total {b['total']})")
    L += [
        "",
        "How to read the data:",
        "",
        "- Stages, lowest to highest: " + ", ".join(STAGES) + ". `best_stage` is the highest reported one with os, gpu, build and a source url.",
        "- A title's `open_blockers` are ordered: the first entry is where it stops now. `scope` limits a step to an OS/GPU path.",
        "- `origin` is `curated` (data/blockers.json, reviewed by a person), `mined` (regex rules over issue and PR text), "
        "`upstream` (docs/user/COMPATIBILITY.md) or `github` (native blocked-by links). Prefer curated facts when they conflict.",
        "- Blocker ids are upstream issue numbers, `pr-N` for blockers known only through a PR, `N~symbol` for a crash site that only "
        "appears as a row in tracker issue N, or a slug.",
        "- Import signatures are keyed by NID, so `undefined symbol: X` (Linux) and `FAIL: unresolved ELF import X ...` (Windows) match.",
        "- Do not quote mined stages as fact without opening the `url` next to them.",
        "",
        "## Data",
        "",
        f"- [roadmap.json](roadmap.json): full data, `schema_version` {doc['schema_version']}. Keys: stages, scoring, stats, ranking "
        "(blocker ids, best first), blockers, titles, coverage (isa, hle, pm4, registers), focus (areas, help_wanted), gaps, sources.",
        "- [ROADMAP.md](ROADMAP.md): ranking, titles, coverage and help wanted as Markdown tables.",
        "- [index.html](index.html): the same for people.",
        "",
        "## Curation",
        "",
        "- [AGENTS.md](AGENTS.md): how to add or correct curated blockers and title chains in data/blockers.json, and how to verify them.",
        "",
        "## Optional",
        "",
        f"- [Upstream repository](https://github.com/{repo}): issues, PRs and source.",
        f"- [Upstream progress.json]({PROGRESS_URL}): HLE and ISA decode counts this page reuses.",
        f"- [COMPATIBILITY.md](https://github.com/{repo}/blob/main/docs/user/COMPATIBILITY.md): the maintainers' tested-compatibility table.",
        "",
    ]
    return "\n".join(L)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def load_curated(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": 1, "blockers": [], "titles": [], "not_blockers": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    ids = [str(b["id"]) for b in data.get("blockers", [])]
    dupes = [i for i, c in Counter(ids).items() if c > 1]
    if dupes:
        raise SystemExit(f"duplicate blocker ids in {path}: {dupes}")
    known = set(ids)
    for t in data.get("titles", []):
        for step in t.get("blockers", []):
            if str(step["id"]) not in known:
                raise SystemExit(f"{path}: title {t['id']} names unknown blocker {step['id']}")
    return data


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=UPSTREAM)
    ap.add_argument("--out", default=str(ROOT / "site"))
    ap.add_argument("--curated", default=str(CURATED))
    ap.add_argument("--cache", default=str(CACHE), help="raw API data is written here and read back with --offline")
    ap.add_argument("--offline", action="store_true", help="reuse the cached API data instead of calling GitHub")
    ap.add_argument("--upstream-checkout", default=os.environ.get("ANYPS5_CHECKOUT"),
                    help="local clone or worktree of the upstream repo (for git show / git grep)")
    ap.add_argument("--ref", default="origin/main", help="ref to read inside the checkout")
    ap.add_argument("--no-git-fetch", action="store_true", help="do not run git fetch in the checkout")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    def log(msg):
        print(msg, flush=True)

    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    curated = load_curated(Path(args.curated))
    cache = Path(args.cache)
    if args.offline:
        raw = json.loads(cache.read_text(encoding="utf-8"))
        log(f"using cached API data from {raw.get('fetched_at')}")
    else:
        cutoff = (now - dt.timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
        log(f"collecting {args.repo} (closed since {cutoff})")
        raw = collect(args.repo, cutoff, curated, log)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(raw), encoding="utf-8")
        log(f"rate limit before/after: {raw['rate_limit']}")
    checkout = Path(args.upstream_checkout) if args.upstream_checkout else None
    upstream = Upstream(checkout, args.ref, args.repo, fetch=not (args.offline or args.no_git_fetch), log=log)
    if not checkout:
        log("no --upstream-checkout: PM4 handler status and source counts are skipped")
    try:
        progress = json.loads(http_get(PROGRESS_URL))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        log(f"progress.json unavailable: {e}")
        progress = None
    compat = upstream.raw("docs/user/COMPATIBILITY.md")
    model = Model(raw, curated, args.repo, now, compat, progress)
    coverage = build_coverage(model, upstream, progress, log)
    doc = assemble(model, coverage, raw, upstream, now)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "roadmap.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "ROADMAP.md").write_text(render_markdown(doc), encoding="utf-8")
    (out / "index.html").write_text(render_html(doc), encoding="utf-8")
    (out / "llms.txt").write_text(render_llms(doc), encoding="utf-8")
    if (ROOT / "AGENTS.md").exists():
        shutil.copyfile(ROOT / "AGENTS.md", out / "AGENTS.md")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    s = doc["stats"]
    log(f"issues {s['issues_scanned']} (open {s['issues_open']}), PRs {s['prs_scanned']}, titles {s['titles']}, "
        f"open blockers {s['blockers_open']} ({s['blockers_ranked']} ranked), wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
