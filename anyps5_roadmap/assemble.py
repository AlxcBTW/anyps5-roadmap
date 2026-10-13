"""Assemble roadmap.json: focus areas, help wanted, stats, gaps and sources."""

from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from typing import TYPE_CHECKING

from . import evaluate
from .config import (
    ARCHIVE_URL,
    CATALOG_URL,
    PM4_HEADER,
    PM4_SOURCE,
    PROGRESS_URL,
    PROJECT_REPO,
    SCHEMA_VERSION,
    STAGE_HELP,
    STAGES,
    TAG_GROUPS,
    TAG_HELP,
    TAGS,
    WINDOW_DAYS,
)
from .identity import CATALOG_SOURCE, CONCEPT_URL, REGIONS
from .images import image_for

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
        a["titles"].update(b["games"])
        a["frontier_titles"].update(b["frontier_games"])
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
            reason = f"First open blocker for {b['frontier']} game{'s' if b['frontier'] != 1 else ''}; no open fix PR"
        if reason:
            help_wanted.append({"blocker": b["id"], "reason": reason})
    return {"areas": areas, "help_wanted": help_wanted[:12]}


def _id_order(tid: str) -> tuple:
    return (not tid.startswith("PPSA"), tid)


def listed(rec: dict) -> bool:
    """A title or game is on the page when it has a stage, an open stop, a claim or a stage on branches."""
    stage = rec.get("best_stage") if "best_stage" in rec else rec.get("stage")
    return bool(stage or rec.get("open_blockers") or rec.get("unverified_claim") or rec.get("stage_on_branches"))


def game_records(model: Model, images: dict | None = None) -> list[dict]:
    """One record per game: its title IDs and names, and the evidence of all of them evaluated together."""
    out = []
    for gid, g in sorted(model.identity.games.items()):
        ordered = model.members(gid)  # the leading title ID first
        members = sorted(ordered, key=lambda t: _id_order(t["id"]))
        primary = ordered[0] if ordered else None
        evidence = evaluate.dedupe([{**e, "title": t["id"]} for t in members for e in t["evidence"]])
        best = evaluate.best_stage(evidence, model.merged)
        claim = evaluate.unverified_claim(evidence, best, model.merged)
        conf = evaluate.confidence(evidence, model.merged, best, claim)
        branch = evaluate.branch_stage(evidence, model.merged, best, claim)
        own_best = {t["id"]: model.best_stage(t) for t in members}
        chain = [
            {"id": s["blocker"], "origin": s["origin"], "why": s["why"], "scope": s.get("scope"), "title": s["title"]}
            for s in model.game_chain(gid)
            if model.blockers[s["blocker"]]["status"] == "open"
        ]
        resolved = [s["blocker"] for s in model.game_chain(gid) if model.blockers[s["blocker"]]["status"] != "open"]
        tags = [tag for tag in TAGS if any(tag in t["tags"] for t in members)]
        sources = list(dict.fromkeys(src for t in members for src in t["tag_sources"]))
        mentions = [m for t in members for m in t["mentions"]]
        last = max(
            mentions + [{"url": e["url"], "date": e.get("date")} for e in evidence if e.get("date")],
            key=lambda m: m.get("date") or "",
            default=None,
        )
        kinds = [t["kind"] for t in members if t["kind"]]
        cg = g.curated or {}
        concept = g.concepts[0] if g.concepts else None
        store_url = CONCEPT_URL.format(concept) if concept else None
        out.append(
            {
                "id": gid,
                "name": g.name,
                "name_origin": g.name_origin,
                "name_sources": cg.get("sources") or ([store_url] if g.name_origin == "store" and store_url else []),
                "aliases": g.aliases,
                "title_ids": [t["id"] for t in members],
                "titles": [
                    {
                        "id": t["id"],
                        "name": t["name"],
                        "region": REGIONS.get(t.get("region") or "", t.get("region")),
                        "platform": "PS4" if t["id"].startswith("CUSA") else "PS5",
                        "content_id": t.get("content_id"),
                        "stage": (own_best[t["id"]] or {}).get("stage"),
                    }
                    for t in members
                ],
                "primary": primary["id"] if primary else None,
                "store_url": store_url,
                "kind": cg.get("kind")
                or next((t["kind"] for t in ordered if t["curated"] and t["kind"]), None)
                or ("retail" if g.concepts else (Counter(kinds).most_common(1)[0][0] if kinds else None)),
                "engine": next((t["engine"] for t in ordered if t["engine"]), None),
                "tags": tags,
                "tag_sources": sources,
                "curated": bool(g.curated) or any(t["curated"] for t in members),
                "image": image_for(g.concepts, g.curated, images or {}),
                "stage": best,
                "confidence": conf,
                "unverified_claim": claim,
                "stage_on_branches": branch,
                "timeline": evaluate.timeline(evidence, model.merged),
                "stage_reviews": [{**rv, "title": t["id"]} for t in members for rv in t.get("reviews", [])],
                "evidence": sorted(evidence, key=lambda e: (-STAGES.index(e["stage"]), e.get("date") or ""))[:12],
                "evidence_count": len(evidence),
                "open_blockers": chain,
                "resolved_blockers": resolved,
                "issues": sorted({m["number"] for m in mentions if m["kind"] == "issue"}),
                "prs": sorted({m["number"] for m in mentions if m["kind"] == "pr"}),
                "discussions": sorted({m["number"] for m in mentions if m["kind"] == "discussion"}),
                "last_evidence": last,
            }
        )
    return out


def identity_section(model: Model, catalog_info: dict | None) -> dict:
    ident = model.identity
    return {
        "merges": ident.merges,
        "review": ident.review,
        "placeholders": sorted(model.placeholders),
        "catalog": catalog_info or {"source": CATALOG_SOURCE, "titles": len(model.catalog)},
        "rules": (
            "Title IDs are one game when data/games.json lists them together, when the PlayStation title list puts "
            "them under one store concept, or when their names agree after normalising case, symbols, punctuation, "
            "accents, a leading The, region, platform and edition suffixes, roman numerals and known abbreviations, "
            "and both names are trusted (curated or from the store) or both are mined. Anything weaker is listed "
            "under review and never merged by itself."
        ),
    }


def assemble(
    model: Model,
    coverage: dict,
    raw: dict,
    upstream: Upstream,
    now: dt.datetime,
    images: dict | None = None,
    catalog_info: dict | None = None,
) -> dict:
    ranking = model.ranking()
    focus = focus_areas(model, ranking)
    games = game_records(model, images)
    shown = [g for g in games if listed(g)]
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
                "name_origin": t.get("name_origin"),
                "game": t.get("game"),
                "region": REGIONS.get(t.get("region") or "", t.get("region")),
                "concept": t.get("concept"),
                "content_id": t.get("content_id"),
                "engine": t["engine"],
                "kind": t["kind"],
                "tags": t["tags"],
                "tag_sources": t["tag_sources"],
                "curated": t["curated"],
                "best_stage": best,
                "unverified_claim": model.unverified_claim(t),
                "stage_on_branches": model.branch_stage(t),
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
                "discussions": sorted({m["number"] for m in t["mentions"] if m["kind"] == "discussion"}),
                "last_evidence": last,
                "confidence": model.confidence(t),
            }
        )
    blockers = []
    for b in sorted(model.blockers.values(), key=lambda b: (b["status"] != "open", -b["score"], -(b["issue"] or 0))):
        blockers.append({k: v for k, v in b.items() if k != "signature_key"})
    rl = raw.get("rate_limit", {})
    levels = Counter(g["confidence"]["level"] for g in shown)
    menus = STAGES.index("Menus")
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
        "tags": [{"name": tag, "group": TAG_GROUPS.get(tag, "Genre"), "meaning": TAG_HELP[tag]} for tag in TAGS],
        "scoring": {
            "formula": "3*one_fix_away + 2*frontier + total",
            "frontier": "games for which this is the earliest open blocker on at least one OS/GPU path of a title ID",
            "one_fix_away": "games for which this is the only open blocker on at least one path of a title ID",
            "total": "games that list this blocker anywhere in the open chain of one of their title IDs",
            "excluded": "games whose stage is Playable count only towards total",
        },
        "confidence_levels": {
            "verified": "A person checked the source (data/blockers.json, a stage review), or the maintainers' list has it.",
            "corroborated": "Two or more GitHub accounts report the stage on main, or on main plus merged PRs.",
            "reported": "One account reports the stage on main, or on main plus merged PRs.",
            "none": "No qualifying report.",
        },
        "stats": {
            "games": len(shown),
            "games_with_stage": sum(1 for g in shown if g["stage"]),
            "games_verified": levels.get("verified", 0),
            "games_corroborated": levels.get("corroborated", 0),
            "games_single_report": levels.get("reported", 0),
            "games_reach_menus": sum(1 for g in shown if g["stage"] and STAGES.index(g["stage"]["stage"]) >= menus),
            "games_playable": sum(1 for g in shown if g["stage"] and g["stage"]["stage"] == "Playable"),
            "games_with_open_blockers": sum(1 for g in shown if g["open_blockers"]),
            "games_with_claim": sum(1 for g in shown if g["unverified_claim"]),
            "games_further_on_branches": sum(1 for g in shown if g["stage_on_branches"]),
            "games_with_image": sum(1 for g in shown if g["image"]),
            "games_by_stage": {st: sum(1 for g in shown if g["stage"] and g["stage"]["stage"] == st) for st in STAGES},
            "games_with_several_title_ids": sum(1 for g in shown if len(g["title_ids"]) > 1),
            "title_ids_folded": sum(len(g["title_ids"]) - 1 for g in shown),
            "identity_review": len(model.identity.review),
            "discussions_scanned": len(raw.get("discussions", [])),
            "issues_scanned": len(raw["issues"]),
            "issues_open": sum(1 for i in raw["issues"] if i["state"] == "OPEN"),
            "prs_scanned": len(raw["prs"]),
            "titles": len(titles),
            "titles_with_open_blockers": sum(1 for t in titles if t["open_blockers"]),
            "titles_with_stage": sum(1 for t in titles if t["best_stage"]),
            "titles_with_unverified_claim": sum(1 for t in titles if t["unverified_claim"]),
            "titles_with_tags": sum(1 for t in titles if t["tags"]),
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
        "games": games,
        "identity": identity_section(model, catalog_info),
        "titles": titles,
        "coverage": coverage,
        "focus": focus,
        "not_blockers": [{"issue": n, "reason": r} for n, r in sorted(model.not_blockers.items())],
        "gaps": model.gaps + [f"Not read in full: {t}." for t in raw.get("truncated", [])][:5] + KNOWN_GAPS,
        "sources": {
            "issues_and_prs": f"https://github.com/{model.repo} via gh api graphql (open + closed in the last {WINDOW_DAYS} days)",
            "dependencies": f"/repos/{model.repo}/issues/{{n}}/dependencies/blocked_by",
            "curated": "data/blockers.json",
            "tags": "data/blockers.json title_tags: Wikidata genres, PlayStation Store genres, SteamSpy user tags and homebrew READMEs, linked per title in tag_sources",
            "games": f"data/games.json (curated) and the PlayStation title list ({CATALOG_URL})",
            "images": "PlayStation Store concept artwork on image.api.playstation.com, else Steam library art via Wikidata; hotlinked, see docs/images.md",
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
        "unblocks": sum(1 for v in vias if "unblocks" in v),
        "fixes": sum(1 for per_issue in model.links.values() for k in per_issue.values() if k == "fixes"),
    }


KNOWN_GAPS = [
    "Title names, engines and stages are mined with keyword rules per line; negation and context are handled only roughly.",
    "Mined chain order is a heuristic: the latest recorded stop first, then issues by creation date.",
    "Read: issue, PR and discussion bodies, their comments and discussion replies, PR reviews and review-thread "
    "comments (up to 100 threads and 50 comments per thread), and timeline cross-references. Not read: commit "
    "messages, diffs, attached logs and screenshots (images, gists, uploaded files), edit history, and bot comments.",
    "Issues and PRs closed more than 60 days ago are not read, even when they hold the last report on a title.",
    "Stops are read from a fenced log when the comment names exactly one title ID, or when an issue comment names "
    "no title ID and its issue title names exactly one valid title ID, provided the issue is not a tracker; the last "
    "error line in the block counts as the stop.",
    "“N reports on main” counts distinct GitHub accounts whose text puts the title at that stage on main. It cannot "
    "tell whether two accounts tested the same build, and text without a stated build counts as main in issues and as "
    "the PR branch in PRs.",
    "Titles without a PPSA or CUSA ID (some homebrew) appear only when curated.",
    "Title IDs are joined into one game only on a person's word, one PlayStation Store concept, or names that agree "
    "once spelling, symbols, editions and known short forms are set aside. A title ID the PlayStation title list does "
    "not know, under a name written differently, stays a game of its own until someone lists it in data/games.json.",
    "Covers come from the PlayStation Store or Steam; homebrew and delisted titles have none.",
    "Discord reports are invisible unless someone copies them into GitHub or the curated file.",
    "Signatures are matched by prefix after hex addresses and long numbers are masked; reworded messages split into separate keys.",
    "PM4 status reads Pm4::UnsupportedReason(); a packet can pass that check and still be handled only partly.",
    "Stages mined from PR text describe the PR branch (build “PR #N”), not main, unless the sentence says main and "
    "names no patches; they count once the PR is merged.",
    "An issue that names seven or more titles is treated as a tracker: only its per-title stop rows count, as separate blockers.",
    "HLE “named in issues” counts any mention of a missing function, including lists of imports that were never reached.",
    "A mined stage of Menus or higher on main is only a claim until a person reviews it. What is reported off main "
    "(open PRs, local patches, a working group's stack) is shown as the stage off main and never counts.",
]
