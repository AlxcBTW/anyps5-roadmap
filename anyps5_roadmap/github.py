"""GitHub access through the gh CLI (GraphQL and REST), with retries for transient errors."""

from __future__ import annotations

import json
import re
import subprocess
import time


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
        transient = (
            status in (None, 500, 502, 503, 504) or "secondary rate limit" in err.lower() or "timeout" in err.lower()
        )
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
        return {
            k: {"remaining": res[k]["remaining"], "limit": res[k]["limit"]}
            for k in ("core", "graphql", "search")
            if k in res
        }
    except GhError:
        return {}
