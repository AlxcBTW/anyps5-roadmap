"""feed.json: what each build changed, as a JSON Feed 1.1 (https://www.jsonfeed.org/version/1.1/).

A live build compares its roadmap.json with the one that is live before the deploy, reading the
ranking through the same comparison as the PR preview (preview.rank_moves), and lists what changed
in one item:

- blockers that are resolved now;
- blockers that enter or leave the ranking, and blockers whose own score moved them up or down with
  the old or the new place in the top 15 (one that only shifts because another one moved is not listed);
- games whose stage (never an unverified claim) or first open blocker changed;
- games that took in another title ID (a region variant, or a name written another way).

Games are compared as the new build groups them: against a roadmap.json from before games existed
(schema 1), a game's old stage is the best of its title IDs then, so the switch adds no false changes.

Items of the live feed are carried over, newest first, up to MAX_ITEMS, so a reader that polls less
often than every build still sees every change. A build that changes nothing adds no item. With
--no-network there is no feed; when the live roadmap.json cannot be read, the feed keeps its items
and gets no new one.
"""

from __future__ import annotations

import html
import json
import urllib.error
from collections.abc import Callable
from pathlib import Path

from .config import SITE_URL
from .preview import TOP, rank_moves
from .upstream import http_get

VERSION = "https://jsonfeed.org/version/1.1"
NAME = "feed.json"
MAX_ITEMS = 50
MAX_CHANGES = 50  # per item; a bigger diff (a new mining rule, say) lists these and counts the rest


def ref(b: dict) -> str:
    """A blocker as the page names it: #2548, PR #1872, or its id."""
    if b.get("issue"):
        return f"#{b['issue']}"
    return f"PR #{b['id'][3:]}" if b["id"].startswith("pr-") else b["id"]


def title_label(t: dict) -> str:
    return f"{t['name']} ({t['id']})" if t.get("name") else t["id"]


STAGE_ORDER = ["Converts", "Loads", "Starts", "First draw", "Presents", "Menus", "Ingame", "Playable"]


def _rank(stage: str | None) -> int:
    return STAGE_ORDER.index(stage) if stage in STAGE_ORDER else -1


def game_views(doc: dict, layout: dict) -> dict[str, dict]:
    """Stage and first open blocker of every game of `layout` (the new build), as `doc` saw them. A doc with
    games reads its own; an older one (titles only) the best of the game's title IDs."""
    out = {}
    own = {g["id"]: g for g in doc.get("games") or []}
    own_by_title = {tid: g for g in own.values() for tid in g.get("title_ids", [])}
    titles = {t["id"]: t for t in doc.get("titles") or []}
    for g in layout.get("games") or []:
        mine = own.get(g["id"]) or next((own_by_title[t] for t in g["title_ids"] if t in own_by_title), None)
        if doc.get("games") is not None:
            if mine is None:
                out[g["id"]] = {"stage": None, "stop": None}
                continue
            steps = mine.get("open_blockers") or []
            out[g["id"]] = {"stage": (mine.get("stage") or {}).get("stage"), "stop": steps[0]["id"] if steps else None}
            continue
        members = [titles[t] for t in g["title_ids"] if t in titles]
        best = max(members, key=lambda t: (_rank(stage_of(t)), bool(t.get("open_blockers"))), default=None)
        out[g["id"]] = {"stage": stage_of(best) if best else None, "stop": first_stop(best) if best else None}
    return out


def merged_sets(doc: dict) -> list[frozenset]:
    """The title IDs that one game holds together, as `doc` grouped them: its merges, or for an older doc the
    title IDs the page put together, those of one exact name."""
    if doc.get("identity") is not None:
        return [frozenset(m["title_ids"]) for m in doc["identity"].get("merges", [])]
    by_name: dict[str, set] = {}
    for t in doc.get("titles") or []:
        if t.get("name"):
            by_name.setdefault(t["name"], set()).add(t["id"])
    return [frozenset(ids) for ids in by_name.values() if len(ids) > 1]


def plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


class Diff:
    """What changed between two built roadmap.json documents, as records and one sentence each."""

    def __init__(self, base: dict, head: dict):
        self.base, self.head = base, head
        self.old_blockers = {b["id"]: b for b in base["blockers"]}
        self.blockers = {b["id"]: b for b in head["blockers"]}
        self.on_page = set(head["ranking"])  # open blockers; the page has an anchor for each
        self.changes: list[tuple[dict, str, str]] = []  # (record, linked subject, rest of the sentence)
        resolved = self.resolved()
        self.ranking(resolved)
        self.merges()
        self.games()

    def blocker_url(self, b: dict) -> str:
        return f"{SITE_URL}#b-{b['id']}" if b["id"] in self.on_page else b.get("url") or SITE_URL

    def add_blocker(self, kind: str, b: dict, rest: str, **facts) -> None:
        record = {"type": kind, "blocker": b["id"], **facts, "url": self.blocker_url(b)}
        self.changes.append((record, ref(b), f"“{b.get('title') or ''}” {rest}"))

    def resolved(self) -> set[str]:
        out = set()
        for b in self.head["blockers"]:
            old = self.old_blockers.get(b["id"])
            if old and old.get("status") == "open" and b.get("status") != "open":
                out.add(b["id"])
                self.add_blocker("resolved", b, "is resolved.")
        return out

    def ranking(self, resolved: set[str]) -> None:
        for m in rank_moves(self.base, self.head):
            b, n, was = self.blockers.get(m["blocker"]["id"], m["blocker"]), m["rank"], m["was"]
            if was is None:
                self.add_blocker(
                    "entered", b, f"entered the ranking at No. {n} (score {m['score']}).", rank=n, score=m["score"]
                )
            elif n is None:
                if b["id"] not in resolved:
                    self.add_blocker("left", b, f"left the ranking (was No. {was}).", was=was)
            elif n != was and m["score"] != m["was_score"] and min(n, was) <= TOP:
                way = "up" if n < was else "down"
                self.add_blocker(
                    "moved",
                    b,
                    f"moved {way} from No. {was} to No. {n} (score {m['was_score']} → {m['score']}).",
                    rank=n,
                    was=was,
                    score=m["score"],
                    was_score=m["was_score"],
                )

    def game_url(self, g: dict) -> str:
        listed = g.get("stage") or g.get("open_blockers") or g.get("unverified_claim") or g.get("stage_on_branches")
        return f"{SITE_URL}#g-{g['primary'] or g['title_ids'][0]}" if listed else SITE_URL

    def game_label(self, g: dict) -> str:
        primary = g.get("primary") or g["title_ids"][0]
        return f"{g['name']} ({primary})" if g.get("name") else primary

    def merges(self) -> None:
        before = merged_sets(self.base)
        games = {g["id"]: g for g in self.head.get("games") or []}
        for m in self.head.get("identity", {}).get("merges", []):
            ids = frozenset(m["title_ids"])
            if any(ids <= old for old in before):
                continue
            g = games.get(m["game"])
            if not g:
                continue
            why = "; ".join(m.get("reasons") or [])
            record = {"type": "merged", "game": g["id"], "title": g.get("primary"), "titles": sorted(ids)}
            record["url"] = self.game_url(g)
            listed = " and ".join(", ".join(sorted(ids)).rsplit(", ", 1))
            self.changes.append((record, self.game_label(g), f"now holds {listed} as one game ({why})."))

    def games(self) -> None:
        old, new = game_views(self.base, self.head), game_views(self.head, self.head)
        for g in sorted(self.head.get("games") or [], key=lambda g: ((g.get("name") or g["id"]).lower(), g["id"])):
            a, b = old[g["id"]], new[g["id"]]
            label, url = self.game_label(g), self.game_url(g)
            primary = g.get("primary") or g["title_ids"][0]
            stage, was = b["stage"], a["stage"]
            if stage != was:
                if stage and was:
                    rest = f"went from {was} to {stage}."
                elif stage:
                    rest = f"is at {stage} now (no stage before)."
                else:
                    rest = f"has no stage now (was {was})."
                record = {"type": "stage", "title": primary, "game": g["id"], "stage": stage, "was": was, "url": url}
                self.changes.append((record, label, rest))
            stop, was_stop = b["stop"], a["stop"]
            if stop != was_stop:
                before = f" (was {ref(self.old_blockers.get(was_stop) or {'id': was_stop})})" if was_stop else ""
                if stop:
                    blk = self.blockers.get(stop) or {"id": stop}
                    rest = f"now stops at {ref(blk)} “{blk.get('title') or ''}”{before}."
                else:
                    rest = f"has no known stop left{before}."
                record = {
                    "type": "stop",
                    "title": primary,
                    "game": g["id"],
                    "blocker": stop,
                    "was": was_stop,
                    "url": url,
                }
                self.changes.append((record, label, rest))


def stage_of(t: dict) -> str | None:
    return (t.get("best_stage") or {}).get("stage")


def first_stop(t: dict) -> str | None:
    steps = t.get("open_blockers") or []
    return steps[0]["id"] if steps else None


def item(base: dict, head: dict) -> dict | None:
    """The feed item for one build, or None when nothing on the list above changed."""
    if base.get("generated_at") == head["generated_at"]:
        return None
    changes = Diff(base, head).changes
    if not changes:
        return None
    shown, more = changes[:MAX_CHANGES], len(changes) - MAX_CHANGES
    records = [record for record, _, _ in changes]
    kinds = [r["type"] for r in records]
    resolved = kinds.count("resolved")
    ranking = sum(kinds.count(k) for k in ("entered", "left", "moved"))
    games = len({r["game"] for r in records if r["type"] in ("stage", "stop")})
    merged = kinds.count("merged")
    summary = [
        plural(resolved, "blocker resolved", "blockers resolved") if resolved else "",
        plural(ranking, "ranking change", "ranking changes") if ranking else "",
        plural(games, "game changed", "games changed") if games else "",
        plural(merged, "game merged", "games merged") if merged else "",
    ]
    text = [f"{subject} {rest}" for _, subject, rest in shown]
    lis = [
        f'<li><a href="{html.escape(r["url"])}">{html.escape(subject)}</a> {html.escape(rest)}</li>'
        for r, subject, rest in shown
    ]
    tail = f"And {plural(more, 'more change', 'more changes')}, not listed here." if more > 0 else ""
    extension = {"about": f"{SITE_URL}llms.txt", "since": base.get("generated_at"), "changes": records[:MAX_CHANGES]}
    if more > 0:
        extension["not_listed"] = more
    return {
        "id": head["generated_at"],
        "url": SITE_URL,
        "title": ", ".join(s for s in summary if s),
        "content_text": "\n".join(text + ([tail] if tail else [])),
        "content_html": f"<ul>{''.join(lis)}</ul>" + (f"<p>{html.escape(tail)}</p>" if tail else ""),
        "date_published": head["generated_at"],
        "_anyps5": extension,
    }


def build(head: dict, base: dict | None = None, previous: dict | None = None) -> dict:
    """The feed after this build: its item, if anything changed since `base`, before the items of `previous`."""
    items = [i for i in (previous or {}).get("items") or [] if isinstance(i, dict) and isinstance(i.get("id"), str)]
    new = item(base, head) if base else None
    if new:
        items = [new] + [i for i in items if i["id"] != new["id"]]
    return {
        "version": VERSION,
        "title": "AnyPS5 blocker map: changes",
        "home_page_url": SITE_URL,
        "feed_url": SITE_URL + NAME,
        "description": "What each snapshot of the AnyPS5 blocker map changed: blockers resolved, blockers entering, "
        "leaving or moving in the ranking, games whose stage or first open blocker changed, and games that took in "
        "another title ID. "
        "Generated data, community prototype, not official.",
        "language": "en",
        "items": items[:MAX_ITEMS],
    }


def fetch(url: str, get: Callable[[str], bytes], log) -> tuple[dict | None, bool]:
    """(document, reached). A 404 is reached without a document: nothing was published there yet."""
    try:
        data = json.loads(get(url))
    except urllib.error.HTTPError as e:
        e.close()
        if e.code == 404:
            return None, True
        log(f"feed.json: {url} answered HTTP {e.code}")
        return None, False
    except (OSError, ValueError) as e:  # network errors, timeouts, broken JSON
        log(f"feed.json: {url} could not be read: {e}")
        return None, False
    return (data, True) if isinstance(data, dict) else (None, False)


def publish(doc: dict, out: Path, cache_dir: Path | None, network: bool, log, get: Callable[[str], bytes] = http_get):
    """Write out/feed.json from the live roadmap.json and feed.json. A live run passes cache_dir and keeps a
    copy there, which the Roadmap workflow keeps between runs: when the live feed cannot be read, the items
    come from that copy."""
    if not network:
        log("feed.json: skipped (--no-network)")
        return None
    bust = "?build=" + "".join(c for c in doc["generated_at"] if c.isdigit())  # past the Pages CDN cache
    base, _ = fetch(SITE_URL + "roadmap.json" + bust, get, log)
    previous, reached = fetch(SITE_URL + NAME + bust, get, log)
    saved = cache_dir / NAME if cache_dir else None
    if not reached and saved and saved.exists():
        log(f"feed.json: carrying the items over from {saved}")
        previous, _ = fetch(str(saved), lambda _: saved.read_bytes(), log)
    try:
        feed = build(doc, base, previous)
    except (KeyError, TypeError, AttributeError, ValueError) as e:  # a live roadmap.json of another shape
        log(f"feed.json: the live roadmap.json could not be compared ({e!r}); no new item")
        feed = build(doc, None, previous)
    text = json.dumps(feed, indent=1, ensure_ascii=False) + "\n"
    for path in (out / NAME, saved):
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
    new = bool(feed["items"]) and feed["items"][0]["id"] == doc["generated_at"]
    log(f"feed.json: {len(feed['items'])} items, {'one new' if new else 'no new one'}")
    return out / NAME
