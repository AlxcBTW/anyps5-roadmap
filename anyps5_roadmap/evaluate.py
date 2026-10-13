"""Evaluation: how far a title or a game gets, how sure the map is, and how it got there.

The same rules hold for one title ID and for a game (the evidence of all of its title IDs together):

- **Qualifying evidence** counts toward the stage: curated facts (data/blockers.json, stage reviews, the
  archived maintainers' list), and mined reports below Menus that ran on main, or on main plus PRs that
  are merged now. Reports from local patches, forks, hacks or branches with open PRs never count. A mined
  report older than the newest curated fact is superseded by it.
- **Stage**: the highest qualifying stage; between equals, the curated one, then the newest.
- **Unverified claim**: the highest mined stage of Menus or higher, reported on main, above that stage. Shown,
  never counted, until a person reviews it.
- **Stage on branches**: the highest stage reached on a build with open PRs or local patches (a PR's branch, a
  working group's stack), above both, with the open PRs it needs. Shown apart, never counted; once those PRs
  are merged the same reports qualify and the stage moves up by itself.
- **Confidence**: `verified` (a person checked the source), `corroborated` (two or more accounts report the
  stage on a qualifying build), `reported` (one account), or `none`.
- **Timeline**: each date on which the qualifying stage rose, with its source.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable

from .config import STAGES, VERIFY_FROM

Merged = Callable[[int], bool]
CONFIDENCE_LABELS = {
    "verified": "Checked by hand",
    "corroborated": "{n} reports on main",
    "reported": "1 report on main",
    "none": None,
}


def rank(stage: str | None) -> int:
    return STAGES.index(stage) if stage in STAGES else -1


def on_main(e: dict, merged: Merged) -> bool:
    """Whether a report ran on main, or on main plus PRs that are all merged now."""
    kind = e.get("build_kind")
    if kind is None:  # curated and older entries carry only the label
        build = e.get("build") or "main"
        if build == "main":
            return True
        prs = [int(n) for n in re.findall(r"#(\d+)", build)]
        return bool(prs) and not re.search(r"patch|local|fork|hack|branch", build, re.I) and all(map(merged, prs))
    if kind == "main":
        return True
    return kind == "prs" and bool(e.get("prs")) and all(merged(n) for n in e["prs"])


def qualifies(e: dict, merged: Merged, superseded_before: str = "") -> bool:
    if e.get("origin") in ("curated", "upstream"):
        return True
    if rank(e.get("stage")) >= VERIFY_FROM or not on_main(e, merged):
        return False
    return not superseded_before or (e.get("date") or "") > superseded_before


def _curated_date(evidence: Iterable[dict]) -> str:
    return max((e.get("date") or "" for e in evidence if e.get("origin") == "curated"), default="")


def best_stage(evidence: list[dict], merged: Merged) -> dict | None:
    """The best qualifying evidence, with `verified` true when a person or the maintainers' list stands
    behind it."""
    since = _curated_date(evidence)
    pool = [e for e in evidence if qualifies(e, merged, since)]
    if not pool:
        return None
    origin_rank = {"curated": 2, "upstream": 1, "mined": 0}
    best = max(pool, key=lambda e: (rank(e["stage"]), origin_rank.get(e.get("origin"), 0), e.get("date") or ""))
    return {**best, "verified": best.get("origin") in ("curated", "upstream")}


def unverified_claim(evidence: list[dict], best: dict | None, merged: Merged | None = None) -> dict | None:
    """The highest mined stage of Menus or higher that nobody has reviewed, above the best stage. With `merged`,
    only reports on main (or on main plus merged PRs) are claims; the others belong to the stage on branches."""
    floor = rank(best["stage"]) if best else -1
    claims = [
        e
        for e in evidence
        if e.get("origin") == "mined"
        and rank(e["stage"]) >= VERIFY_FROM
        and rank(e["stage"]) > floor
        and (merged is None or on_main(e, merged))
    ]
    if not claims:
        return None
    c = max(claims, key=lambda e: (rank(e["stage"]), e.get("date") or ""))
    return {"stage": c["stage"], "url": c["url"], "quote": c.get("quote") or c.get("note"), "build": c.get("build")}


def _authors(evidence: list[dict], stage: str, merged: Merged, main: bool) -> list[str]:
    floor = rank(stage)
    return sorted(
        {
            e["author"]
            for e in evidence
            if e.get("origin") == "mined"
            and e.get("author")
            and rank(e["stage"]) >= floor
            and on_main(e, merged) == main
        }
    )


def confidence(evidence: list[dict], merged: Merged, best: dict | None = None, claim: dict | None = None) -> dict:
    """How sure the map is of the stage. A count of accounts is not a verdict: only a stage review turns a
    claim into a stage."""
    best = best if best is not None else best_stage(evidence, merged)
    claim = claim if claim is not None else unverified_claim(evidence, best, merged)
    out: dict = {"stage": best["stage"] if best else None, "level": "none", "reports_on_main": 0, "authors": []}
    if best:
        out["authors"] = _authors(evidence, best["stage"], merged, True)
        out["reports_on_main"] = len(out["authors"])
        if best.get("verified"):
            out["level"] = "verified"
        else:
            out["level"] = "corroborated" if out["reports_on_main"] >= 2 else "reported"
        dates = [
            e.get("date") or ""
            for e in evidence
            if rank(e["stage"]) >= rank(best["stage"]) and qualifies(e, merged, _curated_date(evidence))
        ]
        out["last_seen"] = max(dates, default="") or None
    if claim:
        out["claim"] = {
            "stage": claim["stage"],
            "reports_on_main": len(_authors(evidence, claim["stage"], merged, True)),
            "reports_on_branches": len(_authors(evidence, claim["stage"], merged, False)),
        }
    n = out["reports_on_main"]
    if out["level"] == "verified":
        out["label"] = CONFIDENCE_LABELS["verified"]
    elif n:
        out["label"] = f"{n} report{'s' if n != 1 else ''} on main"
    else:
        out["label"] = None
    return out


def needs(e: dict, merged: Merged) -> list[int]:
    """The PRs a report ran with that are not merged yet."""
    return sorted({n for n in e.get("prs") or [] if not merged(n)})


def branch_stage(
    evidence: list[dict], merged: Merged, best: dict | None = None, claim: dict | None = None
) -> dict | None:
    """The furthest stage reached off main: on a PR's branch, on main plus open PRs, or on a build with local
    patches. Only when it is above the stage on main and the claim. Between equal stages, the report that needs
    the least wins: open PRs only before local patches, fewer PRs first, then the newest. `needs` lists its open
    PRs, `patches` says it also had changes no PR carries; `confidence` counts the accounts that report the
    stage, or a higher one, off main."""
    floor = max(rank(best["stage"]) if best else -1, rank(claim["stage"]) if claim else -1)
    pool = [e for e in evidence if e.get("origin") == "mined" and not on_main(e, merged) and rank(e["stage"]) > floor]
    if not pool:
        return None

    def cost(e):
        return (rank(e["stage"]), e.get("build_kind") != "patched", -len(needs(e, merged)), e.get("date") or "")

    top = max(pool, key=cost)
    authors = sorted({e["author"] for e in pool if e.get("author") and rank(e["stage"]) >= rank(top["stage"])})
    n = len(authors)
    return {
        "stage": top["stage"],
        "url": top["url"],
        "quote": top.get("quote") or top.get("note"),
        "date": top.get("date"),
        "build": top.get("build"),
        "title": top.get("title"),
        "needs": needs(top, merged),
        "patches": top.get("build_kind") == "patched",
        "confidence": {
            "level": "corroborated" if n >= 2 else "reported",
            "reports": n,
            "authors": authors,
            "label": f"{n} report{'s' if n != 1 else ''} off main" if n else None,
        },
    }


def timeline(evidence: list[dict], merged: Merged) -> list[dict]:
    """The dates on which the qualifying stage rose, oldest first. Undated curated facts (the archived list)
    come first."""
    since = _curated_date(evidence)
    pool = [e for e in evidence if qualifies(e, merged, since) or e.get("origin") == "curated"]
    pool.sort(key=lambda e: (e.get("date") or "", -rank(e["stage"])))
    out, top = [], -1
    for e in pool:
        if rank(e["stage"]) > top:
            top = rank(e["stage"])
            out.append(
                {
                    "date": e.get("date"),
                    "stage": e["stage"],
                    "url": e["url"],
                    "origin": e.get("origin"),
                    "build": e.get("build"),
                    "title": e.get("title"),
                }
            )
    return out


def quote_key(e: dict) -> str:
    return re.sub(r"\W+", " ", (e.get("quote") or e.get("note") or "").lower()).strip()


def dedupe(evidence: list[dict]) -> list[dict]:
    """One entry per report: the same source and stage once, and a quote repeated in another thread (a
    cross-post or a copied summary) folded into its earliest appearance, which lists the others in `also`."""
    out: list[dict] = []
    by_source: dict[tuple, dict] = {}
    by_quote: dict[tuple, dict] = {}
    for e in sorted(evidence, key=lambda e: (e.get("date") or "", e.get("url") or "")):
        q = quote_key(e)
        source = (e.get("url"), e["stage"], q, e.get("origin"))
        if source in by_source:
            continue
        twin = by_quote.get((e["stage"], q, e.get("origin"))) if len(q) >= 24 else None
        if twin is not None:
            if e.get("url") and e["url"] != twin["url"] and e["url"] not in twin.setdefault("also", []):
                twin["also"].append(e["url"])
            by_source[source] = twin
            continue
        e = dict(e)
        out.append(e)
        by_source[source] = e
        if len(q) >= 24:
            by_quote[(e["stage"], q, e.get("origin"))] = e
    return out
