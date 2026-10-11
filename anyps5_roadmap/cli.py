"""Technical roadmap / blocker map generator for AnyPS5 (community prototype).

Command line entry point: collect (or reuse the cache), build the model and write site/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
import urllib.error
from collections import Counter
from pathlib import Path

import render_html

from .assemble import assemble
from .collect import collect
from .config import CACHE, CURATED, PROGRESS_URL, ROOT, STAGES, UPSTREAM, WINDOW_DAYS
from .coverage import build_coverage
from .feed import publish as publish_feed
from .model import Model
from .render_md import render_llms, render_markdown
from .upstream import Upstream, http_get

AREAS = ("shader", "agc", "libkernel", "libc", "relinker", "prx")
VERDICTS = ("confirmed", "downgraded", "suppressed")
TITLE_ID = re.compile(r"PPSA\d{5}")


def _where(kind: str, i: int, item: dict, key: str = "id") -> str:
    label = item.get(key) if isinstance(item, dict) else None
    return f"{kind}[{i}]" + (f" ({label})" if label else "")


def validate_curated(data: dict) -> list[str]:
    """Every rule from AGENTS.md that a machine can check. Returns readable errors, empty when valid."""
    if not isinstance(data, dict):
        return ["the top level must be a JSON object"]
    errors: list[str] = []
    blockers = data.get("blockers", [])
    ids = [str(b.get("id")) for b in blockers]
    for dupe in sorted(i for i, c in Counter(ids).items() if c > 1):
        errors.append(f"blocker id {dupe!r} is used more than once; ids must be unique")
    for i, b in enumerate(blockers):
        at = _where("blockers", i, b)
        if not b.get("id"):
            errors.append(f"{at}: needs an id (the upstream issue number as a string, pr-N or a short slug)")
        if b.get("issue") is not None and not isinstance(b["issue"], int):
            errors.append(f"{at}: issue must be a number or null, not {b['issue']!r}")
        if b.get("area") and b["area"] not in AREAS:
            errors.append(f"{at}: area {b['area']!r} is not one of {', '.join(AREAS)}")
        if b.get("status") and b["status"] not in ("open", "resolved"):
            errors.append(f"{at}: status must be open or resolved, not {b['status']!r}")
        for field in ("fix_prs", "related_prs"):
            for j, ref in enumerate(b.get(field, [])):
                if not isinstance(ref, dict) or not str(ref.get("number", "")).isdigit():
                    errors.append(f'{at}: {field}[{j}] needs a PR number, e.g. {{"number": 454}}')
    known = set(ids)
    for i, t in enumerate(data.get("titles", [])):
        at = _where("titles", i, t)
        if not TITLE_ID.fullmatch(str(t.get("id", ""))):
            errors.append(f"{at}: id must be a PS5 title ID, PPSA plus five digits")
        for j, step in enumerate(t.get("blockers", [])):
            if str(step.get("id")) not in known:
                errors.append(f"{at}: blockers[{j}] names blocker {step.get('id')!r}, which is not in blockers[]")
        for j, ev in enumerate(t.get("evidence", [])):
            if ev.get("stage") not in STAGES:
                errors.append(f"{at}: evidence[{j}] has stage {ev.get('stage')!r}; use one of {', '.join(STAGES)}")
            if not ev.get("url"):
                errors.append(f"{at}: evidence[{j}] has no url; a stage without a public source cannot be added")
    for i, rv in enumerate(data.get("stage_reviews", [])):
        at = _where("stage_reviews", i, rv, "title")
        need = ["title", "claim", "claim_url", "verdict", "quote"]
        if rv.get("verdict") in ("confirmed", "downgraded"):
            need += ["stage", "url"]
        elif rv.get("verdict") not in VERDICTS:
            errors.append(f"{at}: verdict must be confirmed, downgraded or suppressed, not {rv.get('verdict')!r}")
        missing = [k for k in need if not rv.get(k)]
        if missing:
            errors.append(f"{at}: missing {', '.join(missing)}")
        for key in ("claim", "stage"):
            if rv.get(key) and rv[key] not in STAGES:
                errors.append(f"{at}: {key} {rv[key]!r} is not a stage; use one of {', '.join(STAGES)}")
    for i, nb in enumerate(data.get("not_blockers", [])):
        if not isinstance(nb.get("issue"), int):
            errors.append(f"{_where('not_blockers', i, nb, 'issue')}: issue must be an upstream issue number")
    return errors


def load_curated(path: Path) -> dict:
    """Read data/blockers.json; stop with every rule it breaks, one per line."""
    if not path.exists():
        return {"schema_version": 1, "blockers": [], "titles": [], "not_blockers": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{path}:{e.lineno}:{e.colno}: not valid JSON: {e.msg}") from None
    errors = validate_curated(data)
    if errors:
        head = f"{path}: {len(errors)} problem{'s' if len(errors) != 1 else ''}:"
        raise SystemExit("\n".join([head] + [f"  - {e}" for e in errors]))
    return data


def validate_command(path: Path) -> int:
    """--validate: check the curated file and say what it holds. Annotates the file on GitHub Actions."""
    try:
        data = load_curated(path)
    except SystemExit as e:
        print(e, file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS") == "true":
            for line in str(e).splitlines()[1:] or [str(e)]:
                print(f"::error file={path.as_posix()}::{line.strip().removeprefix('- ')}")
        return 1
    counts = {k: len(data.get(k, [])) for k in ("blockers", "titles", "stage_reviews", "not_blockers")}
    print(f"{path}: valid ({', '.join(f'{n} {k}' for k, n in counts.items())})")
    return 0


def read_cached_or_fetch(cache_dir: Path, name: str, fetch, offline: bool, network: bool, log) -> str | None:
    """Upstream inputs (progress.json, COMPATIBILITY.md) are saved next to the API cache on a live run,
    so an offline build reads the same snapshot. Without a saved copy, fetch it unless the network is off."""
    saved = cache_dir / name
    if offline and saved.exists():
        return saved.read_text(encoding="utf-8")
    if not network:
        log(f"{name}: no saved copy in {cache_dir} and --no-network is set; skipped")
        return None
    text = fetch()
    if text is not None and not offline:
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_text(text, encoding="utf-8", newline="\n")
    return text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=UPSTREAM)
    ap.add_argument("--out", default=str(ROOT / "site"))
    ap.add_argument("--curated", default=str(CURATED))
    ap.add_argument("--cache", default=str(CACHE), help="raw API data is written here and read back with --offline")
    ap.add_argument("--offline", action="store_true", help="reuse the cached API data instead of calling GitHub")
    ap.add_argument(
        "--upstream-checkout",
        default=os.environ.get("ANYPS5_CHECKOUT"),
        help="local clone or worktree of the upstream repo (for git show / git grep)",
    )
    ap.add_argument("--ref", default="origin/main", help="ref to read inside the checkout")
    ap.add_argument("--no-git-fetch", action="store_true", help="do not run git fetch in the checkout")
    ap.add_argument(
        "--no-network",
        action="store_true",
        help="with --offline: never touch the network; progress.json and COMPATIBILITY.md come from the cache directory",
    )
    ap.add_argument("--validate", action="store_true", help="only check the curated file (--curated) and exit")
    ap.add_argument("--refresh", action="store_true", help="read every thread again instead of reusing threads.json")
    args = ap.parse_args(argv)
    if args.validate:
        return validate_command(Path(args.curated))
    if args.no_network and not args.offline:
        ap.error("--no-network needs --offline: a live run reads GitHub")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    def log(msg):
        print(msg, flush=True)

    now = dt.datetime.now(dt.UTC).replace(microsecond=0)
    curated = load_curated(Path(args.curated))
    cache = Path(args.cache)
    if args.offline:
        raw = json.loads(cache.read_text(encoding="utf-8"))
        log(f"using cached API data from {raw.get('fetched_at')}")
    else:
        cutoff = (now - dt.timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
        log(f"collecting {args.repo} (closed since {cutoff})")
        raw = collect(args.repo, cutoff, curated, log, cache_dir=cache.parent, refresh=args.refresh)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(raw), encoding="utf-8")
        log(f"graphql cost {raw['api']['graphql_cost']}, remaining {raw['api']['graphql_remaining']}")
    checkout = Path(args.upstream_checkout) if args.upstream_checkout else None
    network = not args.no_network
    fetch = not (args.offline or args.no_git_fetch)
    upstream = Upstream(checkout, args.ref, args.repo, fetch=fetch, log=log, network=network)
    if not checkout:
        log("no --upstream-checkout: PM4 handler status and source counts are skipped")

    def fetch_progress() -> str | None:
        try:
            return http_get(PROGRESS_URL).decode("utf-8")
        except (urllib.error.URLError, TimeoutError, UnicodeDecodeError) as e:
            log(f"progress.json unavailable: {e}")
            return None

    progress_text = read_cached_or_fetch(cache.parent, "progress.json", fetch_progress, args.offline, network, log)
    try:
        progress = json.loads(progress_text) if progress_text else None
    except json.JSONDecodeError as e:
        log(f"progress.json is not valid JSON: {e}")
        progress = None
    compat = read_cached_or_fetch(
        cache.parent, "COMPATIBILITY.md", lambda: upstream.raw("docs/user/COMPATIBILITY.md"), args.offline, network, log
    )
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
    fonts = ROOT / "site" / "fonts"
    if fonts.is_dir() and (out / "fonts").resolve() != fonts.resolve():
        shutil.copytree(fonts, out / "fonts", dirs_exist_ok=True)  # a build outside site/ still renders in Geist
    # against the live site, before the deploy replaces it; only a live run keeps a copy next to the API cache
    publish_feed(doc, out, None if args.offline else cache.parent, network, log)
    # last: the classic page lists the sizes of the other files. index.html gets the same page, so a build
    # without Node still has a front page; the Pages workflow puts the web app (web/) there instead.
    classic = render_html.Page(doc, out).render()
    (out / "classic.html").write_text(classic, **lf)
    (out / "index.html").write_text(classic, **lf)
    s = doc["stats"]
    log(
        f"issues {s['issues_scanned']} (open {s['issues_open']}), PRs {s['prs_scanned']}, titles {s['titles']}, "
        f"open blockers {s['blockers_open']} ({s['blockers_ranked']} ranked), wrote {out}"
    )
    return 0
