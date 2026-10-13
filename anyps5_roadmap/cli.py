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

from . import images as cover_images
from .assemble import assemble
from .collect import collect
from .config import (
    CACHE,
    CATALOG_PS4_URL,
    CATALOG_URL,
    CURATED,
    GAMES,
    PROGRESS_URL,
    ROOT,
    STAGES,
    TAGS,
    UPSTREAM,
    WINDOW_DAYS,
    WORKING_GROUPS,
)
from .coverage import build_coverage
from .feed import publish as publish_feed
from .identity import CATALOG_SOURCE, parse_catalog
from .identity import TITLE_ID as ANY_TITLE_ID
from .model import Model
from .render_md import render_llms, render_markdown
from .upstream import Upstream, fetch_cached, http_get

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
        if "name_sources" in t:
            links = t["name_sources"]
            if not t.get("name"):
                errors.append(f"{at}: name_sources without a name")
            if not isinstance(links, list) or not links:
                errors.append(f"{at}: name_sources needs the public links that tie this title ID to its name")
                links = []
            for url in links:
                if not str(url).startswith("https://"):
                    errors.append(f"{at}: name source {url!r} must be an https link")
        for j, step in enumerate(t.get("blockers", [])):
            if str(step.get("id")) not in known:
                errors.append(f"{at}: blockers[{j}] names blocker {step.get('id')!r}, which is not in blockers[]")
        for j, step in enumerate(t.get("excluded", [])):
            if str(step.get("id")) not in known:
                errors.append(f"{at}: excluded[{j}] names blocker {step.get('id')!r}, which is not in blockers[]")
            if not step.get("why"):
                errors.append(f"{at}: excluded[{j}] needs a why")
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
    errors += validate_title_tags(data.get("title_tags", []))
    return errors


def validate_title_tags(entries: list) -> list[str]:
    """title_tags: one entry per title ID, tags from the fixed list, and the public sources they come from."""
    errors: list[str] = []
    seen = Counter(str(e.get("title")) for e in entries if isinstance(e, dict))
    for dupe in sorted(t for t, c in seen.items() if c > 1):
        errors.append(f"title_tags: {dupe} has more than one entry; put all of its tags in one")
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            errors.append(f"title_tags[{i}]: must be an object")
            continue
        at = _where("title_tags", i, e, "title")
        if not TITLE_ID.fullmatch(str(e.get("title", ""))):
            errors.append(f"{at}: title must be a PS5 title ID, PPSA plus five digits")
        if not e.get("name"):
            errors.append(f"{at}: needs the name the sources were matched on")
        tags = e.get("tags")
        if not isinstance(tags, list) or not tags:
            errors.append(f"{at}: needs a list of tags; a title without a source gets no entry")
            tags = []
        for tag in tags:
            if tag not in TAGS:
                errors.append(f"{at}: tag {tag!r} is not one of {', '.join(TAGS)}")
        for dupe in sorted(t for t, c in Counter(map(str, tags)).items() if c > 1):
            errors.append(f"{at}: tag {dupe!r} is listed twice")
        if "2D" in tags and "3D" in tags:
            errors.append(f"{at}: 2D and 3D exclude each other; when sources disagree, use neither")
        if "App" in tags and len(tags) > 1:
            errors.append(f"{at}: App means not a game, so it takes no other tag")
        sources = e.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append(f"{at}: needs sources, the public links its tags come from")
            sources = []
        for url in sources:
            if not str(url).startswith("https://"):
                errors.append(f"{at}: source {url!r} must be an https link")
    return errors


def validate_games(data: dict) -> list[str]:
    """data/games.json: games listed by hand (their title IDs, name, aliases and picture) and title IDs that
    must stay apart. Every entry rests on public sources."""
    if not isinstance(data, dict):
        return ["the top level must be a JSON object"]
    errors: list[str] = []
    owner: dict[str, int] = {}
    for i, g in enumerate(data.get("games", [])):
        at = _where("games", i, g, "name")
        ids = g.get("title_ids")
        if not isinstance(ids, list) or not ids:
            errors.append(f"{at}: needs title_ids, the PS5 (PPSA) or PS4 (CUSA) title IDs of the game")
            ids = []
        for tid in ids:
            if not ANY_TITLE_ID.fullmatch(str(tid)):
                errors.append(f"{at}: {tid!r} is not a title ID (PPSA or CUSA plus five digits)")
            elif tid in owner:
                errors.append(f"{at}: {tid} is already listed in games[{owner[tid]}]; a title ID belongs to one game")
            else:
                owner[tid] = i
        if "name" in g and not (isinstance(g["name"], str) and g["name"].strip()):
            errors.append(f"{at}: name must be a non-empty string; leave it out to keep the store's name")
        aliases = g.get("aliases", [])
        if not isinstance(aliases, list) or not all(isinstance(a, str) and a.strip() for a in aliases):
            errors.append(f"{at}: aliases must be a list of names")
        sources = g.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append(f"{at}: needs sources, the public links that tie these title IDs and names to the game")
            sources = []
        for url in sources:
            if not str(url).startswith("https://"):
                errors.append(f"{at}: source {url!r} must be an https link")
        if "image" in g and g["image"] is not None:
            img = g["image"]
            url = img.get("url") or img.get("square") if isinstance(img, dict) else None
            if not url or not str(url).startswith("https://"):
                errors.append(f"{at}: image needs an https url (or null for no picture)")
    for i, d in enumerate(data.get("distinct", [])):
        at = f"distinct[{i}]"
        ids = d.get("title_ids") if isinstance(d, dict) else None
        if not isinstance(ids, list) or len(ids) < 2:
            errors.append(f"{at}: needs two or more title_ids that are different games")
            ids = []
        for tid in ids:
            if not ANY_TITLE_ID.fullmatch(str(tid)):
                errors.append(f"{at}: {tid!r} is not a title ID (PPSA or CUSA plus five digits)")
        if not isinstance(d, dict) or not d.get("reason"):
            errors.append(f"{at}: needs a reason")
    return errors


def load_games(path: Path) -> dict:
    """Read data/games.json; stop with every rule it breaks."""
    if not path.exists():
        return {"games": [], "distinct": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{path}:{e.lineno}:{e.colno}: not valid JSON: {e.msg}") from None
    errors = validate_games(data)
    if errors:
        head = f"{path}: {len(errors)} problem{'s' if len(errors) != 1 else ''}:"
        raise SystemExit("\n".join([head] + [f"  - {e}" for e in errors]))
    return data


def load_catalog(cache_dir: Path, offline: bool, network: bool, ps4: bool, log) -> tuple[dict, dict]:
    """The PlayStation title list: from the network on a live run (revalidated with its ETag, so an unchanged
    list costs one 304), else the copy a live run saved next to the API cache. The PS4 list only when a
    report names a CUSA ID."""
    catalog: dict = {}
    info = {"source": CATALOG_SOURCE, "files": []}
    for url, wanted in ((CATALOG_URL, True), (CATALOG_PS4_URL, ps4)):
        if not wanted:
            continue
        path = cache_dir / url.rsplit("/", 1)[1]
        if offline or not network:
            data = path.read_bytes() if path.exists() else None
        else:
            data = fetch_cached(url, path, log=log)
        if data is None:
            log(f"{path.name}: not available; names and region IDs come from the reports alone")
            continue
        part = parse_catalog(data.decode("utf-8", "replace"))
        catalog.update({k: v for k, v in part.items() if k not in catalog})
        info["files"].append({"url": url, "titles": len(part)})
    info["titles"] = len(catalog)
    return catalog, info


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


def validate_command(path: Path, games_path: Path | None = None) -> int:
    """--validate: check the curated files and say what they hold. Annotates the files on GitHub Actions."""
    status = 0
    for file, load, keys in (
        (path, load_curated, ("blockers", "titles", "stage_reviews", "not_blockers", "title_tags")),
        (games_path, load_games, ("games", "distinct")),
    ):
        if file is None:
            continue
        try:
            data = load(file)
        except SystemExit as e:
            print(e, file=sys.stderr)
            if os.environ.get("GITHUB_ACTIONS") == "true":
                for line in str(e).splitlines()[1:] or [str(e)]:
                    print(f"::error file={file.as_posix()}::{line.strip().removeprefix('- ')}")
            status = 1
            continue
        counts = {k: len(data.get(k, [])) for k in keys}
        print(f"{file}: valid ({', '.join(f'{n} {k}' for k, n in counts.items())})")
    return status


def read_cached_or_fetch(cache_dir: Path, name: str, fetch, offline: bool, network: bool, log) -> str | None:
    """Upstream inputs (progress.json) are saved next to the API cache on a live run,
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
    ap.add_argument("--games", default=str(GAMES), help="data/games.json: which title IDs are one game, by hand")
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
        help="with --offline: never touch the network; progress.json comes from the cache directory",
    )
    ap.add_argument("--validate", action="store_true", help="only check the curated file (--curated) and exit")
    ap.add_argument("--refresh", action="store_true", help="read every thread again instead of reusing threads.json")
    args = ap.parse_args(argv)
    if args.validate:
        return validate_command(Path(args.curated), Path(args.games))
    if args.no_network and not args.offline:
        ap.error("--no-network needs --offline: a live run reads GitHub")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    def log(msg):
        print(msg, flush=True)

    now = dt.datetime.now(dt.UTC).replace(microsecond=0)
    curated = load_curated(Path(args.curated))
    games = load_games(Path(args.games))
    cache = Path(args.cache)
    if args.offline:
        raw = json.loads(cache.read_text(encoding="utf-8"))
        log(f"using cached API data from {raw.get('fetched_at')}")
    else:
        cutoff = (now - dt.timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
        log(f"collecting {args.repo} (closed since {cutoff})")
        raw = collect(
            args.repo, cutoff, curated, log, cache_dir=cache.parent, refresh=args.refresh, working_groups=WORKING_GROUPS
        )
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
    ps4 = bool(re.search(r"\bCUSA\d{5}\b", json.dumps([raw.get("issues"), raw.get("prs"), raw.get("discussions")])))
    catalog, catalog_info = load_catalog(cache.parent, args.offline, network, ps4, log)
    model = Model(raw, curated, args.repo, now, progress=progress, catalog=catalog, games=games)
    coverage = build_coverage(model, upstream, progress, log)
    image_cache = cover_images.load_cache(cache.parent)
    if not args.offline and network:
        # the first store concept of every game: a game that is not on the page today may be tomorrow
        concepts = [g.concepts[0] for g in model.identity.games.values() if g.concepts]
        cover_images.refresh(concepts, image_cache, now, log=log)
        cover_images.save_cache(cache.parent, image_cache)
    doc = assemble(model, coverage, raw, upstream, now, images=image_cache, catalog_info=catalog_info)
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
        f"issues {s['issues_scanned']} (open {s['issues_open']}), PRs {s['prs_scanned']}, "
        f"discussions {s['discussions_scanned']}, games {s['games']} ({s['title_ids_folded']} more title "
        f"ID{'s' if s['title_ids_folded'] != 1 else ''} folded in, {s['games_with_image']} with a cover, "
        f"{s['identity_review']} to review), title IDs {s['titles']}, "
        f"open blockers {s['blockers_open']} ({s['blockers_ranked']} ranked), wrote {out}"
    )
    return 0
