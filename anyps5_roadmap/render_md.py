"""Render ROADMAP.md and llms.txt from the assembled document."""

from __future__ import annotations

import html
import re

from .assemble import AREA_NAMES
from .config import ARCHIVE_URL, PROGRESS_URL, STAGES


def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def fmt_date(iso: str | None) -> str:
    return iso[:10] if iso else "—"


def area_name(area: str | None) -> str:
    return AREA_NAMES.get(area, area) if area else "—"


def evidence_label(url: str, repo: str) -> str:
    m = re.search(r"/(issues|pull)/(\d+)(#issuecomment-\d+)?", url or "")
    if not m:
        return "archived report" if url and "discussions/2475" in url else "source"
    return f"#{m.group(2)}" + (" comment" if m.group(3) else "")


def md_cell(text) -> str:
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ")


def render_markdown(doc: dict) -> str:
    repo = doc["upstream"]["repo"]
    B = {b["id"]: b for b in doc["blockers"]}
    s = doc["stats"]
    L = []
    a = L.append
    a("# AnyPS5 blocker map\n")
    a(
        f"> Generated data, community prototype, not official. Built {doc['generated_at']} from public GitHub data of "
        f"[{repo}](https://github.com/{repo}) at `{(doc['upstream'].get('commit') or '?')[:8]}` plus `data/blockers.json`.\n"
    )
    a(
        f"Issues read: {s['issues_scanned']} · PRs read: {s['prs_scanned']} · discussions read: {s.get('discussions_scanned', 0)} · "
        f"games: {s.get('games', s['titles'])} ({s['titles']} title IDs seen) · open blockers: {s['blockers_open']} "
        f"({s['blockers_ranked']} stop at least one game) · curated blockers: {s['blockers_curated']}\n"
    )
    a(
        "Score = 3 × one_fix_away + 2 × frontier + total, counted by game (all title IDs of a game count once). "
        "Frontier: games for which the blocker is the first open one. One fix away: games for which it is the only open one.\n"
    )
    a("## Focus areas\n")
    for i, ar in enumerate(doc["focus"]["areas"], 1):
        tops = ", ".join(md_ref(B[b]) for b in ar["blockers"])
        a(
            f"{i}. **{ar['name']}** (score {ar['score']}): {ar['blocker_count']} blockers on {ar['titles']} games, "
            f"first stop for {ar['frontier_titles']}; open fix PRs {ar['open_fix_prs']}. Top: {tops}"
        )
    a("")
    a("## Blocker ranking\n")
    a("| # | Blocker | Frontier | One fix away | Total | Score | Area | PRs | Last activity |")
    a("|--:|---|--:|--:|--:|--:|---|---|---|")
    ranked = [B[i] for i in doc["ranking"] if B[i]["score"] > 0]
    for n, b in enumerate(ranked, 1):
        prs = ", ".join(f"[{p['ref']}]({p['url']}) {p['state']}" for p in b["prs"][:4]) or "none"
        a(
            f"| {n} | {md_ref(b)} {md_cell(b['title'])} ({b['origin']}) | {b['frontier']} | {b['one_fix_away']} | {b['total']} | "
            f"**{b['score']}** | {area_name(b['area'])} | {md_cell(prs)} | {fmt_date(b.get('last_activity'))} |"
        )
    a("")
    a("## Games\n")
    a(
        "One row per game, with all of its title IDs (region variants and other spellings of its name). The stage "
        "counts only qualifying reports: curated ones, and mined ones below Menus that ran on main or on main plus "
        "merged PRs. A mined claim of Menus or higher that nobody has reviewed is listed as an unverified claim and is "
        "not sorted on. Confidence: checked by hand, or how many GitHub accounts report the stage on main.\n"
    )
    a(
        "| Game | Title IDs | Stage | Confidence | Where | Source | Unverified claim | Off main (open PRs, patches) | "
        "Open blockers, in order |"
    )
    a("|---|---|---|---|---|---|---|---|---|")
    shown = [
        g
        for g in doc["games"]
        if g["stage"] or g["open_blockers"] or g["unverified_claim"] or g.get("stage_on_branches")
    ]
    shown.sort(
        key=lambda g: (
            -(STAGES.index(g["stage"]["stage"]) if g["stage"] else -1),
            len(g["open_blockers"]),
            (g["name"] or g["id"]).lower(),
        )
    )
    for g in shown:
        best = g["stage"]
        stage = f"{best['stage']} ({best['origin']}{', reviewed' if best.get('review') else ''})" if best else "—"
        where = " · ".join(x for x in [best.get("os"), best.get("gpu"), best.get("build")] if x) if best else ""
        src = (
            f"[{evidence_label(best['url'], doc['upstream']['repo'])}]({best['url']})"
            if best and best.get("url")
            else "—"
        )
        claim = g["unverified_claim"]
        claim_md = f"{claim['stage']}, [source]({claim['url']})" if claim else "—"
        branch = g.get("stage_on_branches")
        off = "—"
        if branch:
            needs = ", ".join(f"#{n}" for n in branch["needs"])
            off = (
                f"{branch['stage']}" + (f" with {needs}" if needs else "") + (" + patches" if branch["patches"] else "")
            )
            off += f", [source]({branch['url']})"
        chain = " → ".join(
            md_ref(B[st["id"]]) + (f" ({'/'.join(st['scope'])})" if st.get("scope") else "")
            for st in g["open_blockers"][:6]
            if st["id"] in B
        )
        ids = ", ".join(f"`{t['id']}`" + (f" {t['region']}" if t.get("region") else "") for t in g["titles"])
        sure = g["confidence"].get("label") or "—"
        a(
            f"| {md_cell(g['name'] or '')} | {ids} | {stage} | {md_cell(sure)} | {md_cell(where)} | {src} | {claim_md} | "
            f"{off} | {chain or '—'} |"
        )
    a("")
    cov = doc["coverage"]
    a("## Coverage\n")
    if cov.get("isa"):
        a(f"- RDNA ISA decode: {cov['isa']['done']} of {cov['isa']['total']} ({cov['isa']['percent']}%)")
    if cov.get("hle"):
        a(f"- HLE functions: {cov['hle']['done']} of {cov['hle']['total']} ({cov['hle']['percent']}%)")
    if cov.get("pm4"):
        c = cov["pm4"]["counts"]
        a(
            f"- PM4 type-3 packets: {c.get('handled', 0)} handled, {c.get('conditional', 0)} conditional, {c.get('rejected', 0)} rejected of {cov['pm4']['total']}"
        )
        a("\n| Opcode | Packet | Status | Reason | Issues |\n|---|---|---|---|---|")
        for r in cov["pm4"]["rows"]:
            if r["status"] != "handled":
                a(
                    f"| `{r['hex']}` | `{r['name']}` | {r['status']} | {md_cell(r['reason'] or '')} | {', '.join('#%d' % n for n in r['issues'][:5])} |"
                )
    if cov.get("hle"):
        asked = [(g["library"], n, nums) for g in cov["hle"]["groups"] for n, nums in g["requested"].items()]
        if asked:
            a("\nMissing HLE functions named in issues:\n")
            for lib, name, nums in asked[:30]:
                a(f"- `{lib}`: `{name}` ({', '.join('#%d' % n for n in nums[:4])})")
    a("")
    a("## Help wanted\n")
    for hw in doc["focus"]["help_wanted"]:
        b = B[hw["blocker"]]
        a(f"- {md_ref(b)} {md_cell(b['title'])}: {hw['reason']}")
    a("")
    a("## Known gaps\n")
    for g in doc["gaps"]:
        a(f"- {g}")
    a("")
    return "\n".join(L) + "\n"


def md_ref(b: dict) -> str:
    if b.get("issue"):
        return f"[#{b['issue']}]({b['url']})"
    if b.get("parent"):
        return f"[row in #{b['parent']}]({b['url']})"
    label = f"PR #{b['id'][3:]}" if re.fullmatch(r"pr-[0-9]+", b["id"]) else b["id"]
    return f"[{label}]({b['url']})" if b.get("url") else f"`{label}`"


def render_llms(doc: dict) -> str:
    repo = doc["upstream"]["repo"]
    B = {b["id"]: b for b in doc["blockers"]}
    top = [B[i] for i in doc["ranking"][:5]]
    L = [
        "# AnyPS5 blocker map",
        "",
        f"> Generated technical roadmap for AnyPS5, a tool that ports PS5 executables to Linux and Windows (https://github.com/{repo}): which open issues block which PS5 "
        "games, ranked by how many games a fix would move, plus HLE, RDNA ISA and PM4 coverage. Community prototype, not official; "
        "regenerated from GitHub data by roadmap.py.",
        "",
        f"Snapshot {doc['generated_at']}, upstream commit {(doc['upstream'].get('commit') or '?')[:8]}. "
        f"{doc['stats']['blockers_open']} open blockers, {doc['stats'].get('games')} games on the page ({doc['stats']['titles']} title IDs seen). "
        "Top of the ranking:",
        "",
    ]
    for b in top:
        L.append(
            f"- {md_ref(b)} {b['title']} (score {b['score']}: frontier {b['frontier']}, one fix away {b['one_fix_away']}, total {b['total']})"
        )
    L += [
        "",
        "How to read the data:",
        "",
        "- `games` is the list to read first: one entry per game, with its `title_ids` (PPSA for PS5, CUSA for PS4; region "
        "variants of one game share an entry, `titles` gives each ID's region), its `aliases` (other ways the name is "
        "written, such as GTA V for Grand Theft Auto V), `stage`, `confidence`, `unverified_claim`, `open_blockers`, "
        "`stage_on_branches` (the furthest stage off main, with open PRs or local patches: `needs` lists the open "
        "PRs it ran with, `patches` says it had more; never the stage, never ranked on), "
        "`timeline` (each date the stage rose, with its source) and `image` (a cover on the PlayStation Store or Steam CDN, "
        "hotlinked, or null). `identity.merges` lists every game that holds several title IDs with the reasons; "
        "`identity.review` lists matches that may be one game and are never merged by themselves.",
        "- `confidence.level` is `verified` (a person checked the source), `corroborated` (two or more GitHub accounts "
        "report the stage on main or on main plus merged PRs), `reported` (one account) or `none`.",
        "- Stages, lowest to highest: "
        + ", ".join(STAGES)
        + ". `best_stage` is the highest verified stage, with os, gpu, build, "
        "a source `url` and `verified` (true for curated and upstream entries, false for mined ones below Menus).",
        "- Verification policy: a mined stage of Menus or higher never becomes `best_stage` until a person reviews it "
        "(`stage_reviews` in data/blockers.json). Until then it is `unverified_claim` = {stage, url, quote}: a claim from "
        "issue or PR text, often made on a branch with open PRs. Do not report an unverified claim as the title's stage, "
        "and do not rank or sort titles by it. Only main, or main plus PRs that are merged, counts as reaching a stage.",
        "- `stage_reviews` on a title lists the hand verdicts (confirmed, downgraded, suppressed) with the quote they rest on.",
        "- A title's `open_blockers` are ordered: the first entry is where it stops now. `scope` limits a step to an OS/GPU path.",
        "- `tags` on a title say what kind of game it is, from the fixed list in the top-level `tags` (2D, 3D, genres, and "
        "App for anything that is not a game); `tag_sources` link the Wikidata item, PlayStation Store page, SteamSpy page or "
        "homebrew README they come from. An empty list means no source was found, not that the title has no kind.",
        "- `titles` keeps one entry per title ID, with `game` naming its game. `confidence` on a title counts reports, it does not verify them: `reports_on_main` is the number of distinct GitHub "
        "accounts whose own text puts the title at its best stage (or higher) on main; `claim.reports_on_main` and "
        "`claim.reports_on_branches` do the same for the unverified claim on main and on PR branches or patched builds.",
        "- Each mined evidence item has an `author`, a `part` (body, comment or review) and a `build` (`main`, `main + #N`, "
        "`main + patches`, `PR #N`) with `build_kind` (main, prs or patched) and the `prs` it ran with; a stage on `prs` "
        "counts once every one of them is merged. A PR link on a blocker has `via`: `closing` (GitHub's closing references), `xref` (a timeline "
        "cross-reference), `text` (read from PR text) or `resubmission` (the PR resubmits or carries a fix PR closed "
        "without merge, or carries a fork fix PR, named in `resubmits`).",
        "- `origin` is `curated` (data/blockers.json, reviewed by a person), `mined` (regex rules over issue and PR text), "
        "`upstream` (no longer produced since docs/user/COMPATIBILITY.md was removed upstream) or `github` (native blocked-by links). Prefer curated facts when they conflict.",
        "- Blocker ids are upstream issue numbers, `pr-N` for blockers known only through a PR, `N~symbol` for a crash site that only "
        "appears as a row in tracker issue N, or a slug.",
        "- Import signatures are keyed by NID, so `undefined symbol: X` (Linux) and `FAIL: unresolved ELF import X ...` (Windows) match.",
        "- Do not quote mined stages as fact without opening the `url` next to them.",
        "",
        "## Data",
        "",
        f"- [roadmap.json](roadmap.json): full data, `schema_version` {doc['schema_version']}. Keys: stages, tags, scoring, confidence_levels, stats, ranking "
        "(blocker ids, best first), blockers, games, identity, titles, coverage (isa, hle, pm4, registers), focus (areas, help_wanted), gaps, sources.",
        "- [feed.json](feed.json): what each snapshot changed, as a JSON Feed 1.1, newest first; the last 50 snapshots "
        "that changed something. An item lists blockers resolved, blockers entering, leaving or moving in the ranking "
        "(moves only when the blocker's own score changed and one of its places is in the top 15), games whose "
        "stage or first open blocker changed, and games that took in another title ID, in plain sentences with links to the page. Its `id` and "
        "`date_published` are the snapshot's `generated_at`; `_anyps5.changes` holds the same as records "
        "(`type`: resolved, entered, left, moved, stage, stop or merged) and `_anyps5.since` the snapshot it compares with.",
        "- [ROADMAP.md](ROADMAP.md): ranking, games, coverage and help wanted as Markdown tables.",
        "- [index.html](index.html): the same for people, as an app that reads roadmap.json and feed.json; every blocker "
        "has a link of its own (`#/blockers/<id>`), and so does every game (`#/games/<game id>`, or any of its title IDs).",
        "- [classic.html](classic.html): the same as one static page that works without JavaScript.",
        "",
        "## Curation",
        "",
        "- [AGENTS.md](AGENTS.md): how to add or correct curated blockers and title chains in data/blockers.json, and how to verify them.",
        f"- Report a wrong entry: {doc.get('project', {}).get('corrections', '')} (issue forms for a wrong or missing stage, a "
        "missing or wrong blocker, and a mining bug; a public source link is required).",
        "",
        "## Optional",
        "",
        f"- [Upstream repository](https://github.com/{repo}): issues, PRs and source.",
        f"- [Upstream progress.json]({PROGRESS_URL}): HLE and ISA decode counts this page reuses.",
        f"- [Archived compatibility reports]({ARCHIVE_URL}): the former docs/user/COMPATIBILITY.md, archived upstream; reports now live in the Game bring-up discussions.",
        "",
    ]
    return "\n".join(L)
