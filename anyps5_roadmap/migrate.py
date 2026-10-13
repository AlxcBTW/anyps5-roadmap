"""The game identity migration report: what moving from one row per title ID to one entity per game did.

    python -m anyps5_roadmap.migrate --before old/roadmap.json --after build/site/roadmap.json --out report.md

`--before` is a roadmap.json of schema 1 (titles only, grouped by exact name on the page), `--after` one of
schema 2. The report lists every merge with the title IDs, the names they had and the reasons, every title
whose name changed, every game whose stage changed and why, and the review list, so nothing merges silently.
It reads two files and writes one; it changes no data.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import STAGES


def _listed(t: dict) -> bool:
    return bool(t.get("best_stage") or t.get("open_blockers") or t.get("unverified_claim"))


def _stage(rec: dict | None) -> str | None:
    if not rec:
        return None
    best = rec.get("stage") if "stage" in rec and isinstance(rec.get("stage"), dict) else rec.get("best_stage")
    return (best or {}).get("stage")


def _rank(stage: str | None) -> int:
    return STAGES.index(stage) if stage in STAGES else -1


def _n(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def _cell(text) -> str:
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ")


def before_games(before: dict) -> dict[str, dict]:
    """The page's games before: listed title IDs grouped by exact name, each at its best title's stage."""
    out: dict[str, dict] = {}
    for t in before["titles"]:
        if not _listed(t):
            continue
        name = t.get("name") or t["id"]
        g = out.setdefault(name, {"name": name, "ids": [], "stage": None})
        g["ids"].append(t["id"])
        s = _stage(t)
        if _rank(s) > _rank(g["stage"]):
            g["stage"] = s
    return out


def report(before: dict, after: dict) -> str:
    old_titles = {t["id"]: t for t in before["titles"]}
    old_games = before_games(before)
    games = after["games"]
    shown = [
        g
        for g in games
        if g.get("stage") or g.get("open_blockers") or g.get("unverified_claim") or g.get("stage_on_branches")
    ]
    ident = after["identity"]
    old_rows = sum(len(g["ids"]) for g in old_games.values())
    folded = sum(len(g["title_ids"]) - 1 for g in shown)
    lines = [
        "# Game identity migration",
        "",
        f"Before: roadmap.json of {before.get('generated_at')} (schema {before.get('schema_version')}). "
        f"After: roadmap.json of {after.get('generated_at')} (schema {after.get('schema_version')}), built from the "
        f"API snapshot of {after.get('fetched_at')}.",
        "",
        "Until now each title ID was its own entry and the page put two IDs together only when their names were "
        "spelled exactly alike, so \u201cGTA V\u201d and \u201cGrand Theft Auto V\u201d were two games. Now a game is one entity "
        "with all of its title IDs and aliases; how title IDs are matched is in [CONTEXT.md](../../CONTEXT.md) and "
        "`anyps5_roadmap/identity.py`. This report lists every merge, every renamed title, every game whose stage "
        "changed, and what is left for a person to decide.",
        "",
        "## Counts",
        "",
        "| | Before | After |",
        "|---|---:|---:|",
        f"| Games on the page | {len(old_games)} | {len(shown)} |",
        f"| Title IDs behind them | {old_rows} | {sum(len(g['title_ids']) for g in shown)} |",
        f"| Games with more than one title ID | {sum(1 for g in old_games.values() if len(g['ids']) > 1)} | "
        f"{sum(1 for g in shown if len(g['title_ids']) > 1)} |",
        f"| Title IDs folded into another game | {old_rows - len(old_games)} | {folded} |",
        f"| Matches waiting for review | | {len(ident['review'])} |",
        "",
    ]

    # merges
    lines += ["## Merges", "", f"{_n(len(ident['merges']), 'game holds', 'games hold')} more than one title ID.", ""]
    lines += ["| Game | Title IDs | Names before | Why |", "|---|---|---|---|"]
    by_game = {g["id"]: g for g in games}
    for m in sorted(ident["merges"], key=lambda m: (m["name"] or "").lower()):
        g = by_game.get(m["game"], {})
        regions = {t["id"]: t.get("region") for t in g.get("titles", [])}
        ids = ", ".join(f"`{t}`" + (f" ({regions[t]})" if regions.get(t) else "") for t in m["title_ids"])
        was = "; ".join(
            f"`{t}`: {old_titles[t].get('name') or '(no name)'}" if t in old_titles else f"`{t}`: (new)"
            for t in m["title_ids"]
        )
        lines.append(f"| {_cell(m['name'])} | {ids} | {_cell(was)} | {_cell('; '.join(m['reasons']))} |")
    lines.append("")

    # renames
    renamed = []
    for g in games:
        for t in g.get("titles", []):
            old = old_titles.get(t["id"])
            if old and _listed(old) and (old.get("name") or None) != g["name"]:
                renamed.append((t["id"], old.get("name"), g["name"], g.get("name_origin")))
    origin = {"store": "PlayStation title list", "curated": "data/games.json or data/blockers.json", "mined": "reports"}
    lines += [
        "## Renamed titles",
        "",
        f"{_n(len(renamed), 'listed title ID shows', 'listed title IDs show')} another name now: the store's own name "
        "for the ID, the name of the game it joined, or a correction of a mis-read name.",
        "",
        "| Title ID | Before | After | Name from |",
        "|---|---|---|---|",
    ]
    for tid, was, now, src in sorted(renamed, key=lambda r: (r[2] or "").lower()):
        lines.append(f"| `{tid}` | {_cell(was or '(no name)')} | {_cell(now)} | {origin.get(src, src or '')} |")
    lines.append("")

    # stage changes by game: each title ID's own stage before, the game's stage after
    changes = []
    for g in shown:
        was = max((_stage(old_titles.get(t)) for t in g["title_ids"]), key=_rank, default=None)
        now = _stage(g)
        if was != now and any(t in old_titles for t in g["title_ids"]):
            if _rank(now) < _rank(was):
                why = "the higher stage was reported only off main (open PRs or patches)"
                off, claim = g.get("stage_on_branches") or {}, g.get("unverified_claim") or {}
                if off.get("stage"):
                    needs = ", ".join(f"#{n}" for n in off.get("needs") or [])
                    why += f"; stage off main now: {off['stage']}" + (f" with {needs}" if needs else "")
                    why += " + patches" if off.get("patches") else ""
                elif claim.get("stage"):
                    why += f"; a claim of {claim['stage']} on main waits for review"
            elif len(g["title_ids"]) > 1:
                why = "the reports of all of its title IDs count together"
            else:
                why = "a newer report, or a report from a discussion"
            changes.append((g["name"] or g["id"], was, now, why))
    lines += [
        "## Stage changes",
        "",
        f"{_n(len(changes), 'game shows', 'games show')} another stage. Stages count only on main, or on main plus PRs that are merged "
        "now, as the README and AGENTS.md always said; the old build counted any mined stage below Menus. A stage seen "
        "only on a PR branch, a stack of open PRs or local patches now shows apart, as the stage off main, with the PRs "
        "it needs, and moves up by itself once they are merged.",
        "",
        "| Game | Before | After | Why |",
        "|---|---|---|---|",
    ]
    for name, was, now, why in sorted(changes, key=lambda c: c[0].lower()):
        lines.append(f"| {_cell(name)} | {was or 'no stage'} | {now or 'no stage'} | {why} |")
    lines.append("")

    # review
    lines += [
        "## Waiting for review",
        "",
        "Never merged by themselves. Settle one by listing the title IDs together in `data/games.json` (with a "
        "source), or keep them apart with a `distinct` entry.",
        "",
        "| Kind | Names | Title IDs | Note |",
        "|---|---|---|---|",
    ]
    for r in ident["review"]:
        lines.append(
            f"| {r['kind']} | {_cell(' / '.join(n or '' for n in r['names']))} | "
            f"{', '.join(f'`{t}`' for t in r['title_ids'])} | {_cell(r['note'])} |"
        )
    if ident.get("placeholders"):
        lines += ["", f"Placeholder IDs skipped: {', '.join(f'`{t}`' for t in ident['placeholders'])}."]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--before", required=True, help="roadmap.json of schema 1")
    ap.add_argument("--after", required=True, help="roadmap.json of schema 2")
    ap.add_argument("--out", help="write the report here instead of printing it")
    args = ap.parse_args(argv)
    before = json.loads(Path(args.before).read_text(encoding="utf-8"))
    after = json.loads(Path(args.after).read_text(encoding="utf-8"))
    text = report(before, after)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8", newline="\n")
    else:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
