#!/usr/bin/env python3
"""Render site/index.html from site/roadmap.json.

The page reads nothing but the published JSON, so every fact it shows is also in the
data that tools and agents read. Standard library only. Without JavaScript the page
still shows everything; scripts add the side panel, the game filters and the theme
switch.

    python3 render_html.py                      # site/roadmap.json -> site/index.html
    python3 render_html.py in.json out.html
"""
from __future__ import annotations

import datetime as dt
import html
import json
import math
import sys
from pathlib import Path

TOP = 10
DOTS = 10
AREAS = {"shader": "Shader recompiler", "agc": "AGC driver", "libkernel": "libkernel", "libc": "libc",
         "prx": "HLE libraries", "relinker": "Relinker"}


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


def plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n:,} {one if n == 1 else (many or one + 's')}"


def slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


def ext(url: str, text: str, cls: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    return f'<a{c} href="{esc(url)}">{text}</a>'


def source_label(url: str, repo: str) -> str:
    base = f"https://github.com/{repo}/"
    if url.startswith(base):
        kind, _, tail = url[len(base):].partition("/")
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
        return max(side * side * max(a for a, _ in row) / (area * area),
                   area * area / (side * side * min(a for a, _ in row)))

    while rest:
        side = min(w, h)
        row = [rest[0]]
        for item in rest[1:]:
            if worst(row + [item], side) > worst(row, side):
                break
            row.append(item)
        rest = rest[len(row):]
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


CHEVRON = ('<svg class="chev" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">'
           '<path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.5" '
           'stroke-linecap="round" stroke-linejoin="round"/></svg>')
SEARCH = ('<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="4.5" '
          'fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M10.5 10.5L14 14" stroke="currentColor" '
          'stroke-width="1.5" stroke-linecap="round"/></svg>')
SUN = ('<svg class="ti ti-sun" width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><circle cx="9" cy="9" '
       'r="3.25" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M9 1.75v1.5M9 14.75v1.5M1.75 9h1.5M14.75 '
       '9h1.5M3.87 3.87l1.06 1.06M13.07 13.07l1.06 1.06M3.87 14.13l1.06-1.06M13.07 4.93l1.06-1.06" stroke="currentColor" '
       'stroke-width="1.5" stroke-linecap="round"/></svg>')
MOON = ('<svg class="ti ti-moon" width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path d="M14.75 '
        '10.6A6 6 0 0 1 7.4 3.25a6 6 0 1 0 7.35 7.35z" fill="none" stroke="currentColor" stroke-width="1.5" '
        'stroke-linejoin="round"/></svg>')


class Page:
    def __init__(self, doc: dict):
        self.doc = doc
        self.repo = doc["upstream"]["repo"]
        self.blockers = {b["id"]: b for b in doc["blockers"]}
        self.titles = {t["id"]: t for t in doc["titles"]}
        self.stages = [s["name"] for s in doc["stages"]]
        ranked = [self.blockers[i] for i in doc["ranking"] if i in self.blockers]
        self.ranked = [b for b in ranked if b.get("total")]
        self.unlinked = [b for b in ranked if not b.get("total")]
        self.rank_of = {b["id"]: n for n, b in enumerate(self.ranked, 1)}
        self.listed = [t for t in doc["titles"]
                       if t.get("best_stage") or t.get("open_blockers") or t.get("unverified_claim")]

    # -- names ---------------------------------------------------------------

    def ref(self, b: dict) -> str:
        if b.get("issue"):
            return f"#{b['issue']}"
        if b["id"].startswith("pr-"):
            return f"PR #{b['id'][3:]}"
        return b["id"]

    def title_name(self, tid: str) -> str:
        return (self.titles.get(tid) or {}).get("name") or tid

    def games(self, ids: list[str]) -> list[tuple[str, list[str]]]:
        """Group title ids by game name; region IDs of one game count once."""
        by_name: dict[str, list[str]] = {}
        for tid in ids:
            by_name.setdefault(self.title_name(tid), []).append(tid)
        return list(by_name.items())

    def fix_status(self, b: dict) -> tuple[str, str, dict | None]:
        fixes = [p for p in b.get("prs", []) if p.get("link") == "fixes"]
        for states, kind, label in ((("open", "draft"), "review", "Fix in review"),
                                    (("merged",), "partial", "Partly fixed"),
                                    (("closed",), "closed", "Fix closed unmerged")):
            hit = [p for p in fixes if p.get("state") in states]
            if hit:
                return kind, label, hit[0]
        return "none", "No fix yet", None

    @staticmethod
    def stage_of(t: dict) -> str | None:
        return (t.get("best_stage") or {}).get("stage")

    def blocker_href(self, b: dict) -> str:
        return f"#b-{b['id']}" if b["id"] in self.rank_of or b in self.unlinked else b["url"]

    # -- top bar and hero ----------------------------------------------------

    def topbar(self) -> str:
        commit = self.doc["upstream"].get("commit") or ""
        stamp = (ext(f"https://github.com/{self.repo}/commit/{commit}", esc(commit[:7]), "mono")
                 if commit else esc(self.doc["upstream"].get("ref") or ""))
        nav = "".join(f'<a href="#{i}">{t}</a>' for i, t in
                      (("fix-next", "Fix next"), ("games", "Games"), ("coverage", "Coverage"), ("data", "Data")))
        return f"""<header class="bar">
<div class="wrap bar-in">
  <a class="brand" href="#top"><span class="brand-mark">AnyPS5</span><span class="brand-sub">Blocker map</span></a>
  <nav class="nav" aria-label="Sections">{nav}</nav>
  <div class="bar-end">
    <span class="snap">{esc(fmt_date(self.doc["generated_at"]))} ·
    {stamp}</span>
    <button class="icon-btn" id="theme" type="button" aria-label="Switch theme" hidden>{SUN}{MOON}</button>
  </div>
</div>
</header>"""

    def hero(self) -> str:
        waiting = {self.title_name(t["id"]) for t in self.doc["titles"] if t.get("open_blockers")}
        top3 = set()
        for b in self.ranked[:3]:
            top3.update(self.title_name(t) for t in b.get("frontier_titles", []))
        counts = {s: 0 for s in self.stages}
        none = 0
        for t in self.listed:
            s = self.stage_of(t)
            if s in counts:
                counts[s] += 1
            else:
                none += 1
        rows = [(s, slug(s), counts[s]) for s in reversed(self.stages)] + [("No stage yet", "none", none)]
        peak = max(n for _, _, n in rows) or 1
        bars = "".join(
            f'<li><a href="#games" data-stage-link="{k}" class="{"zero" if not n else ""}">'
            f'<span class="b-label">{esc(s)}</span>'
            f'<span class="b-track"><span class="b-fill" style="width:{max(n / peak * 100, 0.8 if n else 0):.1f}%">'
            f'</span></span><span class="b-num">{n}</span></a></li>' for s, k, n in rows)
        return f"""<section class="hero" aria-labelledby="h-hero">
  <div class="hero-copy">
    <p class="eyebrow">Community roadmap for the AnyPS5 PS5 emulator</p>
    <h1 id="h-hero">{esc(plural(len(self.ranked), "open blocker"))} stop {esc(plural(len(waiting), "PS5 game"))}.</h1>
    <p class="lead">Fixing the top three gets {len(top3)} of them past their current stop.
    Every entry links the GitHub issue or pull request it comes from.</p>
    <div class="actions">
      <a class="btn btn-primary" href="#fix-next">See what to fix</a>
      <a class="btn" href="roadmap.json">Get the data</a>
    </div>
  </div>
  <figure class="card chart" aria-labelledby="cap-stage">
    <figcaption id="cap-stage">Games by highest confirmed stage</figcaption>
    <ol class="bars">{bars}</ol>
  </figure>
</section>"""

    # -- fix next ------------------------------------------------------------

    def dots(self, b: dict) -> str:
        names = [n for n, _ in self.games(b.get("titles", []))]
        first = {n for n, _ in self.games(b.get("frontier_titles", []))}
        names.sort(key=lambda n: n not in first)
        shown = "".join(f'<i class="{"on" if n in first else ""}"></i>' for n in names[:DOTS])
        more = f'<span class="more-dots">+{len(names) - DOTS}</span>' if len(names) > DOTS else ""
        return f'<span class="dots" aria-hidden="true">{shown}{more}</span>'

    def pr_line(self, p: dict) -> str:
        note = f'<span class="pr-note">{esc(p["note"])}</span>' if p.get("note") else ""
        return (f'<li><span class="pr-top">{ext(p["url"], esc(p["ref"]), "mono")}'
                f'<span class="tag t-{esc(p.get("state"))}">{esc(p.get("state"))}</span></span>'
                f'<span class="pr-title">{esc(p.get("title") or "")}</span>{note}</li>')

    def status_html(self, b: dict) -> str:
        kind, label, pr = self.fix_status(b)
        own = pr and b["id"] == f"pr-{pr.get('ref', '').lstrip('#')}"
        ref = f' <span class="mono">{esc(pr["ref"])}</span>' if pr and not own else ""
        return f'<span class="status s-{kind}"><i aria-hidden="true"></i>{label}{ref}</span>'

    def area(self, b: dict) -> str:
        return AREAS.get(b.get("area"), b.get("area") or "Other")

    def blocker_body(self, b: dict, rank: int | None) -> str:
        rows = []
        games = self.games(b.get("titles", []))
        if games:
            links = []
            for name, ids in games:
                extra = f' <span class="muted">({len(ids)} IDs)</span>' if len(ids) > 1 else ""
                links.append(f'<a href="#g-{esc(ids[0])}">{esc(name)}</a>{extra}')
            first = len(self.games(b.get("frontier_titles", [])))
            only = len(self.games(b.get("one_fix_titles", [])))
            facts = [f"first stop for {first}"] if first else []
            if only:
                facts.append(f"the only stop left for {only}")
            fact = f'<p class="muted small">{esc(", ".join(facts).capitalize())}.</p>' if facts else ""
            rows.append(("Blocks", f'<p>{", ".join(links)}</p>{fact}'))
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
        kicker = f"No. {rank:02d} · " if rank else ""
        return f"""<div class="body">
<div class="p-head"><p class="kicker">{kicker}{esc(self.area(b))}</p><h3>{esc(b['title'])}</h3>
<p class="meta">{self.status_html(b)}</p></div>
<dl>{dl}</dl>
<p class="out">{ext(b["url"], f"Open {esc(self.ref(b))} on GitHub")}<span class="muted"> · last activity {esc(fmt_date(b.get("last_activity")))}</span></p>
</div>"""

    def blocker_item(self, b: dict, rank: int | None) -> str:
        n = len(self.games(b.get("titles", [])))
        impact = (f'<span class="impact">{self.dots(b)}<span class="count"><b>{n}</b> '
                  f'{"game" if n == 1 else "games"}</span></span>') if rank else ""
        num = f'<span class="rank">{rank:02d}</span>' if rank else ""
        return f"""<li class="blocker" id="b-{esc(b['id'])}">
<details>
<summary>{num}<span class="what"><span class="name">{esc(b['title'])}</span>
<span class="meta"><span class="mono">{esc(self.ref(b))}</span> · {esc(self.area(b))} · {self.status_html(b)}</span></span>{impact}{CHEVRON}</summary>
{self.blocker_body(b, rank)}
</details>
</li>"""

    def fix_next(self) -> str:
        head = "".join(self.blocker_item(b, n) for n, b in enumerate(self.ranked[:TOP], 1))
        rest = self.ranked[TOP:]
        tail = ""
        if rest:
            items = "".join(self.blocker_item(b, n) for n, b in enumerate(rest, TOP + 1))
            tail = (f'<details class="more"><summary>Show {len(rest)} more blockers</summary>'
                    f'<ol class="blockers" start="{TOP + 1}">{items}</ol></details>')
        unlinked = ""
        if self.unlinked:
            items = "".join(self.blocker_item(b, None) for b in self.unlinked)
            unlinked = (f'<details class="more"><summary>{esc(plural(len(self.unlinked), "open blocker"))} '
                        f'not linked to a game yet</summary><ul class="blockers plain">{items}</ul></details>')
        return f"""<section id="fix-next" class="sec" aria-labelledby="h-fix">
  <div class="sec-head">
    <h2 id="h-fix">Fix next</h2>
    <p class="intro">Ranked by how many games a fix moves. A filled dot is a game this issue stops first;
    a hollow one hits it later. Select a row for the error, the pull requests and what to do next.</p>
  </div>
  <div class="split">
    <div class="list-col">
      <ol class="blockers">{head}</ol>
      <div class="more-row">{tail}{unlinked}</div>
    </div>
    <aside class="panel card" id="panel" aria-label="Selected blocker" tabindex="-1" hidden></aside>
  </div>
</section>"""

    # -- games ---------------------------------------------------------------

    def pips(self, stage: str | None) -> str:
        n = self.stages.index(stage) + 1 if stage in self.stages else 0
        return ('<span class="pips" aria-hidden="true">'
                + "".join(f'<i class="{"on" if i < n else ""}"></i>' for i in range(len(self.stages))) + "</span>")

    def chain_cells(self, t: dict) -> tuple[str, str]:
        steps = [s for s in (t.get("open_blockers") or []) if s["id"] in self.blockers]
        if not steps:
            return '<span class="muted">None known</span>', ""
        first = self.blockers[steps[0]["id"]]
        where = (f'<span class="scope">{esc(", ".join(steps[0]["scope"]))}</span>'
                 if steps[0].get("scope") else "")
        stop = f'<a href="{esc(self.blocker_href(first))}">{esc(first["title"])}</a>{where}'
        refs = []
        for s in steps[1:]:
            b = self.blockers[s["id"]]
            refs.append(f'<a class="mono" href="{esc(self.blocker_href(b))}" title="{esc(b["title"])}">{esc(self.ref(b))}</a>')
        return stop, '<span class="arrow" aria-hidden="true">→</span>'.join(refs)

    def source_cell(self, t: dict) -> str:
        best = t.get("best_stage")
        if not best or not best.get("url"):
            return ""
        where = " · ".join(x for x in (best.get("os"), best.get("gpu")) if x)
        tail = f'<span class="muted">{esc(where)}</span>' if where else ""
        return f'{ext(best["url"], esc(source_label(best["url"], self.repo)))}{tail}'

    def game_row(self, t: dict) -> str:
        stage = self.stage_of(t)
        claim = t.get("unverified_claim")
        claim_html = ""
        if claim and claim.get("url"):
            claim_html = (f'<span class="claim">Claimed {esc(claim.get("stage", ""))}, unverified · '
                          f'{ext(claim["url"], esc(source_label(claim["url"], self.repo)))}</span>')
        stop, then = self.chain_cells(t)
        meta = [f'<span class="mono">{esc(t["id"])}</span>'] + [esc(x) for x in (t.get("engine"), t.get("kind")) if x]
        blockers = " ".join(self.blockers[s["id"]]["title"] for s in (t.get("open_blockers") or [])
                            if s["id"] in self.blockers)
        search = " ".join(x for x in (t.get("name"), t["id"], t.get("engine"), blockers) if x).lower()
        return f"""<tr class="game" id="g-{esc(t['id'])}" data-stage="{slug(stage) if stage else 'none'}" data-search="{esc(search)}">
<td data-label="Game"><span class="g-name">{esc(t.get('name') or t['id'])}</span><span class="meta">{" · ".join(meta)}</span></td>
<td data-label="Stage"><span class="stage">{self.pips(stage)}<span>{esc(stage or "No stage yet")}</span></span>{claim_html}</td>
<td data-label="Stops at">{stop}</td>
<td data-label="Then">{then or '<span class="muted">—</span>'}</td>
<td data-label="Source">{self.source_cell(t) or '<span class="muted">—</span>'}</td>
</tr>"""

    def games_section(self) -> str:
        rank = {s: i for i, s in enumerate(self.stages)}
        ordered = sorted(self.listed, key=lambda t: (-rank.get(self.stage_of(t), -1),
                                                     (t.get("name") or t["id"]).lower()))
        counts = {}
        for t in ordered:
            k = slug(self.stage_of(t)) if self.stage_of(t) else "none"
            counts[k] = counts.get(k, 0) + 1
        chips = [("all", "All", len(ordered))] + [(slug(s), s, counts.get(slug(s), 0)) for s in reversed(self.stages)]
        chips.append(("none", "No stage yet", counts.get("none", 0)))
        chip_html = "".join(
            f'<button type="button" class="chip" data-filter="{k}" aria-pressed="{"true" if k == "all" else "false"}">'
            f'{esc(label)}<span class="chip-n">{n}</span></button>' for k, label, n in chips if n)
        defs = "".join(f"<dt>{esc(s['name'])}</dt><dd>{esc(s['meaning'])}</dd>" for s in self.doc["stages"])
        rows = "".join(self.game_row(t) for t in ordered)
        return f"""<section id="games" class="sec" aria-labelledby="h-games">
  <div class="sec-head">
    <h2 id="h-games">Games</h2>
    <p class="intro">The highest stage confirmed for each game, where it stops now and what it hits after that.</p>
  </div>
  <div class="toolbar js-only">
    <label class="search">{SEARCH}<span class="sr-only">Search games</span>
      <input id="q" type="search" placeholder="Search by game, ID, engine or issue" autocomplete="off" spellcheck="false">
      <kbd aria-hidden="true">/</kbd></label>
    <div class="chips" role="group" aria-label="Filter by stage">{chip_html}</div>
  </div>
  <p class="result js-only" id="count" role="status"></p>
  <div class="table-wrap">
  <table class="games" id="games-table">
    <thead><tr><th scope="col">Game</th><th scope="col">Stage</th><th scope="col">Stops at</th><th scope="col">Then</th><th scope="col">Source</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  </div>
  <div class="empty" id="empty" hidden>
    <p class="empty-title">No games match these filters</p>
    <p class="muted">Try a game name, a PPSA ID or an engine such as Unity.</p>
    <button type="button" class="btn" id="clear">Clear filters</button>
  </div>
  <details class="more"><summary>What the stages mean</summary><dl class="defs">{defs}</dl></details>
</section>"""

    # -- coverage ------------------------------------------------------------

    @staticmethod
    def tile(label: str, value: str, sub: str, parts: list[tuple[float, str]], extra: str = "") -> str:
        fills = "".join(f'<span class="fill {cls}" style="width:{w:.2f}%"></span>' for w, cls in parts)
        return (f'<article class="card tile"><h3>{label}</h3><p class="t-val">{value}</p>'
                f'<span class="track" aria-hidden="true">{fills}</span><p class="t-sub">{sub}</p>{extra}</article>')

    @staticmethod
    def band(top: float, height: float, first: int, count: int, cols: int, done: int, cell: float) -> str:
        """A run of full grid rows holding cells [first, first + count); cells from `done` on are missing."""
        rows = math.ceil(count / cols)
        miss = "".join(
            f'<i style="left:{100 * c / cols:.3f}%;top:{100 * r / rows:.3f}%;'
            f'width:{100 * nc / cols:.3f}%;height:{100 * nr / rows:.3f}%"></i>'
            for c, r, nc, nr in cell_runs(max(done - first, 0), count, cols))
        grid = " grid" if cell >= 3.2 else ""
        return (f'<div class="tm-band{grid}" style="top:{top:.3f}%;height:{height:.3f}%;--c:{cols};--r:{rows}">'
                f'{miss}</div>')

    def treemap(self, groups: list[dict], name_key: str, width: float, height: float, unit: str) -> str:
        """One treemap panel like upstream's progress map: a tile per group, a cell per function.

        The last row is stretched to the tile width, so every cell is a function and no slot stays empty."""
        items = sorted(((g["done"] + g["todo"], g) for g in groups if g["done"] + g["todo"]),
                       key=lambda it: -it[0])
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
            missing = [f'{m} (asked in {", ".join(f"#{i}" for i in asked[m])})' if m in asked else m
                       for m in sorted(g.get("todo_names") or [], key=lambda m: (m not in asked, m))]
            label = g.get(name_key) or g.get("label") or "?"
            tiles.append(
                f'<div class="tm-tile" style="left:calc({100 * x / width:.3f}% + 1.5px);'
                f'top:calc({100 * y / height:.3f}% + 1.5px);width:calc({100 * w / width:.3f}% - 3px);'
                f'height:calc({100 * h / height:.3f}% - 3px)" '
                f'data-name="{esc(label)}" data-done="{g["done"]}" data-total="{n}" data-unit="{unit}" '
                f'data-missing="{esc(chr(10).join(missing))}">{bands}<span class="tm-l">{esc(label)}</span></div>')
        return "".join(tiles)

    def coverage_map(self, isa: dict, hle: dict) -> str:
        libs = [g for g in hle.get("groups", []) if g["done"] + g["todo"]]
        enc = [g for g in isa.get("groups", []) if g["done"] + g["todo"]]
        all_libs = "".join(
            f'<li><span>{esc(g.get("label") or g["library"])}</span>'
            f'<span class="mono">{g["done"]}/{g["done"] + g["todo"]}</span></li>'
            for g in sorted(libs, key=lambda g: (-g["todo"], (g.get("label") or g["library"]).lower())))
        return f"""<figure class="card tm" aria-labelledby="tm-cap">
    <figcaption class="tm-head">
      <span id="tm-cap" class="tm-title">Coverage map</span>
      <span class="tm-legend" aria-hidden="true"><i class="lg-done"></i>Implemented<i class="lg-miss"></i>Missing</span>
      <span class="tm-hint muted">One cell per function or instruction. Point at a block to see what is missing.</span>
    </figcaption>
    <div class="tm-panels">
      <div class="tm-panel">
        <p class="tm-sub"><b>System libraries</b> <span class="muted">{hle["done"]:,} of {hle["total"]:,}</span></p>
        <div class="tm-area" style="aspect-ratio:640/290" role="img"
             aria-label="Treemap of {len(libs)} system libraries, {hle["done"]:,} of {hle["total"]:,} functions implemented">
          {self.treemap(libs, "label", 640, 290, "functions")}</div>
      </div>
      <div class="tm-panel">
        <p class="tm-sub"><b>GPU instructions</b> <span class="muted">{isa["done"]:,} of {isa["total"]:,}</span></p>
        <div class="tm-area" style="aspect-ratio:360/290" role="img"
             aria-label="Treemap of {len(enc)} RDNA instruction encodings, {isa["done"]:,} of {isa["total"]:,} decoded">
          {self.treemap(enc, "encoding", 360, 290, "instructions")}</div>
      </div>
    </div>
    <details class="more"><summary>All {len(libs)} libraries</summary><ul class="kv cols">{all_libs}</ul></details>
    <div class="tm-tip" id="tm-tip" aria-hidden="true" hidden></div>
  </figure>"""

    def coverage(self) -> str:
        cov = self.doc.get("coverage") or {}
        isa, hle, pm4 = cov.get("isa"), cov.get("hle"), cov.get("pm4")
        tiles = []
        if isa and isa.get("total"):
            tiles.append(self.tile("RDNA instructions decoded", f'{isa["percent"]:.0f}%',
                                   f'{isa["done"]:,} of {isa["total"]:,} opcodes',
                                   [(100 * isa["done"] / isa["total"], "")]))
        if hle and hle.get("total"):
            tiles.append(self.tile("HLE functions implemented", f'{hle["percent"]:.0f}%',
                                   f'{hle["done"]:,} of {hle["total"]:,} functions',
                                   [(100 * hle["done"] / hle["total"], "")]))
        if pm4 and pm4.get("total"):
            c, total = pm4["counts"], pm4["total"]
            rejected = [r["name"] for r in pm4.get("rows", [])
                        if r.get("status") == "rejected" and r.get("kind") == "type-3"]
            pm4_rows = "".join(f'<li class="mono">{esc(n)}</li>' for n in rejected)
            tiles.append(self.tile("PM4 packets handled", f'{100 * c.get("handled", 0) / total:.0f}%',
                                   f'{c.get("handled", 0)} of {total} handled, {c.get("conditional", 0)} in part',
                                   [(100 * c.get("handled", 0) / total, ""),
                                    (100 * c.get("conditional", 0) / total, "part")],
                                   f'<details class="more"><summary>Rejected packets</summary>'
                                   f'<ul class="tags">{pm4_rows}</ul></details>'))
        if not tiles:
            return ""
        return f"""<section id="coverage" class="sec" aria-labelledby="h-cov">
  <div class="sec-head">
    <h2 id="h-cov">Coverage</h2>
    <p class="intro">How much of the PS5's instruction set, system libraries and GPU command packets AnyPS5 handles today.
    Same data as the project's own {ext("https://boykopovar.github.io/AnyPS5/", "progress page")}.</p>
  </div>
  <div class="tiles">{"".join(tiles)}</div>
  {self.coverage_map(isa, hle) if isa and hle and isa.get("total") and hle.get("total") else ""}
</section>"""

    # -- data ----------------------------------------------------------------

    def footer(self) -> str:
        gaps = "".join(f"<li>{esc(g)}</li>" for g in self.doc.get("gaps", []))
        files = [("roadmap.json", "Everything on this page, for tools"),
                 ("llms.txt", "Entry point for language models"),
                 ("ROADMAP.md", "The same as Markdown tables"),
                 ("AGENTS.md", "How to add or correct an entry")]
        cards = "".join(f'<li><a class="card file" href="{f}"><span class="mono">{f}</span>'
                        f'<span class="muted">{d}</span></a></li>' for f, d in files)
        return f"""<footer id="data" class="sec" aria-labelledby="h-data">
  <div class="sec-head">
    <h2 id="h-data">Data</h2>
    <p class="intro">Regenerated from GitHub by roadmap.py. Corrections go into data/blockers.json, which always wins over mined text.</p>
  </div>
  <ul class="files">{cards}</ul>
  <details class="more"><summary>Known gaps in the data</summary><ul class="gaps">{gaps}</ul></details>
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
<meta name="description" content="Which open issues stop PS5 games in the AnyPS5 emulator, ranked by how many games a fix moves.">
<meta name="color-scheme" content="light dark">
<link rel="preload" href="fonts/Geist-Variable.woff2" as="font" type="font/woff2" crossorigin>
<link rel="alternate" type="application/json" href="roadmap.json">
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

/* theme */
var tb=$("#theme"),dark=matchMedia("(prefers-color-scheme: dark)");
function eff(){return root.dataset.theme||(dark.matches?"dark":"light")}
function syncTheme(){tb.dataset.mode=eff();tb.setAttribute("aria-label",eff()==="dark"?"Switch to light theme":"Switch to dark theme")}
tb.hidden=false;syncTheme();dark.addEventListener("change",syncTheme);
tb.addEventListener("click",function(){var s=d.createElement("style");
  s.textContent="*:not(.ti),*::before,*::after{transition:none!important}";d.head.appendChild(s);
  root.dataset.theme=eff()==="dark"?"light":"dark";try{localStorage.setItem("theme",root.dataset.theme)}catch(e){}
  getComputedStyle(root).color;requestAnimationFrame(function(){requestAnimationFrame(function(){s.remove()})});syncTheme()});

/* blocker list with a side panel on wide screens */
var wide=matchMedia("(min-width: 1100px)"),panel=$("#panel"),rows=$$(".blocker"),cur=null;
function select(li,write){if(!li)return;cur=li;
  rows.forEach(function(r){var s=r.querySelector("summary");if(r===li)s.setAttribute("aria-current","true");else s.removeAttribute("aria-current")});
  var c=d.createElement("div");c.className="panel-in";c.innerHTML=li.querySelector(".body").innerHTML;panel.replaceChildren(c);panel.scrollTop=0;
  if(write)history.replaceState(null,"","#"+li.id)}
rows.forEach(function(r){var s=r.querySelector("summary");
  s.addEventListener("click",function(e){if(!wide.matches)return;e.preventDefault();select(r,true)});
  s.addEventListener("keydown",function(e){if(!wide.matches||(e.key!=="ArrowDown"&&e.key!=="ArrowUp"))return;
    var vis=rows.filter(function(x){return x.offsetParent!==null}),n=vis[vis.indexOf(r)+(e.key==="ArrowDown"?1:-1)];
    if(n){e.preventDefault();n.querySelector("summary").focus();select(n,true)}})});
function layout(){panel.hidden=!wide.matches;if(wide.matches){rows.forEach(function(r){r.querySelector("details").open=false});if(!cur)select(rows[0],false)}}
wide.addEventListener("change",layout);layout();

/* games: search and stage filter */
var q=$("#q"),games=$$("tr.game"),chips=$$("[data-filter]"),count=$("#count"),empty=$("#empty"),table=$("#games-table"),stage="all";
function apply(){var term=q.value.trim().toLowerCase(),n=0;
  games.forEach(function(g){var ok=(stage==="all"||g.dataset.stage===stage)&&(!term||g.dataset.search.indexOf(term)>=0);g.hidden=!ok;if(ok)n++});
  chips.forEach(function(c){c.setAttribute("aria-pressed",String(c.dataset.filter===stage))});
  count.textContent=n===games.length?n+" games":n+" of "+games.length+" games";empty.hidden=n>0;table.hidden=n===0}
chips.forEach(function(c){c.addEventListener("click",function(){stage=c.dataset.filter;apply()})});
q.addEventListener("input",apply);q.addEventListener("keydown",function(e){if(e.key==="Escape"&&q.value){q.value="";apply()}});
$("#clear").addEventListener("click",function(){q.value="";stage="all";apply();q.focus()});
$$("[data-stage-link]").forEach(function(a){a.addEventListener("click",function(){stage=a.dataset.stageLink;q.value="";apply()})});
addEventListener("keydown",function(e){var t=(d.activeElement||{}).tagName||"";
  if(e.key==="/"&&!e.ctrlKey&&!e.metaKey&&!e.altKey&&!/INPUT|TEXTAREA|SELECT/.test(t)){e.preventDefault();q.focus()}});
apply();

/* coverage map tooltip */
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
  if(t.classList.contains("blocker")){if(wide.matches)select(t,false);else t.querySelector("details").open=true}
  if(t.classList.contains("game")&&t.hidden){q.value="";stage="all";apply()}
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
  --bg:oklch(0.985 0.002 260);--surface:oklch(0.998 0.001 260);--hover:oklch(0.955 0.003 260);
  --line:oklch(0.915 0.004 260);--track:oklch(0.925 0.004 260);--text:oklch(0.21 0.008 260);
  --text-2:oklch(0.45 0.01 260);--text-3:oklch(0.53 0.01 260);--fill-part:oklch(0.62 0.01 260);
  --ok:oklch(0.62 0.16 149);--ok-part:oklch(0.82 0.09 149);--miss:oklch(0.86 0.005 260);--grid:oklch(0.998 0.001 260 / 0.7);
  --sans:Geist,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"Geist Mono",ui-monospace,"Cascadia Mono",Consolas,monospace;
  --pixel:"Geist Pixel","Geist Mono",ui-monospace,monospace;
  --ease:cubic-bezier(0.2,0,0,1);--ease-out:cubic-bezier(0.23,1,0.32,1);
  --bar-h:60px;--gutter:clamp(16px,3.2vw,56px);
  --cols:minmax(0,1.25fr) minmax(0,1fr);--col-gap:clamp(32px,3vw,56px);
}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
  color-scheme:dark;
  --bg:oklch(0.16 0.004 260);--surface:oklch(0.195 0.005 260);--hover:oklch(0.235 0.006 260);
  --line:oklch(0.29 0.006 260);--track:oklch(0.27 0.005 260);--text:oklch(0.95 0.004 260);
  --text-2:oklch(0.76 0.008 260);--text-3:oklch(0.67 0.008 260);--fill-part:oklch(0.55 0.008 260);
  --ok:oklch(0.63 0.16 149);--ok-part:oklch(0.45 0.09 149);--miss:oklch(0.43 0.008 260);--grid:oklch(0.195 0.005 260 / 0.75);
}}
:root[data-theme=dark]{
  color-scheme:dark;
  --bg:oklch(0.16 0.004 260);--surface:oklch(0.195 0.005 260);--hover:oklch(0.235 0.006 260);
  --line:oklch(0.29 0.006 260);--track:oklch(0.27 0.005 260);--text:oklch(0.95 0.004 260);
  --text-2:oklch(0.76 0.008 260);--text-3:oklch(0.67 0.008 260);--fill-part:oklch(0.55 0.008 260);
  --ok:oklch(0.63 0.16 149);--ok-part:oklch(0.45 0.09 149);--miss:oklch(0.43 0.008 260);--grid:oklch(0.195 0.005 260 / 0.75);
}
*,*::before,*::after{box-sizing:border-box}
[hidden]{display:none!important}
html{-webkit-text-size-adjust:100%;scroll-padding-top:calc(var(--bar-h) + 16px)}
@media (prefers-reduced-motion:no-preference){html{scroll-behavior:smooth}}
body{margin:0;background:var(--bg);color:var(--text);font:400 15px/1.55 var(--sans);
  -webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;font-optical-sizing:auto}
.wrap{width:100%;max-width:1760px;margin-inline:auto;padding-inline:var(--gutter)}
a{color:inherit;text-decoration-line:underline;text-decoration-color:color-mix(in oklab,currentColor 35%,transparent);
  text-decoration-thickness:from-font;text-underline-offset:0.2em;text-decoration-skip-ink:auto;
  transition:text-decoration-color 150ms ease}
@media (hover:hover){a:hover{text-decoration-color:currentColor}}
:focus-visible{outline:2px solid var(--text);outline-offset:2px;border-radius:6px}
p{margin:0}
h1,h2,h3{margin:0;text-wrap:balance}
button{font:inherit;color:inherit}
.mono{font-family:var(--mono);font-size:0.9em;font-variant-numeric:tabular-nums}
.muted{color:var(--text-3)}
.small{font-size:13px}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}
.js-only{display:none}
.js .js-only{display:flex}
.js p.js-only{display:block}
.skip{position:fixed;inset-inline-start:16px;top:-64px;z-index:20;padding:10px 14px;border-radius:10px;
  background:var(--text);color:var(--bg);text-decoration:none;font-weight:500}
.skip:focus{top:12px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:16px}

/* top bar */
.bar{position:sticky;top:0;z-index:10;height:var(--bar-h);border-bottom:1px solid var(--line);
  background:color-mix(in oklab,var(--bg) 82%,transparent);-webkit-backdrop-filter:blur(14px) saturate(1.4);
  backdrop-filter:blur(14px) saturate(1.4)}
.bar-in{height:100%;display:flex;align-items:center;gap:32px}
.brand{display:flex;align-items:baseline;gap:10px;text-decoration:none;white-space:nowrap}
.brand-mark{font-family:var(--pixel);font-size:19px;letter-spacing:0.01em}
.brand-sub{font-size:14px;font-weight:500;color:var(--text-2)}
.nav{display:flex;gap:4px;font-size:14px;font-weight:500}
.nav a{position:relative;padding:8px 12px;border-radius:8px;color:var(--text-2);text-decoration:none;
  transition:color 150ms ease,background-color 150ms ease}
@media (hover:hover){.nav a:hover{color:var(--text);background:var(--hover)}}
.nav a[aria-current]{color:var(--text)}
.nav a[aria-current]::after{content:"";position:absolute;inset-inline:12px;bottom:-11px;height:2px;background:var(--text);border-radius:2px}
.bar-end{margin-inline-start:auto;display:flex;align-items:center;gap:16px}
.snap{font-size:13px;color:var(--text-3);white-space:nowrap}
.icon-btn{position:relative;display:grid;place-items:center;width:40px;height:40px;border:1px solid var(--line);border-radius:10px;
  background:var(--surface);cursor:pointer;transition:background-color 150ms ease,scale 160ms var(--ease-out)}
@media (hover:hover){.icon-btn:hover{background:var(--hover)}}
.icon-btn:active{scale:0.96}
.ti{grid-area:1/1;transition:opacity 300ms var(--ease),scale 300ms var(--ease),filter 300ms var(--ease)}
.icon-btn[data-mode=dark] .ti-sun,.icon-btn[data-mode=light] .ti-moon{opacity:0;scale:0.25;filter:blur(4px)}

/* hero */
.hero{display:grid;grid-template-columns:var(--cols);gap:48px var(--col-gap);align-items:center;
  padding-block:clamp(48px,6vw,96px) 0}
.hero-copy{display:grid;gap:20px;align-content:center}
.eyebrow{font-size:14px;font-weight:500;color:var(--text-2)}
h1{font-size:clamp(38px,4.6vw,72px);line-height:1.02;letter-spacing:-0.035em;font-weight:650;max-width:14em}
.lead{font-size:clamp(17px,1.35vw,20px);line-height:1.5;color:var(--text-2);max-width:34em;text-wrap:pretty}
.actions{display:flex;flex-wrap:wrap;gap:12px;padding-top:8px}
.btn{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:0 18px;border-radius:12px;
  border:1px solid var(--line);background:var(--surface);font-size:15px;font-weight:550;text-decoration:none;cursor:pointer;
  transition:background-color 150ms ease,scale 160ms var(--ease-out)}
.btn-primary{background:var(--text);color:var(--bg);border-color:var(--text)}
@media (hover:hover){.btn:hover{background:var(--hover)}.btn-primary:hover{background:color-mix(in oklab,var(--text) 86%,var(--bg))}}
.btn:active{scale:0.96}
.chart{margin:0;padding:24px 24px 16px}
.chart figcaption{font-size:14px;font-weight:550;padding-bottom:12px}
.bars{list-style:none;margin:0;padding:0;display:grid}
.bars a{display:grid;grid-template-columns:7.5em minmax(0,1fr) 3ch;align-items:center;gap:16px;padding:7px 8px;margin-inline:-8px;
  border-radius:8px;text-decoration:none;transition:background-color 150ms ease}
@media (hover:hover){.bars a:hover{background:var(--hover)}}
.b-label{font-size:14px;color:var(--text-2)}
.b-track{height:10px;border-radius:999px;background:var(--track);overflow:hidden}
.b-fill{display:block;height:100%;border-radius:999px;background:var(--text)}
.b-num{font-family:var(--pixel);font-size:20px;line-height:1;text-align:end;font-variant-numeric:tabular-nums}
.bars .zero .b-num,.bars .zero .b-label{color:var(--text-3)}

/* sections */
.sec{padding-block:clamp(56px,6vw,104px) 0}
.sec-head{display:grid;grid-template-columns:var(--cols);gap:12px var(--col-gap);align-items:end;padding-bottom:28px;
  border-bottom:1px solid var(--line)}
h2{font-size:clamp(28px,2.4vw,36px);line-height:1.1;letter-spacing:-0.025em;font-weight:650}
.intro{color:var(--text-2);max-width:44em;text-wrap:pretty}

/* fix next */
.split{display:grid;grid-template-columns:minmax(0,1fr);gap:40px}
.blockers{list-style:none;margin:0;padding:0}
.blocker{border-bottom:1px solid var(--line)}
.blocker summary{display:grid;grid-template-columns:2.25em minmax(0,1fr) auto 16px;gap:4px 20px;align-items:start;
  padding:16px 14px;margin-inline:-14px;border-radius:12px;cursor:pointer;list-style:none;
  transition:background-color 150ms ease}
.plain .blocker summary{grid-template-columns:minmax(0,1fr) 16px}
.blocker summary::-webkit-details-marker{display:none}
@media (hover:hover){.blocker summary:hover{background:var(--hover)}}
.blocker summary[aria-current]{background:var(--hover);box-shadow:inset 3px 0 0 var(--text)}
.rank{font-family:var(--mono);font-size:13px;color:var(--text-3);padding-top:2px;font-variant-numeric:tabular-nums}
.what{display:grid;gap:4px;min-width:0}
.name{font-weight:550;line-height:1.35;text-wrap:pretty;overflow-wrap:break-word}
.meta{font-size:13px;color:var(--text-3);overflow-wrap:break-word}
.status{color:var(--text-2)}
.status i{display:inline-block;width:7px;height:7px;border-radius:50%;margin-inline-end:6px;vertical-align:1px;
  box-shadow:inset 0 0 0 1.5px currentColor}
.s-review i{background:currentColor}
.s-partial i{background:linear-gradient(90deg,currentColor 50%,transparent 50%)}
.impact{display:grid;justify-items:end;gap:6px;padding-top:3px}
.count{font-size:13px;color:var(--text-3);white-space:nowrap;font-variant-numeric:tabular-nums}
.count b{color:var(--text);font-weight:600}
.dots{display:flex;gap:3px;align-items:center}
.dots i{width:7px;height:7px;border-radius:50%;box-shadow:inset 0 0 0 1.5px var(--text-2)}
.dots i.on{background:var(--text);box-shadow:none}
.more-dots{font-size:11px;color:var(--text-3);margin-inline-start:2px}
.chev{color:var(--text-3);margin-top:3px;transition:transform 150ms var(--ease)}
details[open]>summary .chev{transform:rotate(90deg)}
.body{padding:4px 0 24px calc(2.25em + 20px);display:grid;gap:18px}
.plain .body{padding-inline-start:0}
.blocker .p-head{display:none}
.body dl,.panel dl{display:grid;grid-template-columns:7.5em minmax(0,1fr);gap:14px 20px;margin:0}
.body dt{font-size:13px;color:var(--text-3);padding-top:2px}
.body dd{margin:0;min-width:0;display:grid;gap:4px;overflow-wrap:break-word}
.sig{margin:0;padding:12px 14px;border-radius:10px;background:var(--hover);font:13px/1.55 var(--mono);
  white-space:pre-wrap;overflow-wrap:anywhere;color:var(--text-2)}
.prs{list-style:none;margin:0;padding:0;display:grid;gap:12px}
.prs li{display:grid;gap:2px;overflow-wrap:break-word}
.pr-top{display:flex;align-items:center;gap:8px}
.tag{font-size:11px;font-weight:550;letter-spacing:0.02em;padding:1px 7px;border-radius:999px;border:1px solid var(--line);color:var(--text-2)}
.t-open,.t-draft{border-color:var(--text-2)}
.t-merged{background:var(--text);border-color:var(--text);color:var(--bg)}
.pr-note{font-size:13px;color:var(--text-3)}
.out{font-size:14px}
.more-row{display:flex;flex-wrap:wrap;gap:12px;align-items:flex-start;padding-top:20px}
.more-row details[open]{flex-basis:100%}
details.more>summary{display:inline-flex;align-items:center;gap:8px;min-height:40px;padding:0 16px;
  border:1px solid var(--line);border-radius:999px;background:var(--surface);font-size:14px;font-weight:550;cursor:pointer;list-style:none;
  transition:background-color 150ms ease,scale 160ms var(--ease-out)}
details.more>summary::-webkit-details-marker{display:none}
details.more>summary::after{content:"";width:6px;height:6px;border:solid var(--text-3);border-width:0 1.5px 1.5px 0;
  transform:translateY(-2px) rotate(45deg);transition:transform 150ms var(--ease)}
details.more[open]>summary::after{transform:translateY(1px) rotate(-135deg)}
@media (hover:hover){details.more>summary:hover{background:var(--hover)}}
details.more>summary:active{scale:0.96}
details.more>ol,details.more>ul.blockers{margin-top:12px;border-top:1px solid var(--line)}

/* side panel */
.panel{position:sticky;top:calc(var(--bar-h) + 24px);max-height:calc(100dvh - var(--bar-h) - 48px);overflow:auto;
  overscroll-behavior:contain;padding:28px 28px 24px;scrollbar-width:thin}
.panel-in{display:grid;gap:20px;transition:opacity 180ms var(--ease-out),translate 180ms var(--ease-out)}
@starting-style{.panel-in{opacity:0;translate:0 6px}}
.panel .p-head{display:grid;gap:8px;padding-bottom:20px;border-bottom:1px solid var(--line)}
.kicker{font-size:13px;color:var(--text-3)}
.panel h3{font-size:22px;line-height:1.25;letter-spacing:-0.015em;font-weight:620;text-wrap:balance}
.panel .meta{font-size:14px}
.panel dl{grid-template-columns:minmax(0,1fr);gap:6px}
.panel dt{font-size:13px;color:var(--text-3);padding-top:10px}
.panel dt:first-child{padding-top:0}
.panel dd{margin:0;display:grid;gap:4px;overflow-wrap:break-word}

/* games */
.toolbar{flex-wrap:wrap;gap:12px 16px;align-items:center;padding-top:24px}
.search{position:relative;display:flex;align-items:center;flex:1 1 300px;max-width:440px;color:var(--text-3)}
.search svg{position:absolute;inset-inline-start:14px;pointer-events:none}
.search input{width:100%;min-height:44px;padding:0 40px 0 40px;border:1px solid var(--line);border-radius:12px;
  background:var(--surface);color:var(--text);font:inherit;font-size:16px;transition:border-color 150ms ease}
.search input::placeholder{color:var(--text-3)}
.search input:focus-visible{outline:2px solid var(--text);outline-offset:1px;border-radius:12px}
.search kbd{position:absolute;inset-inline-end:10px;padding:1px 7px;border:1px solid var(--line);border-radius:6px;
  font:12px/1.5 var(--mono);color:var(--text-3)}
.search input:focus~kbd,.search input:not(:placeholder-shown)~kbd{display:none}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{display:inline-flex;align-items:center;gap:8px;min-height:36px;padding:0 12px;border:1px solid var(--line);border-radius:999px;
  background:var(--surface);font-size:13px;font-weight:550;cursor:pointer;transition:background-color 150ms ease,scale 160ms var(--ease-out)}
@media (hover:hover){.chip:hover{background:var(--hover)}}
.chip:active{scale:0.96}
.chip-n{font-variant-numeric:tabular-nums;color:var(--text-3);font-weight:500}
.chip[aria-pressed=true]{background:var(--text);border-color:var(--text);color:var(--bg)}
.chip[aria-pressed=true] .chip-n{color:color-mix(in oklab,var(--bg) 70%,var(--text))}
.result{padding-top:16px;font-size:13px;color:var(--text-3)}
.table-wrap{margin-top:16px}
table.games{width:100%;border-collapse:collapse;font-size:14px}
.games thead th{position:sticky;top:var(--bar-h);z-index:1;background:var(--bg);text-align:start;font-size:12px;font-weight:550;
  color:var(--text-3);padding:10px 16px 10px 0;border-bottom:1px solid var(--line)}
.games td{padding:14px 16px 14px 0;border-bottom:1px solid var(--line);vertical-align:top;overflow-wrap:break-word}
.games th:nth-child(1){width:22%}.games th:nth-child(2){width:14%}.games th:nth-child(3){width:34%}
.games th:nth-child(4){width:14%}.games th:nth-child(5){width:16%}
@media (hover:hover){.games tbody tr{transition:background-color 150ms ease}.games tbody tr:hover{background:var(--hover)}}
.games tr:target td{background:var(--hover)}
.g-name{display:block;font-size:15px;font-weight:550}
.games .meta{display:block;margin-top:2px}
.stage{display:flex;align-items:center;gap:10px;white-space:nowrap}
.pips{display:inline-flex;gap:2px}
.pips i{width:5px;height:12px;border-radius:2px;background:var(--track)}
.pips i.on{background:var(--text)}
.claim{display:block;margin-top:6px;font-size:12px;color:var(--text-3)}
.claim a{white-space:nowrap}
.scope{display:block;margin-top:2px;font-size:12px;color:var(--text-3)}
.arrow{color:var(--text-3);padding-inline:4px}
.games td:nth-child(5) .muted{display:block;font-size:12px}
.empty{display:grid;justify-items:start;gap:8px;padding:48px 0}
.empty-title{font-size:17px;font-weight:550}
.empty .btn{margin-top:8px}
.defs{display:grid;grid-template-columns:7.5em minmax(0,1fr);gap:8px 20px;margin:16px 0 0;font-size:14px;max-width:56em}
.defs dt{font-weight:550}.defs dd{margin:0;color:var(--text-2)}
#games>details.more{margin-top:24px}

/* coverage */
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:16px;padding-top:28px}
.tile{display:grid;gap:10px;align-content:start;padding:24px}
.tile h3{font-size:14px;font-weight:550;color:var(--text-2)}
.t-val{font-family:var(--pixel);font-size:clamp(44px,4vw,60px);line-height:1;letter-spacing:-0.01em;padding-top:6px}
.track{display:flex;height:8px;margin-top:4px;border-radius:999px;background:var(--track);overflow:hidden}
.fill{display:block;height:100%;background:var(--ok)}
.fill.part{background:var(--ok-part)}
.t-sub{font-size:13px;color:var(--text-3)}
.tile details.more{margin-top:6px}
.kv{list-style:none;margin:12px 0 0;padding:0}
.kv li{display:flex;justify-content:space-between;gap:16px;padding:7px 0;border-bottom:1px solid var(--line);font-size:14px}
.kv .mono{color:var(--text-2)}
.tags{list-style:none;margin:12px 0 0;padding:0;display:flex;flex-wrap:wrap;gap:6px}
.tags li{padding:3px 9px;border:1px solid var(--line);border-radius:999px;font-size:11.5px;color:var(--text-2)}

.tm{margin:16px 0 0;padding:24px}
.tm-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 24px;padding-bottom:20px}
.tm-title{font-size:16px;font-weight:600}
.tm-legend{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--text-2)}
.tm-legend i{width:10px;height:10px;border-radius:2px;display:inline-block}
.tm-legend .lg-miss{margin-inline-start:10px}
.lg-done{background:var(--ok)}
.lg-miss{background:var(--miss)}
.tm-hint{font-size:13px;margin-inline-start:auto}
.tm-panels{display:grid;grid-template-columns:minmax(0,640fr) minmax(0,360fr);gap:24px}
.tm-sub{font-size:13px;padding-bottom:10px}
.tm-sub b{font-weight:600}
.tm-area{position:relative;width:100%}
.tm-tile{position:absolute;overflow:hidden;border-radius:3px;container-type:size}
.tm-band{position:absolute;inset-inline:0;background:var(--ok)}
.tm-band i{position:absolute;display:block;background:var(--miss)}
.tm-band.grid::after{content:"";position:absolute;inset:0;pointer-events:none;
  background-image:linear-gradient(to right,var(--grid) 1px,transparent 1px),linear-gradient(to bottom,var(--grid) 1px,transparent 1px);
  background-size:calc(100% / var(--c)) calc(100% / var(--r))}
.tm-tile::before{content:"";position:absolute;inset:0;z-index:2;border-radius:4px;pointer-events:none;
  box-shadow:inset 0 0 0 2px var(--text);opacity:0;transition:opacity 150ms ease}
@media (hover:hover){.tm-tile:hover::before{opacity:1}}
.tm-l{position:absolute;z-index:1;inset-block-start:3px;inset-inline-start:3px;max-width:calc(100% - 6px);
  padding:0 4px;border-radius:3px;background:var(--surface);font-size:11px;font-weight:550;line-height:16px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;pointer-events:none}
@container (width < 38px) or (height < 22px){.tm-l{display:none}}
.tm-tip{position:fixed;z-index:30;max-width:300px;padding:10px 12px;border-radius:10px;background:var(--text);color:var(--bg);
  font-size:12px;line-height:1.45;pointer-events:none;box-shadow:0 8px 24px oklch(0 0 0 / 0.18)}
.tm-tip b{display:block;font-size:13px;font-weight:600}
.tm-tip .tt-n{opacity:0.75;padding-bottom:4px}
.tm-tip .tt-m{font-family:var(--mono);font-size:11.5px;overflow-wrap:anywhere}
.tm details.more{margin-top:20px}
.kv.cols{columns:4 220px;column-gap:32px;max-width:none}
.kv.cols li{break-inside:avoid}

/* data */
.files{list-style:none;margin:0;padding:28px 0 0;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:16px}
.file{display:grid;gap:6px;padding:20px;text-decoration:none;transition:background-color 150ms ease}
@media (hover:hover){.file:hover{background:var(--hover)}}
.file .mono{font-size:14px;font-weight:500}
.file .muted{font-size:14px}
#data>details.more{margin-top:24px}
.gaps{margin:16px 0 0;padding-inline-start:20px;display:grid;gap:6px;color:var(--text-2);font-size:14px;max-width:56em}
.fine{padding:40px 0 64px;font-size:13px;color:var(--text-3);max-width:60em;text-wrap:pretty}

@media (min-width:1100px){
  .split{grid-template-columns:var(--cols);align-items:start;gap:var(--col-gap)}
  .js .blocker .body{display:none}
  .js .blocker .chev{transform:none}
}
@media (max-width:1099px){
  .hero{grid-template-columns:minmax(0,1fr)}
}
@media (max-width:860px){
  .tm-panels{grid-template-columns:minmax(0,1fr)}
  .tm-hint{margin-inline-start:0}
  .bar-in{gap:16px}
  .snap{display:none}
  .sec-head{grid-template-columns:minmax(0,1fr)}
  table.games,.games tbody,.games tr,.games td{display:block;width:auto}
  .games thead{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}
  .games tr{padding:14px 0;border-bottom:1px solid var(--line)}
  .games td{display:grid;grid-template-columns:5.5em minmax(0,1fr);gap:12px;padding:4px 0;border:0}
  .games td::before{content:attr(data-label);font-size:12px;color:var(--text-3);padding-top:2px}
  .games td:first-child{display:block;padding-bottom:8px}
  .games td:first-child::before{content:none}
}
@media (max-width:640px){
  :root{--bar-h:104px}
  .bar{height:auto}
  .bar-in{flex-wrap:wrap;row-gap:0;padding-block:10px 0}
  .nav{order:3;flex-basis:100%;overflow-x:auto;scrollbar-width:none;margin-inline:-12px;padding-bottom:6px}
  .nav a[aria-current]::after{bottom:-1px}
  .blocker summary{grid-template-columns:1.75em minmax(0,1fr) 16px;gap:4px 12px}
  .blocker summary .impact{grid-column:2;grid-row:2;display:flex;align-items:center;gap:8px;justify-items:start}
  .blocker summary .chev{grid-column:3;grid-row:1}
  .body{padding-inline-start:0}
  .body dl{grid-template-columns:minmax(0,1fr);gap:4px}
  .body dd{margin-bottom:12px}
  .bars a{grid-template-columns:6.5em minmax(0,1fr) 3ch;gap:12px}
  .defs{grid-template-columns:minmax(0,1fr);gap:2px}
  .defs dd{margin-bottom:10px}
}
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{transition-property:opacity,background-color,color,text-decoration-color!important}
  @starting-style{.panel-in{translate:none}}
}
@media (forced-colors:active){.dots i.on,.fill,.b-fill,.pips i.on,.s-review i,.tm-band{background:CanvasText}.tm-band i{background:Canvas}}
"""


def main(argv: list[str]) -> int:
    src = Path(argv[1]) if len(argv) > 1 else Path(__file__).with_name("site") / "roadmap.json"
    dst = Path(argv[2]) if len(argv) > 2 else src.with_name("index.html")
    doc = json.loads(src.read_text(encoding="utf-8"))
    dst.write_text(Page(doc).render(), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
