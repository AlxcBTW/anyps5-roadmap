"""Technical roadmap / blocker map generator for AnyPS5 (community prototype).

Command line entry point: collect (or reuse the cache), build the model and write site/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
import urllib.error
from collections import Counter
from pathlib import Path

import render_html

from .assemble import assemble
from .collect import collect
from .config import CACHE, CURATED, ROOT, STAGES, UPSTREAM, WINDOW_DAYS, PROGRESS_URL
from .coverage import build_coverage
from .model import Model
from .render_md import render_llms, render_markdown
from .upstream import Upstream, http_get


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
        for ev in t.get("evidence", []):
            if not ev.get("url") or ev.get("stage") not in STAGES:
                raise SystemExit(f"{path}: title {t['id']}: every curated stage needs a known stage and a public url ({ev})")
    for rv in data.get("stage_reviews", []):
        need = ["title", "claim", "claim_url", "verdict", "quote"]
        if rv.get("verdict") in ("confirmed", "downgraded"):
            need += ["stage", "url"]
        elif rv.get("verdict") != "suppressed":
            raise SystemExit(f"{path}: stage review for {rv.get('title')}: verdict must be confirmed, downgraded or suppressed")
        missing = [k for k in need if not rv.get(k)]
        if missing or (rv.get("stage") and rv["stage"] not in STAGES):
            raise SystemExit(f"{path}: stage review for {rv.get('title')} lacks {missing or 'a known stage'}")
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
    lf = {"encoding": "utf-8", "newline": "\n"}  # same bytes on Windows and on the Actions runner
    (out / "roadmap.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", **lf)
    (out / "ROADMAP.md").write_text(render_markdown(doc), **lf)
    (out / "llms.txt").write_text(render_llms(doc), **lf)
    if (ROOT / "AGENTS.md").exists():
        shutil.copyfile(ROOT / "AGENTS.md", out / "AGENTS.md")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    (out / "index.html").write_text(render_html.Page(doc, out).render(), **lf)  # last: it lists the sizes of the other files
    s = doc["stats"]
    log(f"issues {s['issues_scanned']} (open {s['issues_open']}), PRs {s['prs_scanned']}, titles {s['titles']}, "
        f"open blockers {s['blockers_open']} ({s['blockers_ranked']} ranked), wrote {out}")
    return 0
