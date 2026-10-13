"""PR preview: what a change does to the ranking, the games, their stages and which title IDs are one game.

CI builds the base branch and the PR head from the same API snapshot and writes this
comparison to the job summary, so a reviewer sees the effect of a data or rule change
without running anything:

    python -m anyps5_roadmap.preview build/base build/head --snapshot "API snapshot of 2026-10-10"

Each directory holds a built site (roadmap.json and ROADMAP.md). Prints Markdown.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

TOP = 15
MAX_DIFF_LINES = 400
STATS = [
    ("games", "Games"),
    ("titles", "Title IDs"),
    ("title_ids_folded", "Title IDs folded into another game"),
    ("games_with_stage", "Games with a stage"),
    ("games_verified", "Games checked by hand"),
    ("games_with_claim", "Unverified claims"),
    ("identity_review", "Possible duplicates to review"),
    ("games_with_image", "Games with a picture"),
    ("stage_reviews", "Stage reviews"),
    ("blockers_open", "Open blockers"),
    ("blockers_ranked", "Ranked blockers (stop at least one game)"),
    ("blockers_curated", "Curated blockers"),
]
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def load(site: Path) -> dict | None:
    path = site / "roadmap.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def cell(text) -> str:
    return str(text if text not in (None, "") else "—").replace("|", "\\|").replace("\n", " ")


def blocker_label(b: dict) -> str:
    ref = f"#{b['issue']}" if b.get("issue") else b["id"]
    return f"{ref} {b.get('title') or ''}".strip()


def ranked(doc: dict) -> list[dict]:
    by_id = {b["id"]: b for b in doc["blockers"]}
    return [by_id[i] for i in doc["ranking"] if i in by_id and by_id[i].get("score", 0) > 0]


def stage_text(t: dict) -> str:
    best = t.get("stage") if "stage" in t else t.get("best_stage")
    if not best:
        return "—"
    return f"{best['stage']} ({best.get('origin', '?')})"


def step_ref(bid: str) -> str:
    return f"#{bid}" if bid.isdigit() else bid


def title_view(t: dict) -> dict:
    claim = t.get("unverified_claim") or {}
    branch = t.get("stage_on_branches") or {}
    steps = [step_ref(s["id"]) for s in t.get("open_blockers") or []]
    needs = " ".join(f"#{n}" for n in branch.get("needs") or [])
    return {
        "stage": stage_text(t),
        "claim": claim.get("stage") or "—",
        "branch": f"{branch['stage']}{' with ' + needs if needs else ''}{' + patches' if branch.get('patches') else ''}"
        if branch
        else "—",
        "chain": " → ".join(steps[:4]) + (f" (+{len(steps) - 4})" if len(steps) > 4 else "") if steps else "—",
        "reports": (t.get("confidence") or {}).get("label") or "—",
    }


def stats_table(base: dict, head: dict) -> list[str]:
    rows = ["| | Base | This PR |", "|---|--:|--:|"]
    for key, label in STATS:
        a, b = base["stats"].get(key), head["stats"].get(key)
        mark = f"**{b}**" if a != b else str(b)
        rows.append(f"| {label} | {a} | {mark} |")
    return rows


def rank_moves(base: dict, head: dict) -> list[dict]:
    """Every blocker ranked in either build, with its place and score in both (None where it is not ranked).

    The head's ranking comes first, in order, then the blockers only the base ranks, in the base's order.
    `blocker` is the head's entry when there is one, `old` the base's. The PR preview and the change feed
    (feed.py) both read the ranking through this."""
    old = {b["id"]: (n, b) for n, b in enumerate(ranked(base), 1)}
    moves = []
    for n, b in enumerate(ranked(head), 1):
        was, ob = old.pop(b["id"], (None, None))
        moves.append(
            {
                "blocker": b,
                "old": ob,
                "rank": n,
                "was": was,
                "score": b.get("score"),
                "was_score": (ob or {}).get("score"),
            }
        )
    for was, ob in old.values():
        moves.append({"blocker": ob, "old": ob, "rank": None, "was": was, "score": None, "was_score": ob.get("score")})
    return moves


def ranking_changes(base: dict, head: dict) -> list[str]:
    moves = rank_moves(base, head)
    rows = []
    for m in moves:
        n, was, b = m["rank"], m["was"], m["blocker"]
        if n is None or n > TOP:
            continue
        if was is None:
            change = "new"
        else:
            parts = []
            if was != n:
                parts.append(f"{'▲' if was > n else '▼'}{abs(was - n)} (was {was})")
            if m["was_score"] != m["score"]:
                parts.append(f"score {m['was_score']} → {m['score']}")
            change = ", ".join(parts)
        rows.append((n, b, change))
    dropped = sorted(
        (
            (m["was"], m["old"])
            for m in moves
            if m["was"] is not None and m["was"] <= TOP and (m["rank"] or TOP + 1) > TOP
        ),
        key=lambda wb: wb[0],
    )
    if not any(change for _, _, change in rows) and not dropped:
        return []
    out = [f"### Ranking, top {TOP}", "", "| # | Blocker | Score | Change |", "|--:|---|--:|---|"]
    out += [f"| {n} | {cell(blocker_label(b))} | {b.get('score')} | {cell(change)} |" for n, b, change in rows]
    if dropped:
        out += [
            "",
            "Left the top " + str(TOP) + ": " + ", ".join(f"{cell(blocker_label(b))} (was {n})" for n, b in dropped),
        ]
    return out + [""]


def game_records(doc: dict, layout: dict) -> dict[str, dict]:
    """The games of `layout` (the PR head) as `doc` saw them: its own game records, or for a build from before
    games existed, the title ID of each game that went furthest then."""
    if doc.get("games") is not None:
        by_title = {t: g for g in doc["games"] for t in g["title_ids"]}
        return {
            g["id"]: next((by_title[t] for t in g["title_ids"] if t in by_title), None) for g in layout.get("games", [])
        }
    titles = {t["id"]: t for t in doc["titles"]}
    out = {}
    for g in layout.get("games", []):
        members = [titles[t] for t in g["title_ids"] if t in titles]
        out[g["id"]] = max(members, key=lambda t: (stage_rank(t), bool(t.get("open_blockers"))), default=None)
    return out


def stage_rank(t: dict) -> int:
    order = ["Converts", "Loads", "Starts", "First draw", "Presents", "Menus", "Ingame", "Playable"]
    best = t.get("stage") if "stage" in t else t.get("best_stage")
    return order.index(best["stage"]) if best and best.get("stage") in order else -1


def listed(g: dict | None) -> bool:
    return bool(
        g
        and (
            g.get("stage")
            or g.get("best_stage")
            or g.get("open_blockers")
            or g.get("unverified_claim")
            or g.get("stage_on_branches")
        )
    )


def game_changes(base: dict, head: dict) -> list[str]:
    old = game_records(base, head)
    rows = []
    for g in sorted(head.get("games", []), key=lambda g: ((g.get("name") or g["id"]).lower(), g["id"])):
        was = old.get(g["id"])
        if not listed(g) and not listed(was):
            continue
        a = title_view(was) if was else None
        b = title_view(g) if listed(g) else None
        if a == b:
            continue
        ids = ", ".join(f"`{t}`" for t in g["title_ids"])
        if a is None or b is None:
            note = "added" if a is None else "removed"
            view = b or a
            rows.append(
                f"| {cell(g.get('name'))} {ids} ({note}) | {view['stage']} | {view['claim']} | {cell(view['branch'])} | "
                f"{cell(view['chain'])} | {view['reports']} |"
            )
            continue

        def diff(key, a=a, b=b):
            return cell(b[key]) if a[key] == b[key] else f"{cell(a[key])} → **{cell(b[key])}**"

        rows.append(
            f"| {cell(g.get('name'))} {ids} | {diff('stage')} | {diff('claim')} | {diff('branch')} | {diff('chain')} | "
            f"{diff('reports')} |"
        )
    if not rows:
        return []
    head_row = (
        "| Game | Stage | Unverified claim | Off main (open PRs, patches) | Open blockers, in order | Reports on main |"
    )
    return [f"### Games that change ({len(rows)})", "", head_row, "|---|---|---|---|---|---|", *rows, ""]


def identity_changes(base: dict, head: dict) -> list[str]:
    """Merges and review items this PR adds or removes, so no title ID joins a game unseen."""

    def merges(doc):
        if doc.get("identity") is None:
            by_name: dict[str, set] = {}
            for t in doc["titles"]:
                if t.get("name"):
                    by_name.setdefault(t["name"], set()).add(t["id"])
            return {frozenset(ids): {"name": n, "reasons": ["same name"]} for n, ids in by_name.items() if len(ids) > 1}
        return {frozenset(m["title_ids"]): m for m in doc["identity"].get("merges", [])}

    def review(doc):
        return {frozenset(r["title_ids"]): r for r in (doc.get("identity") or {}).get("review", [])}

    a, b = merges(base), merges(head)
    added = [b[k] for k in b if k not in a]
    removed = [a[k] for k in a if k not in b]
    ra, rb = review(base), review(head)
    new_review = [rb[k] for k in rb if k not in ra]
    if not (added or removed or new_review):
        return []
    out = ["### Game identity", ""]
    if added or removed:
        out += ["| Game | Title IDs | Change | Why |", "|---|---|---|---|"]
        for m, what in [(m, "merged") for m in added] + [(m, "no longer merged") for m in removed]:
            ids = ", ".join(f"`{t}`" for t in sorted(m.get("title_ids") or []))
            out.append(f"| {cell(m.get('name'))} | {ids} | {what} | {cell('; '.join(m.get('reasons') or []))} |")
        out.append("")
    if new_review:
        out += [f"New matches waiting for review ({len(new_review)}), never merged by themselves:", ""]
        out += [
            f"- {r['kind']}: {' / '.join(n or '' for n in r['names'])} ({', '.join(r['title_ids'])})"
            for r in new_review
        ]
        out.append("")
    return out


def markdown_diff(base_dir: Path, head_dir: Path) -> list[str]:
    a = base_dir / "ROADMAP.md"
    b = head_dir / "ROADMAP.md"
    if not (a.exists() and b.exists()):
        return []
    old = [TIMESTAMP.sub("…", line) for line in a.read_text(encoding="utf-8").splitlines()]
    new = [TIMESTAMP.sub("…", line) for line in b.read_text(encoding="utf-8").splitlines()]
    lines = list(difflib.unified_diff(old, new, "base/ROADMAP.md", "head/ROADMAP.md", n=0, lineterm=""))
    if not lines:
        return []
    shown = lines[:MAX_DIFF_LINES]
    more = f"\n… {len(lines) - MAX_DIFF_LINES} more lines" if len(lines) > MAX_DIFF_LINES else ""
    return [
        f"<details><summary>ROADMAP.md diff ({len(lines)} lines)</summary>",
        "",
        "```diff",
        *shown,
        "```" + more,
        "",
        "</details>",
        "",
    ]


def render(base_dir: Path, head_dir: Path, snapshot: str | None = None) -> str:
    head = load(head_dir)
    if head is None:
        return "## Blocker map preview\n\nThe PR head did not build, so there is nothing to compare. See the job log.\n"
    out = ["## Blocker map preview", ""]
    if snapshot:
        out += [f"Base and this PR, both built from {snapshot}.", ""]
    base = load(base_dir)
    if base is None:
        out += ["The base branch could not be built from the same snapshot, so only this PR's numbers are shown.", ""]
        out += ["| | This PR |", "|---|--:|"] + [f"| {label} | {head['stats'].get(key)} |" for key, label in STATS]
        return "\n".join(out) + "\n"
    ranking = ranking_changes(base, head)
    identity = identity_changes(base, head)
    games = game_changes(base, head)
    diff = markdown_diff(base_dir, head_dir)
    if not (ranking or identity or games or diff) and base["stats"] == head["stats"]:
        out += ["No change to the ranking, the games, their stages or their blocker chains.", ""]
    out += stats_table(base, head) + [""] + ranking + identity + games + diff
    out += ["The built site of this PR is attached to the workflow run as the `site-preview` artifact.", ""]
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Compare two built sites and print a Markdown summary.")
    ap.add_argument("base", type=Path, help="site built from the base branch")
    ap.add_argument("head", type=Path, help="site built from the PR head")
    ap.add_argument("--snapshot", help="where the API data came from, for the first line")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(render(args.base, args.head, args.snapshot))
    return 0


if __name__ == "__main__":
    sys.exit(main())
