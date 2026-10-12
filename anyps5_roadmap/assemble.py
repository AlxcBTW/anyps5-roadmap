"""Assemble roadmap.json: focus areas, help wanted, stats, gaps and sources."""

from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from typing import TYPE_CHECKING

from .config import (
    ARCHIVE_URL,
    PM4_HEADER,
    PM4_SOURCE,
    PROGRESS_URL,
    PROJECT_REPO,
    SCHEMA_VERSION,
    STAGE_HELP,
    STAGES,
    WINDOW_DAYS,
)

if TYPE_CHECKING:  # used in annotations only
    from .model import Model
    from .upstream import Upstream


AREA_NAMES = {
    "shader": "Shader recompiler",
    "agc": "AGC driver",
    "libkernel": "libkernel",
    "libc": "libc",
    "relinker": "Relinker",
    "prx": "HLE libraries",
}


def focus_areas(model: Model, ranking: list[dict]) -> dict:
    by_area: dict = defaultdict(
        lambda: {"score": 0, "blockers": [], "titles": set(), "frontier_titles": set(), "open_prs": 0}
    )
    for b in ranking:
        if b["score"] <= 0:
            continue
        a = by_area[b["area"]]
        a["score"] += b["score"]
        a["blockers"].append(b["id"])
        a["titles"].update(b["titles"])
        a["frontier_titles"].update(b["frontier_titles"])
        a["open_prs"] += sum(
            1 for p in b["prs"] if p["state"] in ("open", "draft") and p["link"] in ("fixes", "related")
        )
    areas = []
    for area, a in sorted(((k, v) for k, v in by_area.items() if k), key=lambda kv: -kv[1]["score"])[:5]:
        areas.append(
            {
                "area": area,
                "name": AREA_NAMES.get(area, area),
                "score": a["score"],
                "blockers": a["blockers"][:4],
                "blocker_count": len(a["blockers"]),
                "titles": len(a["titles"]),
                "frontier_titles": len(a["frontier_titles"]),
                "open_fix_prs": a["open_prs"],
            }
        )
    help_wanted = []
    for b in ranking:
        has_fix = any(p["state"] in ("open", "draft") and p["link"] in ("fixes", "related") for p in b["prs"])
        reason = None
        if b.get("help_wanted"):
            reason = b["help_wanted"]
        elif "help wanted" in b["labels"] or "good first issue" in b["labels"]:
            reason = "Labelled " + ", ".join(lb for lb in b["labels"] if lb in ("help wanted", "good first issue"))
        elif b["frontier"] > 0 and not has_fix:
            reason = f"First open blocker for {b['frontier']} title{'s' if b['frontier'] != 1 else ''}; no open fix PR"
        if reason:
            help_wanted.append({"blocker": b["id"], "reason": reason})
    return {"areas": areas, "help_wanted": help_wanted[:12]}


def assemble(model: Model, coverage: dict, raw: dict, upstream: Upstream, now: dt.datetime) -> dict:
    ranking = model.ranking()
    focus = focus_areas(model, ranking)
    titles = []
    for tid, t in sorted(model.titles.items()):
        best = model.best_stage(t)
        last = max(
            t["mentions"] + [{"url": e["url"], "date": e["date"]} for e in t["evidence"] if e.get("date")],
            key=lambda m: m["date"] or "",
            default=None,
        )
        titles.append(
            {
                "id": tid,
                "name": t["name"],
                "engine": t["engine"],
                "kind": t["kind"],
                "curated": t["curated"],
                "best_stage": best,
                "unverified_claim": model.unverified_claim(t),
                "stage_reviews": t.get("reviews", []),
                "evidence": sorted(t["evidence"], key=lambda e: (-STAGES.index(e["stage"]), e.get("date") or ""))[:12],
                "open_blockers": [
                    {"id": s["blocker"], "origin": s["origin"], "why": s["why"], "scope": s.get("scope")}
                    for s in t["open_chain"]
                ],
                "resolved_blockers": [
                    s["blocker"] for s in t["chain"] if model.blockers[s["blocker"]]["status"] != "open"
                ],
                "issues": sorted({m["number"] for m in t["mentions"] if m["kind"] == "issue"}),
                "prs": sorted({m["number"] for m in t["mentions"] if m["kind"] == "pr"}),
                "last_evidence": last,
                "confidence": model.confidence(t),
            }
        )
    blockers = []
    for b in sorted(model.blockers.values(), key=lambda b: (b["status"] != "open", -b["score"], -(b["issue"] or 0))):
        blockers.append({k: v for k, v in b.items() if k != "signature_key"})
    rl = raw.get("rate_limit", {})
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fetched_at": raw.get("fetched_at"),
        "upstream": {"repo": model.repo, "ref": upstream.ref, "commit": upstream.commit},
        "project": {
            "repo": PROJECT_REPO,
            "corrections": f"https://github.com/{PROJECT_REPO}/issues/new/choose",
            "issue_forms": ["wrong-stage.yml", "blocker.yml", "mining-bug.yml"],
        },
        "window": {"days": WINDOW_DAYS, "since": raw.get("cutoff")},
        "stages": [{"name": s, "rank": i, "meaning": STAGE_HELP[s]} for i, s in enumerate(STAGES)],
        "scoring": {
            "formula": "3*one_fix_away + 2*frontier + total",
            "frontier": "titles for which this is the earliest open blocker on at least one OS/GPU path",
            "one_fix_away": "titles for which this is the only open blocker on at least one path",
            "total": "titles that list this blocker anywhere in their open chain",
            "excluded": "titles whose best stage is Playable count only towards total",
        },
        "stats": {
            "issues_scanned": len(raw["issues"]),
            "issues_open": sum(1 for i in raw["issues"] if i["state"] == "OPEN"),
            "prs_scanned": len(raw["prs"]),
            "titles": len(titles),
            "titles_with_open_blockers": sum(1 for t in titles if t["open_blockers"]),
            "titles_with_stage": sum(1 for t in titles if t["best_stage"]),
            "titles_with_unverified_claim": sum(1 for t in titles if t["unverified_claim"]),
            "stage_reviews": sum(len(t["stage_reviews"]) for t in titles),
            "blockers_open": sum(1 for b in blockers if b["status"] == "open"),
            "blockers_ranked": sum(1 for b in blockers if b["status"] == "open" and b["score"] > 0),
            "blockers_curated": sum(1 for b in blockers if b["origin"] == "curated"),
            "rate_limit": rl,
            "api": raw.get("api"),
            "evidence_items": sum(len(t["evidence"]) for t in model.titles.values()),
            "evidence_by_part": dict(
                sorted(
                    Counter(e.get("part") or e["origin"] for t in model.titles.values() for e in t["evidence"]).items()
                )
            ),
            "stops_from_log_blocks": sum(
                1 for t in model.titles.values() for s in t["stops"] if s.get("via") == "log block"
            ),
            "titles_with_two_or_more_reports": sum(1 for t in titles if (t["confidence"]["reports_on_main"] or 0) >= 2),
            "links": link_stats(model),
        },
        "ranking": [b["id"] for b in ranking],
        "blockers": blockers,
        "titles": titles,
        "coverage": coverage,
        "focus": focus,
        "not_blockers": [{"issue": n, "reason": r} for n, r in sorted(model.not_blockers.items())],
        "gaps": model.gaps + [f"Not read in full: {t}." for t in raw.get("truncated", [])][:5] + KNOWN_GAPS,
        "sources": {
            "issues_and_prs": f"https://github.com/{model.repo} via gh api graphql (open + closed in the last {WINDOW_DAYS} days)",
            "dependencies": f"/repos/{model.repo}/issues/{{n}}/dependencies/blocked_by",
            "curated": "data/blockers.json",
            "progress": PROGRESS_URL,
            "pm4": f"{PM4_HEADER} (raw, main) + {PM4_SOURCE} at {upstream.ref}",
            "compatibility": ARCHIVE_URL,
        },
    }


def link_stats(model: Model) -> dict:
    """Issue-to-PR links by how they are known: closing references, timeline cross-references, PR text."""
    vias = [v for per_issue in model.link_via.values() for v in per_issue.values()]
    return {
        "total": len(vias),
        "closing": sum(1 for v in vias if "closing" in v),
        "xref": sum(1 for v in vias if "xref" in v),
        "text": sum(1 for v in vias if "text" in v),
        "text_only": sum(1 for v in vias if v == {"text"}),
    }


KNOWN_GAPS = [
    "Title names, engines and stages are mined with keyword rules per line; negation and context are handled only roughly.",
    "Mined chain order is a heuristic: the latest recorded stop first, then issues by creation date.",
    "Read: issue and PR bodies, their comments, PR reviews and review-thread comments (up to 100 threads and 50 comments "
    "per thread), and timeline cross-references. Not read: commit messages, diffs, attached logs and screenshots "
    "(images, gists, uploaded files), edit history, and bot comments.",
    "Issues and PRs closed more than 60 days ago are not read, even when they hold the last report on a title.",
    "Stops are read from a fenced log only when the comment names exactly one title ID; the last error line in the "
    "block counts as the stop.",
    "“N reports on main” counts distinct GitHub accounts whose text puts the title at that stage on main. It cannot "
    "tell whether two accounts tested the same build, and text without a stated build counts as main in issues and as "
    "the PR branch in PRs.",
    "Titles without a PPSA ID (some homebrew) appear only when curated.",
    "Discord reports are invisible unless someone copies them into GitHub or the curated file.",
    "Signatures are matched by prefix after hex addresses and long numbers are masked; reworded messages split into separate keys.",
    "PM4 status reads Pm4::UnsupportedReason(); a packet can pass that check and still be handled only partly.",
    "Stages mined from PR text describe the PR branch (build “PR #N”), not main, unless the sentence says main and "
    "names no patches.",
    "An issue that names seven or more titles is treated as a tracker: only its per-title stop rows count, as separate blockers.",
    "HLE “named in issues” counts any mention of a missing function, including lists of imports that were never reached.",
    "A mined stage of Menus or higher is only a claim until a person reviews it; most such claims in PR text were made on branches with open PRs.",
]
