#!/usr/bin/env python3
"""Render the classic page, site/classic.html, from site/roadmap.json.

The site's front page is the web app in web/, which reads the same JSON at runtime. The
classic page is the whole map as one static page: the fallback without JavaScript, and the
front page of a build made without Node (roadmap.py writes it as index.html too).

The page reads nothing but the published JSON, so every fact it shows is also in the
data that tools and agents read. Standard library only. Without JavaScript the page
still shows everything; scripts add the side panel, the game filters, the coverage
tooltip and the theme switch.

"Games" are counted by name everywhere; one game can have several title IDs (regions),
and the games table has one row per title ID.

    python3 render_html.py                      # site/roadmap.json -> site/classic.html
    python3 render_html.py in.json out.html
"""

from __future__ import annotations

import datetime as dt
import html
import json
import math
import sys
import urllib.parse
from pathlib import Path

TOP = 10
DOTS = 10
AREAS = {
    "shader": "Shader recompiler",
    "agc": "AGC driver",
    "libkernel": "libkernel",
    "libc": "libc",
    "prx": "HLE libraries",
    "relinker": "Relinker",
}
FILES = [
    ("roadmap.json", "Everything on this page, for tools and scripts"),
    ("feed.json", "What changed in each snapshot, for feed readers"),
    ("llms.txt", "Entry point for language models"),
    ("ROADMAP.md", "Ranking, games and coverage as Markdown tables"),
    ("AGENTS.md", "How to add or correct an entry"),
]


def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def fmt_date(iso: str | None) -> str:
    if not iso:
        return ""
    d = dt.date.fromisoformat(iso[:10])
    return f"{d.day} {d:%b %Y}"


def fmt_time(iso: str) -> str:
    t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return f"{t.day} {t:%b %Y}, {t:%H:%M} UTC"


def fmt_size(n: int) -> str:
    return f"{n / 1024:,.0f} KB" if n >= 1024 else f"{n} bytes"


def plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n:,} {one if n == 1 else (many or one + 's')}"


def slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


def ext(url: str, text: str, cls: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    return f'<a{c} href="{esc(url)}">{text}</a>'


# Octicons mark-github (16 px), drawn in currentColor.
GITHUB_MARK = (
    '<svg class="gh-mark" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">'
    '<path fill="currentColor" d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 '
    "0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2."
    "36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 "
    "1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61."
    "55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 "
    '1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"/></svg>'
)


def source_label(url: str, repo: str) -> str:
    base = f"https://github.com/{repo}/"
    if url.startswith(base):
        kind, _, tail = url[len(base) :].partition("/")
        num = tail.split("#")[0].split("/")[0]
        if kind == "pull" and num.isdigit():
            return f"PR #{num}"
        if kind == "issues" and num.isdigit():
            return f"#{num}" + (" comment" if "#issuecomment" in tail else "")
        if kind == "blob":
            return tail.rsplit("/", 1)[-1]
    if url.startswith("https://github.com/"):
        parts = url.split("/")
        if len(parts) > 6 and parts[6].split("#")[0].isdigit():
            return f"{parts[3]}#{parts[6].split('#')[0]}"
    return url.split("//", 1)[-1].split("/", 1)[0]


def squarify(items: list[tuple[float, object]], x: float, y: float, w: float, h: float) -> list[tuple]:
    """Squarified treemap (Bruls et al.): (value, payload) sorted largest first -> (payload, x, y, w, h)."""
    items = [it for it in items if it[0] > 0]
    total = sum(v for v, _ in items)
    out: list[tuple] = []
    if not items or w <= 0 or h <= 0:
        return out
    rest = [(v * w * h / total, p) for v, p in items]

    def worst(row: list, side: float) -> float:
        area = sum(a for a, _ in row)
        return max(
            side * side * max(a for a, _ in row) / (area * area), area * area / (side * side * min(a for a, _ in row))
        )

    while rest:
        side = min(w, h)
        row = [rest[0]]
        for item in rest[1:]:
            if worst(row + [item], side) > worst(row, side):
                break
            row.append(item)
        rest = rest[len(row) :]
        area = sum(a for a, _ in row)
        if w >= h:
            col_w, cy = area / h, y
            for a, p in row:
                out.append((p, x, cy, col_w, a / col_w))
                cy += a / col_w
            x, w = x + col_w, w - col_w
        else:
            row_h, cx = area / w, x
            for a, p in row:
                out.append((p, cx, y, a / row_h, row_h))
                cx += a / row_h
            y, h = y + row_h, h - row_h
    return out


def grid_for(n: int, w: float, h: float) -> tuple[int, int]:
    """Columns and rows for n near-square cells in w x h, preferring grids with no empty cells."""
    ideal = max(1, round(w / math.sqrt(w * h / n)))
    best = None
    for cols in range(max(1, ideal - 4), min(n, ideal + 4) + 1):
        rows = math.ceil(n / cols)
        aspect = (w / cols) / (h / rows)
        if not 0.55 <= aspect <= 1.8 and cols != ideal:
            continue
        key = (rows * cols - n, abs(math.log(aspect)))
        if best is None or key < best[0]:
            best = (key, cols, rows)
    if best is None:
        return ideal, math.ceil(n / ideal)
    return best[1], best[2]


def cell_runs(start: int, end: int, cols: int) -> list[tuple[int, int, int, int]]:
    """Cells [start, end) of a row-major grid as rectangles (col, row, cols wide, rows high)."""
    runs = []
    while start < end:
        row, col = divmod(start, cols)
        if col == 0 and end - start >= cols:
            rows = (end - start) // cols
            runs.append((0, row, cols, rows))
            start += rows * cols
        else:
            stop = min(end, (row + 1) * cols)
            runs.append((col, row, stop - start, 1))
            start = stop
    return runs


CHEVRON = (
    '<svg class="chev" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">'
    '<path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round"/></svg>'
)
SEARCH = (
    '<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="4.5" '
    'fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M10.5 10.5L14 14" stroke="currentColor" '
    'stroke-width="1.5" stroke-linecap="round"/></svg>'
)


class Page:
    def __init__(self, doc: dict, site: Path | None = None):
        self.doc = doc
        self.site = site
        self.repo = doc["upstream"]["repo"]
        self.project = (doc.get("project") or {}).get("repo") or "AlxcBTW/anyps5-roadmap"
        self.blockers = {b["id"]: b for b in doc["blockers"]}
        self.titles = {t["id"]: t for t in doc["titles"]}
        self.stages = [s["name"] for s in doc["stages"]]
        self.stage_rank = {s: i for i, s in enumerate(self.stages)}
        ranked = [self.blockers[i] for i in doc["ranking"] if i in self.blockers]
        linked = [b for b in ranked if b.get("total")]
        self.unlinked = [b for b in ranked if not b.get("total")]
        # The data ranks by title ID; the page counts games by name, so it ranks by name too.
        self.score = {
            b["id"]: 3 * len(self.names(b.get("one_fix_titles", [])))
            + 2 * len(self.names(b.get("frontier_titles", [])))
            + len(self.names(b.get("titles", [])))
            for b in linked
        }
        order = {b["id"]: i for i, b in enumerate(linked)}
        self.ranked = sorted(linked, key=lambda b: (-self.score[b["id"]], order[b["id"]]))
        self.rank_of = {b["id"]: n for n, b in enumerate(self.ranked, 1)}
        self.listed = [
            t for t in doc["titles"] if t.get("best_stage") or t.get("open_blockers") or t.get("unverified_claim")
        ]

    # -- names ---------------------------------------------------------------

    def ref(self, b: dict) -> str:
        if b.get("issue"):
            return f"#{b['issue']}"
        if b["id"].startswith("pr-"):
            return f"PR #{b['id'][3:]}"
        return b["id"]

    def title_name(self, tid: str) -> str:
        return (self.titles.get(tid) or {}).get("name") or tid

    def names(self, ids: list[str]) -> set[str]:
        return {self.title_name(t) for t in ids}

    def games(self, ids: list[str]) -> list[tuple[str, list[str]]]:
        """Group title IDs by game name; the region IDs of one game count once."""
        by_name: dict[str, list[str]] = {}
        for tid in ids:
            by_name.setdefault(self.title_name(tid), []).append(tid)
        return list(by_name.items())

    def fix_status(self, b: dict) -> tuple[str, str, dict | None]:
        fixes = [p for p in b.get("prs", []) if p.get("link") == "fixes"]
        for states, kind, label in (
            (("open", "draft"), "review", "Fix in review"),
            (("merged",), "partial", "Partly fixed"),
            (("closed",), "closed", "Fix closed unmerged"),
        ):
            hit = [p for p in fixes if p.get("state") in states]
            if hit:
                return kind, label, hit[0]
        return "none", "No fix yet", None

    @staticmethod
    def stage_of(t: dict) -> str | None:
        return (t.get("best_stage") or {}).get("stage")

    def game_stages(self) -> dict[str, str | None]:
        """Best confirmed stage per game name, over all of its listed title IDs."""
        best: dict[str, str | None] = {}
        for t in self.listed:
            name, stage = self.title_name(t["id"]), self.stage_of(t)
            cur = best.get(name)
            if name not in best or (stage and (cur is None or self.stage_rank[stage] > self.stage_rank[cur])):
                best[name] = stage
        return best

    def blocker_href(self, b: dict) -> str:
        return f"#b-{b['id']}" if b["id"] in self.rank_of or b in self.unlinked else b["url"]

    def blocker_link(self, b: dict, name: bool = True) -> str:
        text = f'<span class="mono">{esc(self.ref(b))}</span>'
        if name:
            text += f' <span class="b-name">{esc(b["title"])}</span>'
        return f'<a class="b-link" href="{esc(self.blocker_href(b))}">{text}</a>'

    def report(self, template: str, about: str, fields: dict[str, str]) -> str:
        """A small link to a prefilled issue form of this project (issue forms take ?<field id>=value)."""
        query = urllib.parse.urlencode({"template": template, **{k: v for k, v in fields.items() if v}})
        url = f"https://github.com/{self.project}/issues/new?{query}"
        return f'<a class="report" href="{esc(url)}">Report a correction<span class="sr-only"> {esc(about)}</span></a>'

    def area(self, b: dict) -> str:
        return AREAS.get(b.get("area"), b.get("area") or "Other")

    # -- top bar and hero ----------------------------------------------------

    def topbar(self) -> str:
        up = self.doc["upstream"]
        commit = up.get("commit") or ""
        ref = (
            ext(f"https://github.com/{self.repo}/commit/{commit}", esc(commit[:7]), "mono")
            if commit
            else esc(up.get("ref") or "")
        )
        nav = "".join(
            f'<a href="#{i}">{t}</a>'
            for i, t in (("fix-next", "Fix next"), ("games", "Games"), ("coverage", "Coverage"), ("data", "Data"))
        )
        return f"""<header class="bar">
<div class="wrap bar-in">
  <a class="brand" href="#top"><span class="brand-mark">AnyPS5</span><span class="brand-sub">Blocker map</span></a>
  <nav class="nav" aria-label="Sections">{nav}</nav>
  <div class="bar-end">
    <span class="snap">Upstream {ref} · {esc(fmt_date(self.doc["generated_at"]))}</span>
    <button class="theme" id="theme" type="button" hidden>Theme: <span id="theme-v">System</span></button>
    <a class="gh" href="https://github.com/{esc(self.project)}">{GITHUB_MARK}<span class="gh-t">GitHub</span></a>
  </div>
</div>
</header>"""

    def hero(self) -> str:
        waiting = {self.title_name(t["id"]) for t in self.doc["titles"] if t.get("open_blockers")}
        top3 = set()
        for b in self.ranked[:3]:
            top3 |= self.names(b.get("frontier_titles", []))
        best = self.game_stages()
        held: dict[str, dict[str, set[str]]] = {s: {} for s in self.stages}
        for t in self.listed:
            stage, steps = self.stage_of(t), t.get("open_blockers") or []
            if stage and steps and steps[0]["id"] in self.blockers:
                held[stage].setdefault(steps[0]["id"], set()).add(self.title_name(t["id"]))
        rungs = []
        for i, s in enumerate(self.stages):
            n = sum(1 for v in best.values() if v == s)
            top = max(held[s].items(), key=lambda kv: (len(kv[1]), -self.rank_of.get(kv[0], 999)), default=None)
            pips = "".join(f'<i class="{"on" if j <= i else ""}"></i>' for j in range(len(self.stages)))
            meaning = self.doc["stages"][i]["meaning"]
            hold = (
                (
                    f'<span class="r-top">{len(top[1])} held by '
                    f'<span class="mono">{esc(self.ref(self.blockers[top[0]]))}</span></span>'
                )
                if top
                else ""
            )
            inner = (
                f'<span class="pips" aria-hidden="true">{pips}</span>'
                f'<span class="r-n">{n}</span><span class="r-name">{esc(s)}</span>'
                f'<span class="r-def">{esc(meaning)}</span>{hold}'
            )
            if n:
                rungs.append(
                    f'<li><a class="rung" href="#games" data-stage-link="{slug(s)}">'
                    f'<span class="sr-only">Show games at </span>{inner}</a></li>'
                )
            else:
                rungs.append(f'<li class="zero"><span class="rung">{inner}</span></li>')
        none = sum(1 for v in best.values() if v is None)
        rest = (
            f'<p class="ladder-note"><a href="#games" data-stage-link="none">'
            f"{plural(none, 'more game')}</a> {'has' if none == 1 else 'have'} an open blocker but no confirmed stage yet.</p>"
            if none
            else ""
        )
        return f"""<section class="hero" aria-labelledby="h-hero">
  <h1 id="h-hero">{esc(plural(len(self.ranked), "open blocker"))} stop {esc(plural(len(waiting), "PS5 game"))}.</h1>
  <p class="lead">Fixing the top three gets {len(top3)} of them past their current stop. Below: how far each game gets
  in AnyPS5, the tool that ports PS5 executables to Linux and Windows, and which issue holds most of them at each stage.</p>
  <ol class="ladder" aria-label="Games by highest confirmed stage">{"".join(rungs)}</ol>
  {rest}
</section>"""

    # -- fix next ------------------------------------------------------------

    def dots(self, b: dict) -> str:
        names = sorted(self.names(b.get("titles", [])))
        first = self.names(b.get("frontier_titles", []))
        names.sort(key=lambda n: n not in first)
        shown = "".join(f'<i class="{"on" if n in first else ""}"></i>' for n in names[:DOTS])
        more = f'<span class="more-dots">+{len(names) - DOTS}</span>' if len(names) > DOTS else ""
        return f'<span class="dots" aria-hidden="true">{shown}{more}</span>'

    def status_html(self, b: dict) -> str:
        kind, label, pr = self.fix_status(b)
        own = pr and b["id"] == f"pr-{pr.get('ref', '').lstrip('#')}"
        ref = f' <span class="mono">{esc(pr["ref"])}</span>' if pr and not own else ""
        return f'<span class="status s-{kind}"><i aria-hidden="true"></i>{label}{ref}</span>'

    def after_fix(self, b: dict) -> str:
        """What each blocked game hits once this blocker is fixed."""
        rows: list[str] = []
        seen: set[tuple] = set()
        for tid in b.get("titles", []):
            t = self.titles.get(tid) or {}
            steps = [s["id"] for s in (t.get("open_blockers") or []) if s["id"] in self.blockers]
            if b["id"] not in steps:
                continue
            i = steps.index(b["id"])
            if i > 0:
                key = (self.title_name(tid), "earlier", steps[0])
                tail = (
                    f'<span class="muted">stops earlier at</span> {self.blocker_link(self.blockers[steps[0]], False)}'
                )
            elif i + 1 < len(steps):
                key = (self.title_name(tid), "next", steps[i + 1])
                tail = f'<span class="muted">then</span> {self.blocker_link(self.blockers[steps[i + 1]])}'
            else:
                key = (self.title_name(tid), "done", "")
                tail = '<span class="muted">no known stop left</span>'
            if key in seen:
                continue
            seen.add(key)
            rows.append(f'<li><a href="#g-{esc(tid)}">{esc(self.title_name(tid))}</a> {tail}</li>')
        return f'<ul class="after">{"".join(rows)}</ul>' if rows else ""

    def pr_line(self, p: dict) -> str:
        note = f'<span class="pr-note">{esc(p["note"])}</span>' if p.get("note") else ""
        return (
            f'<li><span>{ext(p["url"], esc(p["ref"]), "mono")} <span class="muted">{esc(p.get("state"))}</span></span>'
            f'<span class="pr-title">{esc(p.get("title") or "")}</span>{note}</li>'
        )

    def blocker_body(self, b: dict, rank: int | None) -> str:
        rows = []
        after = self.after_fix(b)
        if after:
            first = len(self.names(b.get("frontier_titles", [])))
            only = len(self.names(b.get("one_fix_titles", [])))
            facts = [f"first stop for {plural(first, 'game')}"] if first else []
            if only:
                facts.append(f"the only stop left for {only}")
            fact = f'<p class="muted small">{esc(", ".join(facts).capitalize())}.</p>' if facts else ""
            rows.append(("After this fix", after + fact))
        if b.get("next"):
            rows.append(("Next step", f"<p>{esc(b['next'])}</p>"))
        if b.get("help_wanted"):
            rows.append(("Help wanted", f"<p>{esc(b['help_wanted'])}</p>"))
        if b.get("signature"):
            rows.append(("Error", f'<pre class="sig"><code>{esc(b["signature"])}</code></pre>'))
        prs = [p for p in b.get("prs", []) if p.get("link") in ("fixes", "related")]
        if prs:
            rows.append(("Pull requests", f'<ul class="prs">{"".join(self.pr_line(p) for p in prs)}</ul>'))
        dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
        num = f"No. {rank:02d} · " if rank else ""
        return f"""<div class="body">
<div class="p-head"><h3>{esc(b["title"])}</h3>
<p class="meta">{num}<span class="mono">{esc(self.ref(b))}</span> · {esc(self.area(b))} · {self.status_html(b)}</p></div>
<dl>{dl}</dl>
<p class="out">{ext(b["url"], f"Open {esc(self.ref(b))} on GitHub")}<span class="muted"> · last activity {esc(fmt_date(b.get("last_activity")))}</span> <span class="tail"><span class="muted">· </span>{self.blocker_report(b)}</span></p>
</div>"""

    def blocker_report(self, b: dict) -> str:
        label = f"{self.ref(b)} {b['title']}"
        fields = {
            "title": f"Blocker: {label}"[:120],
            "blocker": label,
            "page_source": b.get("url") or "",
            "error": b.get("signature") or "",
        }
        return self.report("blocker.yml", f"for {self.ref(b)}", fields)

    def game_report(self, t: dict) -> str:
        best, claim = t.get("best_stage") or {}, t.get("unverified_claim") or {}
        now = f"{best['stage']} ({best.get('origin', 'mined')})" if best.get("stage") else "No stage yet"
        if claim.get("stage"):
            now += f"; claimed {claim['stage']}, unverified"
        name = t.get("name") or ""
        fields = {
            "title": f"Stage: {name} ({t['id']})" if name else f"Stage: {t['id']}",
            "title_id": t["id"],
            "game": name,
            "page_stage": now,
            "page_source": best.get("url") or claim.get("url") or "",
        }
        return self.report("wrong-stage.yml", f"for {name or t['id']}" + (f" ({t['id']})" if name else ""), fields)

    def blocker_item(self, b: dict, rank: int | None) -> str:
        n = len(self.names(b.get("titles", [])))
        impact = (
            (
                f'<span class="impact">{self.dots(b)}<span class="count"><b>{n}</b> '
                f"{'game' if n == 1 else 'games'}</span></span>"
            )
            if rank
            else ""
        )
        num = f'<span class="rank">{rank:02d}</span>' if rank else ""
        sig = f'<span class="sig-line">{esc(b["signature"])}</span>' if b.get("signature") else ""
        return f"""<li class="blocker" id="b-{esc(b["id"])}">
<details>
<summary>{num}<span class="what"><span class="name">{esc(b["title"])}</span>
<span class="meta"><span class="mono">{esc(self.ref(b))}</span> · {esc(self.area(b))} · {self.status_html(b)}</span>{sig}</span>{impact}{CHEVRON}</summary>
{self.blocker_body(b, rank)}
</details>
</li>"""

    def fix_next(self) -> str:
        head = "".join(self.blocker_item(b, n) for n, b in enumerate(self.ranked[:TOP], 1))
        rest = self.ranked[TOP:]
        tail = ""
        if rest:
            items = "".join(self.blocker_item(b, n) for n, b in enumerate(rest, TOP + 1))
            tail = (
                f'<details class="rows"><summary><span class="rank">{TOP + 1}–{len(self.ranked)}</span>'
                f"<span>Show {len(rest)} more blockers</span>{CHEVRON}</summary>"
                f'<ol class="blockers" start="{TOP + 1}">{items}</ol></details>'
            )
        unlinked = ""
        if self.unlinked:
            items = "".join(self.blocker_item(b, None) for b in self.unlinked)
            unlinked = (
                f'<details class="rows"><summary><span class="rank">—</span>'
                f"<span>{esc(plural(len(self.unlinked), 'open blocker'))} not linked to a game yet</span>"
                f'{CHEVRON}</summary><ul class="blockers plain">{items}</ul></details>'
            )
        return f"""<section id="fix-next" class="sec" aria-labelledby="h-fix">
  <div class="sec-head">
    <h2 id="h-fix">Fix next</h2>
    <p class="intro">Score = 3 × games this is the last stop for + 2 × games it stops first + every game it touches.
    Filled dots are games it stops first, hollow ones hit it later.</p>
  </div>
  <div class="split">
    <div class="list-col">
      <ol class="blockers">{head}</ol>
      {tail}{unlinked}
    </div>
    <aside class="panel" id="panel" aria-label="Selected blocker" tabindex="-1" hidden></aside>
  </div>
  <p class="sr-only" role="status" id="sel-status"></p>
</section>"""

    # -- games ---------------------------------------------------------------

    def pips(self, stage: str | None) -> str:
        n = self.stage_rank[stage] + 1 if stage in self.stage_rank else 0
        return (
            '<span class="pips" aria-hidden="true">'
            + "".join(f'<i class="{"on" if i < n else ""}"></i>' for i in range(len(self.stages)))
            + "</span>"
        )

    def game_row(self, t: dict) -> str:
        stage = self.stage_of(t)
        claim = t.get("unverified_claim")
        conf = t.get("confidence") or {}
        # how many people back the shown stage on main; a count, never a promotion
        reports = f'<span class="note">{esc(conf["label"])}</span>' if stage and conf.get("label") else ""
        claim_html = ""
        if claim and claim.get("url"):
            n = (conf.get("claim") or {}).get("reports_on_main") or 0
            said = f"Claimed {claim.get('stage', '')}" + (f" in {n} reports on main" if n >= 2 else "")
            claim_html = (
                f'<span class="note">{esc(said)}, unverified · '
                f"{ext(claim['url'], esc(source_label(claim['url'], self.repo)))}</span>"
            )
        steps = [s for s in (t.get("open_blockers") or []) if s["id"] in self.blockers]
        if steps:
            first = self.blockers[steps[0]["id"]]
            where = f'<span class="note">{esc(", ".join(steps[0]["scope"]))}</span>' if steps[0].get("scope") else ""
            stop = f"<div>{self.blocker_link(first)}{where}</div>"
        else:
            stop = '<span class="muted">None known</span>'
        then = "".join(f"<li>{self.blocker_link(self.blockers[s['id']])}</li>" for s in steps[1:])
        then = f'<ol class="then">{then}</ol>' if then else '<span class="muted">—</span>'
        best = t.get("best_stage")
        if best and best.get("url"):
            where = " · ".join(x for x in (best.get("os"), best.get("gpu")) if x)
            source = (
                f"{ext(best['url'], esc(source_label(best['url'], self.repo)))}"
                f"{f'<span class=note>{esc(where)}</span>' if where else ''}"
            )
        else:
            source = '<span class="muted">—</span>'
        source = f'<div>{source}<span class="note">{self.game_report(t)}</span></div>'
        meta = [f'<span class="mono">{esc(t["id"])}</span>'] + [esc(x) for x in (t.get("engine"), t.get("kind")) if x]
        words = [t.get("name"), t["id"], t.get("engine"), t.get("kind")]
        for s in steps:
            b = self.blockers[s["id"]]
            words += [b["title"], self.ref(b), self.ref(b).replace("PR ", ""), b.get("signature")]
        search = " ".join(w for w in words if w).lower()
        return f"""<tr class="game" id="g-{esc(t["id"])}" data-stage="{slug(stage) if stage else "none"}" data-search="{esc(search)}">
<td data-label="Game"><span class="g-name">{esc(t.get("name") or t["id"])}</span><span class="meta">{" · ".join(meta)}</span></td>
<td data-label="Stage"><div><span class="stage">{self.pips(stage)}<span>{esc(stage or "No stage yet")}</span></span>{reports}{claim_html}</div></td>
<td data-label="Stops at">{stop}</td>
<td data-label="Then">{then}</td>
<td data-label="Source">{source}</td>
</tr>"""

    def games_section(self) -> str:
        ordered = sorted(
            self.listed, key=lambda t: (-self.stage_rank.get(self.stage_of(t), -1), (t.get("name") or t["id"]).lower())
        )
        counts: dict[str, int] = {}
        for t in ordered:
            k = slug(self.stage_of(t)) if self.stage_of(t) else "none"
            counts[k] = counts.get(k, 0) + 1
        chips = [("all", "All", len(ordered))] + [(slug(s), s, counts.get(slug(s), 0)) for s in reversed(self.stages)]
        chips.append(("none", "No stage yet", counts.get("none", 0)))
        chip_html = "".join(
            f'<label class="chip"><input type="radio" name="stage" value="{k}"{" checked" if k == "all" else ""}>'
            f'{esc(label)}<span class="chip-n">{n}</span></label>'
            for k, label, n in chips
            if n
        )
        rows = "".join(self.game_row(t) for t in ordered)
        games = len({self.title_name(t["id"]) for t in ordered})
        return f"""<section id="games" class="sec" aria-labelledby="h-games">
  <div class="sec-head">
    <h2 id="h-games">Games</h2>
    <p class="intro">{plural(games, "game")} in {plural(len(ordered), "title ID")}: the highest stage confirmed for each,
    where it stops now and what it hits after that.</p>
  </div>
  <div class="toolbar js-only">
    <label class="search">{SEARCH}<span class="sr-only">Search games and errors</span>
      <input id="q" type="search" placeholder="Paste a log line, a game or a PPSA ID" autocomplete="off" spellcheck="false">
      <kbd aria-hidden="true">/</kbd></label>
    <fieldset class="chips"><legend class="sr-only">Filter by stage</legend>{chip_html}</fieldset>
  </div>
  <p class="result js-only" id="count" role="status"></p>
  <table class="games" id="games-table" data-games="{games}">
    <thead><tr><th scope="col">Game</th><th scope="col">Stage</th><th scope="col">Stops at</th><th scope="col">Then</th><th scope="col">Source</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <div class="empty" id="empty" hidden>
    <p class="empty-title" id="empty-title">No title IDs match</p>
    <p class="muted">Try a game name, a PPSA ID, an engine such as Unity, an issue number or part of an error line.</p>
    <button type="button" class="btn" id="clear">Clear filters</button>
  </div>
</section>"""

    # -- coverage ------------------------------------------------------------

    @staticmethod
    def band(top: float, height: float, first: int, count: int, cols: int, done: int, cell: float) -> str:
        """A run of full grid rows holding cells [first, first + count); cells from `done` on are missing."""
        rows = math.ceil(count / cols)
        miss = "".join(
            f'<i style="left:{100 * c / cols:.3f}%;top:{100 * r / rows:.3f}%;'
            f'width:{100 * nc / cols:.3f}%;height:{100 * nr / rows:.3f}%"></i>'
            for c, r, nc, nr in cell_runs(max(done - first, 0), count, cols)
        )
        grid = " grid" if cell >= 3.2 else ""
        return (
            f'<div class="tm-band{grid}" style="top:{top:.3f}%;height:{height:.3f}%;--c:{cols};--r:{rows}">{miss}</div>'
        )

    def treemap(self, groups: list[dict], name_key: str, width: float, height: float, unit: str) -> str:
        """One treemap like upstream's progress map: a tile per group, a cell per function.

        The last row is stretched to the tile width, so every cell is a function and no slot stays empty."""
        items = sorted(((g["done"] + g["todo"], g) for g in groups if g["done"] + g["todo"]), key=lambda it: -it[0])
        tiles = []
        for g, x, y, w, h in squarify(items, 0, 0, width, height):
            n = g["done"] + g["todo"]
            cols, rows = grid_for(n, w, h)
            full = n if rows * cols == n else (rows - 1) * cols
            cell = min(w / cols, h / rows)
            bands = self.band(0, 100 * (full // cols) / rows, 0, full, cols, g["done"], cell) if full else ""
            if full < n:
                bands += self.band(100 * (rows - 1) / rows, 100 / rows, full, n - full, n - full, g["done"], cell)
            asked = g.get("requested") or {}
            missing = [
                f"{m} (asked in {', '.join(f'#{i}' for i in asked[m])})" if m in asked else m
                for m in sorted(g.get("todo_names") or [], key=lambda m: (m not in asked, m))
            ]
            label = g.get(name_key) or g.get("label") or "?"
            tiles.append(
                f'<div class="tm-tile" style="left:calc({100 * x / width:.3f}% + 1.5px);'
                f"top:calc({100 * y / height:.3f}% + 1.5px);width:calc({100 * w / width:.3f}% - 3px);"
                f'height:calc({100 * h / height:.3f}% - 3px)" '
                f'data-name="{esc(label)}" data-done="{g["done"]}" data-total="{n}" data-unit="{unit}" '
                f'data-missing="{esc(chr(10).join(missing))}">{bands}<span class="tm-l">{esc(label)}</span></div>'
            )
        return "".join(tiles)

    def issue_link(self, n: int) -> str:
        b = self.blockers.get(str(n))
        href = self.blocker_href(b) if b else f"https://github.com/{self.repo}/issues/{n}"
        return f'<a class="mono" href="{esc(href)}">#{n}</a>'

    def coverage(self) -> str:
        cov = self.doc.get("coverage") or {}
        isa, hle, pm4 = cov.get("isa"), cov.get("hle"), cov.get("pm4")
        parts = []
        if hle and hle.get("total"):
            libs = [g for g in hle.get("groups", []) if g["done"] + g["todo"]]
            name = lambda g: g.get("label") or g["library"]  # noqa: E731
            lib_rows = "".join(
                f'<li><span class="lib">{esc(name(g))}</span><span class="mono muted">{g["done"]}/{g["done"] + g["todo"]}</span>'
                f'<span class="fns">{", ".join(esc(m) for m in sorted(g.get("todo_names") or []))}</span></li>'
                for g in sorted(libs, key=lambda g: (-g["todo"], name(g).lower()))
                if g["todo"]
            )
            asked = sorted(
                ((f, name(g), iss) for g in libs for f, iss in (g.get("requested") or {}).items()),
                key=lambda r: (-len(r[2]), r[1].lower(), r[0]),
            )
            asked_rows = "".join(
                f'<tr><td class="mono">{esc(f)}</td><td>{esc(lib)}</td>'
                f"<td>{' '.join(self.issue_link(i) for i in iss)}</td></tr>"
                for f, lib, iss in asked
            )
            asked_html = (
                f'<details class="rows"><summary><span class="rank">{len(asked)}</span>'
                f"<span>Missing functions that open issues ask for</span>{CHEVRON}</summary>"
                f'<table class="asked"><thead><tr><th scope="col">Function</th><th scope="col">Library</th>'
                f'<th scope="col">Asked in</th></tr></thead><tbody>{asked_rows}</tbody></table></details>'
                if asked
                else ""
            )
            enc = [g for g in (isa or {}).get("groups", []) if g["done"] + g["todo"]]
            pct = 100 * hle["done"] / hle["total"]
            lib_label = (
                f"Treemap of {len(libs)} system libraries, {hle['done']:,} of {hle['total']:,} functions implemented"
            )
            shader_panel = ""
            if enc and isa.get("total"):
                spct = 100 * isa["done"] / isa["total"]
                isa_label = (
                    f"Treemap of {len(enc)} shader instruction encodings, {isa['done']:,} of "
                    f"{isa['total']:,} instructions decoded"
                )
                shader_panel = f"""<div class="tm-panel">
        <h3 class="tm-sub">GPU shader instructions <span class="tm-n">{isa["done"]:,} of {isa["total"]:,} · {spct:.0f}%</span></h3>
        <div class="tm-area tm-wide" style="aspect-ratio:360/330" role="img" aria-label="{isa_label}">
          {self.treemap(enc, "encoding", 360, 330, "instructions")}</div>
        <div class="tm-area tm-narrow" style="aspect-ratio:400/280" role="img" aria-label="{isa_label}">
          {self.treemap(enc, "encoding", 400, 280, "instructions")}</div>
      </div>"""
            parts.append(f"""<figure class="tm" aria-labelledby="tm-cap">
    <figcaption class="tm-head">
      <span id="tm-cap" class="tm-title">Coverage map</span>
      <span class="tm-legend" aria-hidden="true"><i class="lg-done"></i>Implemented<i class="lg-miss"></i>Missing</span>
      <span class="tm-hint">One cell per function or instruction. Point at a block, or open the lists below.</span>
    </figcaption>
    <div class="tm-panels{" two" if shader_panel else ""}">
      <div class="tm-panel">
        <h3 class="tm-sub">System library functions <span class="tm-n">{hle["done"]:,} of {hle["total"]:,} · {pct:.0f}%</span></h3>
        <div class="tm-area tm-wide" style="aspect-ratio:{640 if shader_panel else 1000}/330" role="img" aria-label="{lib_label}">
          {self.treemap(libs, "label", 640 if shader_panel else 1000, 330, "functions")}</div>
        <div class="tm-area tm-narrow" style="aspect-ratio:400/440" role="img" aria-label="{lib_label}">
          {self.treemap(libs, "label", 400, 440, "functions")}</div>
      </div>
      {shader_panel}
    </div>
    <div class="tm-tip" id="tm-tip" aria-hidden="true" hidden></div>
  </figure>
  {asked_html}
  <details class="rows"><summary><span class="rank">{sum(1 for g in libs if g["todo"])}</span>
    <span>Libraries with missing functions, and their names</span>{CHEVRON}</summary>
    <ul class="libs">{lib_rows}</ul></details>""")
        lines = []
        if pm4 and pm4.get("total"):
            c, total = pm4["counts"], pm4["total"]
            rejected = [
                r["name"] for r in pm4.get("rows", []) if r.get("status") == "rejected" and r.get("kind") == "type-3"
            ]
            rej = f' Rejected: <span class="mono">{", ".join(esc(n) for n in rejected)}</span>.' if rejected else ""
            lines.append(
                f'<li><span class="cv-name">GPU command packets (PM4)</span><span class="cv-bar" aria-hidden="true">'
                f'<i style="width:{100 * c.get("handled", 0) / total:.2f}%"></i>'
                f'<i class="part" style="width:{100 * c.get("conditional", 0) / total:.2f}%"></i></span>'
                f"<span>{c.get('handled', 0)} of {total} handled, {c.get('conditional', 0)} in part.{rej}</span></li>"
            )
        if lines:
            parts.append(f'<ul class="cv-lines">{"".join(lines)}</ul>')
        if not parts:
            return ""
        return f"""<section id="coverage" class="sec" aria-labelledby="h-cov">
  <div class="sec-head">
    <h2 id="h-cov">Coverage</h2>
    <p class="intro">What AnyPS5 implements of the PS5's system libraries and GPU. Same data as the project's own
    {ext("https://boykopovar.github.io/AnyPS5/", "progress page")}.</p>
  </div>
  {"".join(parts)}
</section>"""

    # -- data ----------------------------------------------------------------

    def footer(self) -> str:
        gaps = "".join(f"<li>{esc(g)}</li>" for g in self.doc.get("gaps", []))
        rows = []
        for f, purpose in FILES:
            size = ""
            if self.site and (self.site / f).exists():
                size = fmt_size((self.site / f).stat().st_size)
            rows.append(
                f'<div class="file"><dt><a class="mono" href="{f}">{f}</a></dt>'
                f'<dd class="muted mono">{size}</dd><dd>{purpose}</dd></div>'
            )
        return f"""<footer id="data" class="sec" aria-labelledby="h-data">
  <div class="sec-head">
    <h2 id="h-data">Data</h2>
    <p class="intro">Regenerated from GitHub by roadmap.py. Corrections go into data/blockers.json, which always wins over mined text.</p>
  </div>
  <dl class="files">{"".join(rows)}</dl>
  <details class="rows"><summary><span class="rank">{len(self.doc.get("gaps", []))}</span>
    <span>Known gaps in the data</span>{CHEVRON}</summary><ul class="gaps">{gaps}</ul></details>
  <p class="fine">Built from public GitHub data of {ext(f"https://github.com/{self.repo}", esc(self.repo))}.
  Some stages and links come from keyword rules over issue text and can be wrong, so every one links its source.
  A community prototype, not an official AnyPS5 page. Snapshot {esc(fmt_time(self.doc["generated_at"]))}.</p>
</footer>"""

    def render(self) -> str:
        return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AnyPS5 blocker map</title>
<meta name="description" content="Which open issues stop PS5 games in AnyPS5, the PS5 executable porting tool, ranked by how many games a fix moves.">
<meta name="color-scheme" content="light dark">
<link rel="preload" href="fonts/Geist-Variable.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="fonts/GeistPixel-Square.woff2" as="font" type="font/woff2" crossorigin>
<link rel="alternate" type="application/json" href="roadmap.json">
<link rel="alternate" type="application/feed+json" href="feed.json" title="AnyPS5 blocker map: changes">
<link rel="alternate" type="text/plain" href="llms.txt" title="llms.txt">
<script>try{{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}}catch(e){{}}document.documentElement.classList.add("js")</script>
<style>{CSS}</style>
</head>
<body>
<a class="skip" href="#fix-next">Skip to the ranking</a>
{self.topbar()}
<main id="top" class="wrap">
{self.hero()}
{self.fix_next()}
{self.games_section()}
{self.coverage()}
{self.footer()}
</main>
<script>{JS}</script>
</body>
</html>
"""


JS = r"""
(function(){
var d=document,root=d.documentElement;
function $(s){return d.querySelector(s)}function $$(s){return [].slice.call(d.querySelectorAll(s))}

/* theme: system, light, dark */
var tb=$("#theme"),tv=$("#theme-v"),modes=["system","light","dark"];
function mode(){return root.dataset.theme||"system"}
function label(){tv.textContent=mode().charAt(0).toUpperCase()+mode().slice(1)}
tb.hidden=false;label();
tb.addEventListener("click",function(){var next=modes[(modes.indexOf(mode())+1)%3],s=d.createElement("style");
  s.textContent="*,*::before,*::after{transition:none!important}";d.head.appendChild(s);
  if(next==="system")delete root.dataset.theme;else root.dataset.theme=next;
  try{if(next==="system")localStorage.removeItem("theme");else localStorage.setItem("theme",next)}catch(e){}
  getComputedStyle(root).color;requestAnimationFrame(function(){requestAnimationFrame(function(){s.remove()})});label()});

/* blocker list with a side panel on wide screens */
var wide=matchMedia("(min-width: 1100px)"),panel=$("#panel"),status=$("#sel-status"),rows=$$(".blocker"),cur=null;
function select(li,write,focus){if(!li)return;cur=li;
  rows.forEach(function(r){var s=r.querySelector("summary");if(r===li)s.setAttribute("aria-current","true");else s.removeAttribute("aria-current")});
  var c=d.createElement("div");c.className="panel-in";c.innerHTML=li.querySelector(".body").innerHTML;panel.replaceChildren(c);panel.scrollTop=0;
  var rk=li.querySelector(".rank");status.textContent="Showing "+(rk?"No. "+rk.textContent+": ":"")+li.querySelector(".name").textContent;
  if(write)history.replaceState(null,"","#"+li.id);if(focus)panel.focus({preventScroll:true})}
rows.forEach(function(r){var s=r.querySelector("summary");
  s.addEventListener("click",function(e){if(!wide.matches)return;e.preventDefault();select(r,true,e.detail===0)});
  s.addEventListener("keydown",function(e){if(!wide.matches||(e.key!=="ArrowDown"&&e.key!=="ArrowUp"))return;
    var vis=rows.filter(function(x){return x.offsetParent!==null}),n=vis[vis.indexOf(r)+(e.key==="ArrowDown"?1:-1)];
    if(n){e.preventDefault();n.querySelector("summary").focus();select(n,true,false)}})});
function layout(){panel.hidden=!wide.matches;
  rows.forEach(function(r){var s=r.querySelector("summary");if(wide.matches)s.setAttribute("aria-controls","panel");else s.removeAttribute("aria-controls")});
  if(wide.matches){rows.forEach(function(r){r.querySelector("details").open=false});if(!cur)select(rows[0],false,false)}}
wide.addEventListener("change",layout);layout();

/* games: search and stage filter */
var q=$("#q"),games=$$("tr.game"),radios=$$("input[name=stage]"),count=$("#count"),empty=$("#empty"),table=$("#games-table");
function stage(){var r=radios.filter(function(x){return x.checked})[0];return r?r.value:"all"}
function setStage(v){var hit=false;radios.forEach(function(x){x.checked=x.value===v;hit=hit||x.checked});if(!hit)radios[0].checked=true}
function apply(){var term=q.value.trim().toLowerCase(),st=stage(),n=0,names={};
  games.forEach(function(g){var ok=(st==="all"||g.dataset.stage===st)&&(!term||g.dataset.search.indexOf(term)>=0);g.hidden=!ok;
    if(ok){n++;names[g.querySelector(".g-name").textContent]=1}});
  var k=Object.keys(names).length;
  count.textContent=(n===games.length?"All ":"")+n+" title IDs, "+k+" games";empty.hidden=n>0;table.hidden=n===0;
  if(!n){var where=st==="all"?"":" in "+radios.filter(function(x){return x.checked})[0].parentNode.firstChild.textContent;
    $("#empty-title").textContent="No title IDs match"+(term?" “"+q.value.trim()+"”":"")+where}}
radios.forEach(function(r){r.addEventListener("change",apply)});
q.addEventListener("input",apply);q.addEventListener("keydown",function(e){if(e.key==="Escape"&&q.value){q.value="";apply()}});
$("#clear").addEventListener("click",function(){q.value="";setStage("all");apply();q.focus()});
$$("[data-stage-link]").forEach(function(a){a.addEventListener("click",function(){setStage(a.dataset.stageLink);q.value="";apply()})});
addEventListener("keydown",function(e){var t=(d.activeElement||{}).tagName||"";
  if(e.key==="/"&&!e.ctrlKey&&!e.metaKey&&!e.altKey&&!/INPUT|TEXTAREA|SELECT/.test(t)){e.preventDefault();q.focus()}});
apply();

/* coverage map tooltip (the lists under the map carry the same names) */
var tip=$("#tm-tip");
if(tip){$$(".tm-tile").forEach(function(t){
  t.addEventListener("pointerenter",function(){var miss=t.dataset.missing?t.dataset.missing.split("\n"):[],done=+t.dataset.done,total=+t.dataset.total;
    tip.replaceChildren();var b=d.createElement("b");b.textContent=t.dataset.name;tip.appendChild(b);
    var n=d.createElement("div");n.className="tt-n";n.textContent=done+" of "+total+" "+t.dataset.unit+(miss.length?", "+miss.length+" missing":"");tip.appendChild(n);
    miss.slice(0,8).forEach(function(m){var e=d.createElement("div");e.className="tt-m";e.textContent=m;tip.appendChild(e)});
    if(miss.length>8){var e=d.createElement("div");e.className="tt-n";e.textContent="and "+(miss.length-8)+" more";tip.appendChild(e)}
    tip.hidden=false});
  t.addEventListener("pointermove",function(e){var w=tip.offsetWidth,h=tip.offsetHeight,x=e.clientX+14,y=e.clientY+14;
    if(x+w>innerWidth-8)x=e.clientX-w-14;if(y+h>innerHeight-8)y=e.clientY-h-14;tip.style.left=Math.max(8,x)+"px";tip.style.top=Math.max(8,y)+"px"});
  t.addEventListener("pointerleave",function(){tip.hidden=true})})}

/* in-page links into closed disclosures */
function reveal(){var id=decodeURIComponent(location.hash.slice(1)),t=id&&d.getElementById(id);if(!t)return;
  for(var e=t.parentElement;e;e=e.parentElement){if(e.tagName==="DETAILS")e.open=true}
  if(t.classList.contains("blocker")){if(wide.matches)select(t,false,false);else t.querySelector("details").open=true}
  if(t.classList.contains("game")&&t.hidden){q.value="";setStage("all");apply()}
  t.scrollIntoView({block:"start"})}
addEventListener("hashchange",reveal);reveal();

/* current section in the top bar */
var links=$$(".nav a");
if("IntersectionObserver" in window){var io=new IntersectionObserver(function(es){es.forEach(function(en){if(!en.isIntersecting)return;
  links.forEach(function(l){if(l.getAttribute("href")==="#"+en.target.id)l.setAttribute("aria-current","true");else l.removeAttribute("aria-current")})})},
  {rootMargin:"-35% 0px -60% 0px"});
  ["fix-next","games","coverage","data"].forEach(function(id){var s=d.getElementById(id);if(s)io.observe(s)})}
})();
"""

CSS = r"""
@font-face{font-family:Geist;src:url(fonts/Geist-Variable.woff2) format("woff2");font-weight:100 900;font-display:swap}
@font-face{font-family:"Geist Mono";src:url(fonts/GeistMono-Variable.woff2) format("woff2");font-weight:100 900;font-display:swap}
@font-face{font-family:"Geist Pixel";src:url(fonts/GeistPixel-Square.woff2) format("woff2");font-display:swap}
:root{
  color-scheme:light;
  --bg:oklch(0.985 0 0);--surface:oklch(0.998 0 0);--hover:oklch(0.955 0 0);--selected:oklch(0.955 0 0);--code:oklch(0.955 0 0);
  --line:oklch(0.915 0 0);--line-strong:oklch(0.62 0 0);--track:oklch(0.925 0 0);
  --text:oklch(0.21 0 0);--text-2:oklch(0.45 0 0);--text-3:oklch(0.53 0 0);
  --ok:oklch(0.62 0.16 149);--ok-part:oklch(0.82 0.09 149);--miss:oklch(0.86 0 0);--grid:oklch(0.998 0 0 / 0.7);
  --sans:Geist,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"Geist Mono",ui-monospace,"Cascadia Mono",Consolas,monospace;
  --pixel:"Geist Pixel","Geist Mono",ui-monospace,monospace;
  --fs-xs:12px;--fs-s:13px;--fs-m:15px;--fs-l:17px;--fs-xl:22px;
  --ease:cubic-bezier(0.2,0,0,1);--ease-out:cubic-bezier(0.23,1,0.32,1);
  --bar-h:60px;--gutter:clamp(16px,3.2vw,56px);
  --cols:minmax(0,1.25fr) minmax(0,1fr);--col-gap:clamp(32px,3vw,56px);
}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
  color-scheme:dark;
  --bg:oklch(0.16 0 0);--surface:oklch(0.195 0 0);--hover:oklch(0.235 0 0);--selected:oklch(0.235 0 0);--code:oklch(0.235 0 0);
  --line:oklch(0.29 0 0);--line-strong:oklch(0.55 0 0);--track:oklch(0.27 0 0);
  --text:oklch(0.95 0 0);--text-2:oklch(0.76 0 0);--text-3:oklch(0.67 0 0);
  --ok:oklch(0.63 0.16 149);--ok-part:oklch(0.45 0.09 149);--miss:oklch(0.43 0 0);--grid:oklch(0.195 0 0 / 0.75);
}}
:root[data-theme=dark]{
  color-scheme:dark;
  --bg:oklch(0.16 0 0);--surface:oklch(0.195 0 0);--hover:oklch(0.235 0 0);--selected:oklch(0.235 0 0);--code:oklch(0.235 0 0);
  --line:oklch(0.29 0 0);--line-strong:oklch(0.55 0 0);--track:oklch(0.27 0 0);
  --text:oklch(0.95 0 0);--text-2:oklch(0.76 0 0);--text-3:oklch(0.67 0 0);
  --ok:oklch(0.63 0.16 149);--ok-part:oklch(0.45 0.09 149);--miss:oklch(0.43 0 0);--grid:oklch(0.195 0 0 / 0.75);
}
*,*::before,*::after{box-sizing:border-box}
[hidden]{display:none!important}
html{-webkit-text-size-adjust:100%;scroll-padding-top:calc(var(--bar-h) + 16px)}
@media (prefers-reduced-motion:no-preference){html{scroll-behavior:smooth}}
body{margin:0;background:var(--bg);color:var(--text);font:400 var(--fs-m)/1.55 var(--sans);
  -webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;font-optical-sizing:auto}
.wrap{width:100%;max-width:1760px;margin-inline:auto;padding-inline:var(--gutter)}
a{color:inherit;text-decoration-line:underline;text-decoration-color:color-mix(in oklab,currentColor 35%,transparent);
  text-decoration-thickness:from-font;text-underline-offset:0.2em;text-decoration-skip-ink:auto;transition:text-decoration-color 150ms ease}
@media (hover:hover){a:hover{text-decoration-color:currentColor}}
:focus-visible{outline:2px solid var(--text);outline-offset:2px;border-radius:6px}
p{margin:0}
h1,h2,h3{margin:0;text-wrap:balance}
button{font:inherit;color:inherit}
.mono{font-family:var(--mono);font-size:0.92em;font-variant-numeric:tabular-nums}
.muted{color:var(--text-3)}
.small{font-size:var(--fs-s)}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}
.js-only{display:none}
.js .js-only{display:flex}
.js p.js-only{display:block}
.skip{position:fixed;inset-inline-start:16px;top:-64px;z-index:20;padding:10px 14px;border-radius:10px;
  background:var(--text);color:var(--bg);text-decoration:none;font-weight:550}
.skip:focus{top:12px}

/* top bar */
.bar{position:sticky;top:0;z-index:10;height:var(--bar-h);border-bottom:1px solid var(--line);background:var(--bg)}
.bar-in{height:100%;display:flex;align-items:center;gap:32px}
.brand{display:flex;align-items:baseline;gap:10px;text-decoration:none;white-space:nowrap}
.brand-mark{font-family:var(--pixel);font-size:19px}
.brand-sub{font-size:var(--fs-s);color:var(--text-2)}
.nav{display:flex;gap:4px;font-size:var(--fs-s);font-weight:550}
.nav a{position:relative;padding:8px 12px;border-radius:8px;color:var(--text-2);text-decoration:none;white-space:nowrap;
  transition:color 150ms ease,background-color 150ms ease}
@media (hover:hover){.nav a:hover{color:var(--text);background:var(--hover)}}
.nav a[aria-current]{color:var(--text)}
.nav a[aria-current]::after{content:"";position:absolute;inset-inline:12px;bottom:-11px;height:2px;background:var(--text);border-radius:2px}
.bar-end{margin-inline-start:auto;display:flex;align-items:center;gap:16px}
.snap{font-size:var(--fs-s);color:var(--text-3);white-space:nowrap}
.theme,.gh{min-height:36px;padding:0 12px;border:1px solid var(--line-strong);border-radius:8px;background:none;
  font-size:var(--fs-s);cursor:pointer;white-space:nowrap;transition:background-color 150ms ease,scale 160ms var(--ease-out)}
.gh{display:inline-flex;align-items:center;gap:8px;color:var(--text);font-weight:550;text-decoration:none}
.gh-mark{flex:none;display:block}
@media (hover:hover){.theme:hover,.gh:hover{background:var(--hover)}}
.theme:active,.gh:active{scale:0.96}

/* hero: the stage ladder */
.hero{padding-block:clamp(40px,5vw,80px) 0}
h1{font-size:clamp(34px,4.2vw,64px);line-height:1.04;letter-spacing:-0.035em;font-weight:650}
.lead{margin-top:16px;font-size:var(--fs-l);line-height:1.5;color:var(--text-2);max-width:52em;text-wrap:pretty}
.ladder{list-style:none;margin:48px 0 0;padding:0;display:grid;grid-template-columns:repeat(8,minmax(0,1fr))}
.ladder li{position:relative;border-top:2px solid var(--text)}
.ladder li::before{content:"";position:absolute;top:-7px;inset-inline-start:0;width:2px;height:12px;background:var(--text)}
.rung{display:grid;gap:8px;align-content:start;height:100%;padding:16px 16px 20px 12px;text-decoration:none;
  border-radius:0 0 12px 12px;transition:background-color 150ms ease}
@media (hover:hover){a.rung:hover{background:var(--hover)}}
.r-n{font-family:var(--pixel);font-size:clamp(34px,3vw,48px);line-height:1;font-variant-numeric:tabular-nums}
.r-name{font-weight:650}
.r-def{font-size:var(--fs-xs);line-height:1.45;color:var(--text-3);text-wrap:pretty}
.r-top{font-size:var(--fs-xs);color:var(--text-2)}
.zero .r-n,.zero .r-name{color:var(--text-3)}
.ladder-note{margin-top:16px;font-size:var(--fs-s);color:var(--text-3)}
.pips{display:inline-flex;gap:2px}
.pips i{width:5px;height:12px;border-radius:1px;background:var(--track)}
.pips i.on{background:var(--text)}

/* sections */
.sec{padding-top:clamp(64px,7vw,112px)}
.sec-head{display:grid;gap:8px;padding-bottom:24px}
h2{font-size:clamp(28px,2.4vw,36px);line-height:1.1;letter-spacing:-0.025em;font-weight:650}
.intro{color:var(--text-2);max-width:62em;text-wrap:pretty}

/* fix next */
.split{display:grid;grid-template-columns:minmax(0,1fr);gap:40px}
.blockers{list-style:none;margin:0;padding:0;border-top:1px solid var(--line)}
.blocker{border-bottom:1px solid var(--line)}
.blocker summary,details.rows>summary{display:grid;grid-template-columns:2.5em minmax(0,1fr) auto 16px;gap:4px 20px;align-items:start;
  padding:16px 14px;margin-inline:-14px;border-radius:12px;cursor:pointer;list-style:none;transition:background-color 150ms ease}
details.rows>summary{grid-template-columns:2.5em minmax(0,1fr) 16px;font-weight:550}
.plain .blocker summary{grid-template-columns:minmax(0,1fr) 16px}
.blocker summary::-webkit-details-marker,details.rows>summary::-webkit-details-marker{display:none}
@media (hover:hover){.blocker summary:hover,details.rows>summary:hover{background:var(--hover)}}
.blocker summary[aria-current]{background:var(--selected)}
.blocker summary[aria-current] .rank{color:var(--text);font-weight:650}
details.rows{border-bottom:1px solid var(--line)}
details.rows>.blockers{border-top:1px solid var(--line)}
.rank{font-family:var(--mono);font-size:var(--fs-s);color:var(--text-3);padding-top:2px;font-variant-numeric:tabular-nums;white-space:nowrap}
.what{display:grid;gap:4px;min-width:0}
.name{font-weight:550;line-height:1.35;text-wrap:pretty;overflow-wrap:break-word}
.meta{font-size:var(--fs-s);color:var(--text-3);overflow-wrap:break-word}
.sig-line{font-family:var(--mono);font-size:var(--fs-xs);color:var(--text-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.status{color:var(--text-2)}
.status i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-inline-end:6px;vertical-align:0;border:1.5px solid currentColor}
.s-review i{background:currentColor}
.s-partial i{background:linear-gradient(90deg,currentColor 50%,transparent 50%)}
.impact{display:grid;justify-items:end;gap:6px;padding-top:3px}
.count{font-size:var(--fs-s);color:var(--text-3);white-space:nowrap;font-variant-numeric:tabular-nums}
.count b{color:var(--text);font-weight:650}
.dots{display:flex;gap:3px;align-items:center}
.dots i{width:8px;height:8px;border-radius:50%;border:1.5px solid var(--text-2)}
.dots i.on{background:var(--text);border-color:var(--text)}
.more-dots{font-size:var(--fs-xs);color:var(--text-3);margin-inline-start:2px}
.chev{color:var(--text-3);margin-top:3px;transition:transform 150ms var(--ease)}
details[open]>summary .chev{transform:rotate(90deg)}
.body{padding:4px 0 24px calc(2.5em + 20px);display:grid;gap:18px}
.plain .body{padding-inline-start:0}
.blocker .p-head{display:none}
.body dl,.panel dl{display:grid;grid-template-columns:8.5em minmax(0,1fr);gap:14px 20px;margin:0}
.body dt{font-size:var(--fs-s);color:var(--text-3);padding-top:2px}
.body dd{margin:0;min-width:0;display:grid;gap:6px;overflow-wrap:break-word}
.after{list-style:none;margin:0;padding:0;display:grid;gap:4px}
.b-link .b-name{color:var(--text-2)}
.sig{margin:0;padding:12px 14px;border-radius:10px;background:var(--code);font:var(--fs-s)/1.55 var(--mono);
  white-space:pre-wrap;overflow-wrap:anywhere;color:var(--text-2)}
.prs{list-style:none;margin:0;padding:0;display:grid;gap:12px}
.prs li{display:grid;gap:2px;overflow-wrap:break-word}
.pr-note{font-size:var(--fs-s);color:var(--text-3)}
.out{font-size:var(--fs-s)}
.report{color:var(--text-3);white-space:nowrap}
.note .report{display:inline-block;padding-block:3px}
.out .tail{white-space:nowrap}
.panel{position:sticky;top:calc(var(--bar-h) + 24px);max-height:calc(100dvh - var(--bar-h) - 48px);overflow:auto;
  overscroll-behavior:contain;padding:28px 28px 24px;border:1px solid var(--line);border-radius:16px;background:var(--surface);scrollbar-width:thin}
.panel-in{display:grid;gap:20px;transition:opacity 180ms var(--ease-out),translate 180ms var(--ease-out)}
@starting-style{.panel-in{opacity:0;translate:0 6px}}
.panel .p-head{display:grid;gap:8px;padding-bottom:20px;border-bottom:1px solid var(--line)}
.panel h3{font-size:var(--fs-xl);line-height:1.25;letter-spacing:-0.015em;font-weight:650;text-wrap:balance}
.panel dl{grid-template-columns:minmax(0,1fr);gap:6px}
.panel dt{font-size:var(--fs-s);color:var(--text-3);padding-top:10px}
.panel dt:first-child{padding-top:0}
.panel dd{margin:0;display:grid;gap:6px;overflow-wrap:break-word}

/* games */
.toolbar{flex-wrap:wrap;gap:12px 16px;align-items:center}
.search{position:relative;display:flex;align-items:center;flex:1 1 320px;max-width:480px;color:var(--text-3)}
.search svg{position:absolute;inset-inline-start:14px;pointer-events:none}
.search input{width:100%;min-height:44px;padding:0 40px;border:1px solid var(--line-strong);border-radius:12px;
  background:var(--surface);color:var(--text);font:inherit;font-size:16px}
.search input::placeholder{color:var(--text-3)}
.search input:focus-visible{outline:2px solid var(--text);outline-offset:1px;border-radius:12px}
.search kbd{position:absolute;inset-inline-end:10px;padding:1px 7px;border:1px solid var(--line);border-radius:6px;
  font:var(--fs-xs)/1.5 var(--mono);color:var(--text-3)}
.search input:focus~kbd,.search input:not(:placeholder-shown)~kbd{display:none}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:0;padding:0;border:0;min-width:0}
.chip{position:relative;display:inline-flex;align-items:center;gap:8px;min-height:36px;padding:0 12px;border:1px solid var(--line-strong);
  border-radius:999px;background:var(--surface);font-size:var(--fs-s);font-weight:550;cursor:pointer;
  transition:background-color 150ms ease,scale 160ms var(--ease-out)}
.chip input{position:absolute;opacity:0;inset:0;margin:0;cursor:pointer}
@media (hover:hover){.chip:hover{background:var(--hover)}}
.chip:active{scale:0.96}
.chip:has(input:focus-visible){outline:2px solid var(--text);outline-offset:2px}
.chip-n{font-variant-numeric:tabular-nums;color:var(--text-3);font-weight:400}
.chip:has(input:checked){background:var(--text);border-color:var(--text);color:var(--bg)}
.chip:has(input:checked) .chip-n{color:color-mix(in oklab,var(--bg) 70%,var(--text))}
.result{padding-top:16px;font-size:var(--fs-s);color:var(--text-3)}
table.games{width:100%;margin-top:16px;border-collapse:collapse;font-size:var(--fs-s)}
.games thead th{position:sticky;top:var(--bar-h);z-index:1;background:var(--bg);text-align:start;font-size:var(--fs-xs);font-weight:550;
  color:var(--text-3);padding:10px 16px 10px 0;border-bottom:1px solid var(--line)}
.games td{padding:14px 16px 14px 0;border-bottom:1px solid var(--line);vertical-align:top;overflow-wrap:break-word}
.games th:nth-child(1){width:20%}.games th:nth-child(2){width:14%}.games th:nth-child(3){width:28%}
.games th:nth-child(4){width:24%}.games th:nth-child(5){width:14%}
@media (hover:hover){.games tbody tr{transition:background-color 150ms ease}.games tbody tr:hover{background:var(--hover)}}
.games tr:target td{background:var(--selected)}
@media (min-width:861px){.games tr{scroll-margin-top:24px}}  /* a jump to a row clears the sticky table header */
.g-name{display:block;font-size:var(--fs-m);font-weight:550}
.games .meta{display:block;margin-top:2px}
.stage{display:flex;align-items:center;gap:10px;white-space:nowrap}
.note{display:block;margin-top:4px;font-size:var(--fs-xs);color:var(--text-3)}
.note a{white-space:nowrap}
.then{list-style:none;margin:0;padding:0;display:grid;gap:4px}
.then li,.games td:nth-child(3) .b-link{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.games td:nth-child(3) .b-link{white-space:normal}
.empty{display:grid;justify-items:start;gap:8px;padding:48px 0}
.empty-title{font-size:var(--fs-l);font-weight:550}
.btn{display:inline-flex;align-items:center;min-height:44px;margin-top:8px;padding:0 18px;border-radius:12px;border:1px solid var(--line-strong);
  background:var(--surface);font-weight:550;cursor:pointer;transition:background-color 150ms ease,scale 160ms var(--ease-out)}
@media (hover:hover){.btn:hover{background:var(--hover)}}
.btn:active{scale:0.96}

/* coverage */
.tm{margin:0;padding:24px;border:1px solid var(--line);border-radius:16px;background:var(--surface)}
.tm-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 24px;padding-bottom:20px}
.tm-title{font-size:var(--fs-l);font-weight:650}
.tm-panels{display:grid;grid-template-columns:minmax(0,1fr);gap:24px}
.tm-panels.two{grid-template-columns:minmax(0,640fr) minmax(0,360fr)}
.tm-sub{font-size:var(--fs-s);font-weight:650;padding-bottom:10px}
.tm-n{font-weight:400;color:var(--text-2);font-variant-numeric:tabular-nums}
.tm-legend{display:inline-flex;align-items:center;gap:6px;font-size:var(--fs-s);color:var(--text-2)}
.tm-legend i{width:10px;height:10px;border-radius:2px;display:inline-block}
.tm-legend .lg-miss{margin-inline-start:10px}
.lg-done{background:var(--ok)}.lg-miss{background:var(--miss)}
.tm-hint{font-size:var(--fs-s);color:var(--text-3);margin-inline-start:auto}
.tm-area{position:relative;width:100%}
.tm-narrow{display:none}
.tm-tile{position:absolute;overflow:hidden;border-radius:3px;container-type:size}
.tm-band{position:absolute;inset-inline:0;background:var(--ok)}
.tm-band i{position:absolute;display:block;background:var(--miss)}
.tm-band.grid::after{content:"";position:absolute;inset:0;pointer-events:none;
  background-image:linear-gradient(to right,var(--grid) 1px,transparent 1px),linear-gradient(to bottom,var(--grid) 1px,transparent 1px);
  background-size:calc(100% / var(--c)) calc(100% / var(--r))}
.tm-tile::before{content:"";position:absolute;inset:0;z-index:2;border-radius:3px;pointer-events:none;
  box-shadow:inset 0 0 0 2px var(--text);opacity:0;transition:opacity 150ms ease}
@media (hover:hover){.tm-tile:hover::before{opacity:1}}
.tm-l{position:absolute;z-index:1;inset-block-start:3px;inset-inline-start:3px;max-width:calc(100% - 6px);padding:0 4px;
  border-radius:3px;background:var(--surface);font-size:var(--fs-xs);font-weight:550;line-height:16px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;pointer-events:none}
@container (width < 40px) or (height < 22px){.tm-l{display:none}}
.tm-tip{position:fixed;z-index:30;max-width:320px;padding:10px 12px;border-radius:10px;background:var(--text);color:var(--bg);
  font-size:var(--fs-xs);line-height:1.45;pointer-events:none;box-shadow:0 8px 24px oklch(0 0 0 / 0.18)}
.tm-tip b{display:block;font-size:var(--fs-s);font-weight:650}
.tm-tip .tt-n{opacity:0.75;padding-bottom:4px}
.tm-tip .tt-m{font-family:var(--mono);overflow-wrap:anywhere}
#coverage details.rows:first-of-type{margin-top:16px}
table.asked{width:100%;max-width:960px;margin:4px 0 20px;border-collapse:collapse;font-size:var(--fs-s)}
.asked th{text-align:start;font-size:var(--fs-xs);font-weight:550;color:var(--text-3);padding:8px 16px 8px 0;border-bottom:1px solid var(--line)}
.asked td{padding:8px 16px 8px 0;border-bottom:1px solid var(--line);vertical-align:top;overflow-wrap:anywhere}
.asked td a+a{margin-inline-start:6px}
.libs{list-style:none;margin:4px 0 20px;padding:0;display:grid;gap:14px}
.libs li{display:grid;grid-template-columns:minmax(8em,14em) 5em minmax(0,1fr);gap:4px 16px;font-size:var(--fs-s)}
.libs .lib{font-weight:550}
.libs .fns{font-family:var(--mono);font-size:var(--fs-xs);color:var(--text-2);overflow-wrap:anywhere}
.cv-lines{list-style:none;margin:24px 0 0;padding:0;display:grid;gap:14px}
.cv-lines li{display:grid;grid-template-columns:minmax(10em,16em) 200px minmax(0,1fr);gap:8px 24px;align-items:center;font-size:var(--fs-s)}
.cv-name{font-weight:550}
.cv-bar{display:flex;height:8px;border-radius:2px;background:var(--track);overflow:hidden}
.cv-bar i{display:block;height:100%;background:var(--ok)}
.cv-bar i.part{background:var(--ok-part)}

/* data */
.files{margin:0;display:grid;gap:0;border-top:1px solid var(--line)}
.file{display:grid;grid-template-columns:minmax(9em,14em) 6em minmax(0,1fr);gap:4px 24px;padding:14px 0;border-bottom:1px solid var(--line)}
.file dt,.file dd{margin:0}
.gaps{margin:4px 0 20px;padding-inline-start:20px;display:grid;gap:6px;color:var(--text-2);font-size:var(--fs-s);max-width:62em}
#data details.rows{margin-top:16px}
.fine{padding:40px 0 64px;font-size:var(--fs-s);color:var(--text-3);max-width:72ch;text-wrap:pretty}

@media (min-width:1100px){
  .split{grid-template-columns:var(--cols);align-items:start;gap:var(--col-gap)}
  .js .blocker .body{display:none}
  .js .blocker .chev{transform:none}
}
@media (max-width:1180px){
  .ladder{grid-template-columns:repeat(4,minmax(0,1fr));row-gap:24px}
}
@media (max-width:860px){
  .bar-in{gap:16px}
  .snap{display:none}
  .gh{padding:0 10px}
  .gh-t{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}
  table.games,.games tbody,.games tr,.games td{display:block;width:auto}
  .games thead{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}
  .games tr{padding:14px 0;border-bottom:1px solid var(--line)}
  .games td{display:grid;grid-template-columns:5.5em minmax(0,1fr);gap:12px;padding:4px 0;border:0}
  .games td::before{content:attr(data-label);font-size:var(--fs-xs);color:var(--text-3);padding-top:2px}
  .games td>*{grid-column:2}
  .games td:first-child{display:block;padding-bottom:8px}
  .games td:first-child::before{content:none}
  .tm-wide{display:none}.tm-narrow{display:block}
  .tm-panels.two{grid-template-columns:minmax(0,1fr)}
  .tm-hint{margin-inline-start:0}
  .cv-lines li,.libs li,.file{grid-template-columns:minmax(0,1fr) auto}
  .cv-lines li>span:last-child,.libs .fns,.file dd:last-child{grid-column:1/-1}
  .cv-bar{width:120px}
}
@media (max-width:640px){
  :root{--bar-h:104px}
  .bar{height:auto}
  .bar-in{flex-wrap:wrap;row-gap:0;padding-block:10px 0}
  .nav{order:3;flex-basis:100%;overflow-x:auto;scrollbar-width:none;margin-inline:-12px;padding-bottom:6px}
  .nav a[aria-current]::after{bottom:-1px}
  .ladder{grid-template-columns:repeat(2,minmax(0,1fr))}
  .blocker summary{grid-template-columns:2em minmax(0,1fr) 16px;gap:4px 12px}
  details.rows>summary{grid-template-columns:2em minmax(0,1fr) 16px;gap:4px 12px}
  .blocker summary .impact{grid-column:2;grid-row:3;display:flex;align-items:center;gap:8px;justify-items:start}
  .blocker summary .chev{grid-column:3;grid-row:1}
  .body{padding-inline-start:0}
  .body dl{grid-template-columns:minmax(0,1fr);gap:4px}
  .body dd{margin-bottom:12px}
}
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{transition-property:opacity,background-color,color,text-decoration-color!important}
  @starting-style{.panel-in{translate:none}}
}
@media (forced-colors:active){
  .dots i.on,.pips i.on,.s-review i,.tm-band,.cv-bar i,.lg-done{background:CanvasText}
  .tm-band i,.lg-miss{background:Canvas;border:1px solid CanvasText}
  .tm-tile{outline:1px solid CanvasText}
  .chip:has(input:checked){background:Highlight;color:HighlightText;border-color:Highlight}
  .blocker summary[aria-current]{outline:2px solid Highlight;outline-offset:-2px}
}
"""


def main(argv: list[str]) -> int:
    src = Path(argv[1]) if len(argv) > 1 else Path(__file__).with_name("site") / "roadmap.json"
    dst = Path(argv[2]) if len(argv) > 2 else src.with_name("classic.html")
    doc = json.loads(src.read_text(encoding="utf-8"))
    dst.write_text(Page(doc, dst.parent).render(), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
