"""PR preview: what a change does to the ranking, the titles and their stages.

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
    ("titles", "Title IDs"),
    ("titles_with_stage", "Title IDs with a verified stage"),
    ("titles_with_unverified_claim", "Unverified claims"),
    ("stage_reviews", "Stage reviews"),
    ("blockers_open", "Open blockers"),
    ("blockers_ranked", "Ranked blockers (block at least one title)"),
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
    best = t.get("best_stage")
    if not best:
        return "—"
    return f"{best['stage']} ({best.get('origin', '?')})"


def step_ref(bid: str) -> str:
    return f"#{bid}" if bid.isdigit() else bid


def title_view(t: dict) -> dict:
    claim = t.get("unverified_claim") or {}
    steps = [step_ref(s["id"]) for s in t.get("open_blockers") or []]
    return {
        "stage": stage_text(t),
        "claim": claim.get("stage") or "—",
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


def ranking_changes(base: dict, head: dict) -> list[str]:
    old = {b["id"]: (n, b) for n, b in enumerate(ranked(base), 1)}
    new = ranked(head)
    rows = []
    for n, b in enumerate(new[:TOP], 1):
        if b["id"] not in old:
            change = "new"
        else:
            was, ob = old[b["id"]]
            parts = []
            if was != n:
                parts.append(f"{'▲' if was > n else '▼'}{abs(was - n)} (was {was})")
            if ob.get("score") != b.get("score"):
                parts.append(f"score {ob.get('score')} → {b.get('score')}")
            change = ", ".join(parts)
        rows.append((n, b, change))
    top_new = {b["id"] for b in new[:TOP]}
    dropped = [(n, b) for n, b in old.values() if n <= TOP and b["id"] not in top_new]
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


def title_changes(base: dict, head: dict) -> list[str]:
    old = {t["id"]: t for t in base["titles"]}
    new = {t["id"]: t for t in head["titles"]}
    rows = []
    for tid in sorted(set(old) | set(new)):
        a = title_view(old[tid]) if tid in old else None
        b = title_view(new[tid]) if tid in new else None
        if a == b:
            continue
        name = (new.get(tid) or old.get(tid) or {}).get("name") or ""
        if a is None or b is None:
            note = "added" if a is None else "removed"
            view = b or a
            rows.append(
                f"| `{tid}` {cell(name)} ({note}) | {view['stage']} | {view['claim']} | {cell(view['chain'])} | "
                f"{view['reports']} |"
            )
            continue

        def diff(key, a=a, b=b):
            return cell(b[key]) if a[key] == b[key] else f"{cell(a[key])} → **{cell(b[key])}**"

        rows.append(
            f"| `{tid}` {cell(name)} | {diff('stage')} | {diff('claim')} | {diff('chain')} | {diff('reports')} |"
        )
    if not rows:
        return []
    head_row = "| Title | Verified stage | Unverified claim | Open blockers, in order | Reports on main |"
    return [f"### Titles that change ({len(rows)})", "", head_row, "|---|---|---|---|---|", *rows, ""]


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
    titles = title_changes(base, head)
    diff = markdown_diff(base_dir, head_dir)
    if not (ranking or titles or diff) and base["stats"] == head["stats"]:
        out += ["No change to the ranking, the titles, their stages or their blocker chains.", ""]
    out += stats_table(base, head) + [""] + ranking + titles + diff
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
