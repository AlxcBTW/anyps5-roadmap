"""Cover images: a picture for every game that has one on a public CDN, looked up at build time.

The first source that has one wins:

1. data/games.json: a person's choice of `image` for a game, or `"image": null` for none.
2. The PlayStation Store. The PlayStation title list gives each title ID its store concept; the concept's
   page lists the game's artwork on image.api.playstation.com: MASTER (square key art) for the rows and
   GAMEHUB_COVER_ART (16:9) for the game's panel. The CDN resizes on request (`?w=`).
3. Steam. Wikidata ties a store concept (P12332) to a Steam app (P1733); the app's library artwork is on
   Steam's CDN.

Nothing is downloaded into the repository: roadmap.json carries the URLs and the browser loads the pictures
from the CDN. Lookups are cached in data/cache/images.json, a found picture for 30 days and a miss for 7,
and one run spends at most BUDGET_S seconds on them, reading WORKERS pages at a time, so a cold cache fills
over a run or two. docs/images.md
has the sources and their terms.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .identity import CONCEPT_URL

CACHE_FILE = "images.json"
CACHE_VERSION = 1
TTL_HIT = dt.timedelta(days=30)
TTL_MISS = dt.timedelta(days=7)
BUDGET_S = 180.0
PAUSE_S = 1.0  # between two rounds of store pages
WORKERS = 3  # store pages read at once
TIMEOUT_S = 20
UA = "Mozilla/5.0 (compatible; anyps5-roadmap/2; +https://github.com/AlxcBTW/anyps5-roadmap)"
STEAM_ART = "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{}/"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
SONY_CDN = re.compile(r"^https://image\.api\.playstation\.com/")
SCRIPT_JSON = re.compile(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', re.S)
ROLES = {"square": ("MASTER",), "wide": ("GAMEHUB_COVER_ART", "BACKGROUND"), "portrait": ("PORTRAIT_BANNER",)}


def _get(url: str, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:  # noqa: S310 (fixed https hosts)
        return resp.read()


def _media_lists(node, concept: str, out: dict) -> None:
    """Every `Concept:<id>` and `Product:<id>` object in the page's embedded Apollo state."""
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, dict) and (key == f"Concept:{concept}" or key.startswith("Product:")):
                out.setdefault(key, []).append(value)
            _media_lists(value, concept, out)
    elif isinstance(node, list):
        for value in node:
            _media_lists(value, concept, out)


def concept_media(html: str, concept: str) -> dict[str, str]:
    """The artwork of one store concept, by use: square, wide and portrait. The concept's own media first,
    then that of its default product; other products on the page (editions, add-ons) are not used."""
    objects: dict[str, list[dict]] = {}
    for blob in SCRIPT_JSON.findall(html):
        try:
            _media_lists(json.loads(blob), concept, objects)
        except json.JSONDecodeError:
            continue
    concepts = objects.get(f"Concept:{concept}", [])
    media: list[dict] = []
    default = None
    for c in concepts:
        media += (c.get("personalizedMeta") or {}).get("media") or []
        media += c.get("media") or []
        default = default or ((c.get("defaultProduct") or {}).get("__ref"))
    if default:
        for p in objects.get(default, []):
            media += p.get("media") or []
    out: dict[str, str] = {}
    for use, roles in ROLES.items():
        for role in roles:
            hit = next(
                (
                    m["url"]
                    for m in media
                    if m.get("role") == role and m.get("type") == "IMAGE" and SONY_CDN.match(m.get("url") or "")
                ),
                None,
            )
            if hit:
                out[use] = hit
                break
    return out


def steam_apps(concepts: list[str], fetch: Callable[[str, dict], bytes] = _get) -> dict[str, str]:
    """Steam app IDs of store concepts, from Wikidata (P12332 concept ID, P1733 Steam app ID)."""
    if not concepts:
        return {}
    values = " ".join(json.dumps(c) for c in concepts)
    query = f"SELECT ?concept ?steam WHERE {{ VALUES ?concept {{ {values} }} ?item wdt:P12332 ?concept; wdt:P1733 ?steam. }}"
    url = WIKIDATA_SPARQL + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    data = json.loads(fetch(url, {"Accept": "application/sparql-results+json"}))
    out: dict[str, str] = {}
    for row in data.get("results", {}).get("bindings", []):
        out.setdefault(row["concept"]["value"], row["steam"]["value"])
    return out


def _fresh(entry: dict | None, now: dt.datetime) -> bool:
    if not entry or "checked" not in entry:
        return False
    try:
        checked = dt.datetime.fromisoformat(entry["checked"].replace("Z", "+00:00"))
    except ValueError:
        return False
    return now - checked < (TTL_MISS if entry.get("miss") else TTL_HIT)


def load_cache(cache_dir: Path | None) -> dict:
    path = cache_dir / CACHE_FILE if cache_dir else None
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path and path.exists() else {}
    except (OSError, json.JSONDecodeError):
        data = {}
    return data if data.get("version") == CACHE_VERSION else {"version": CACHE_VERSION, "concepts": {}}


def save_cache(cache_dir: Path | None, cache: dict) -> None:
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / CACHE_FILE).write_text(json.dumps(cache, indent=0, sort_keys=True), encoding="utf-8")


def refresh(
    concepts: list[str],
    cache: dict,
    now: dt.datetime,
    log=print,
    fetch: Callable[[str, dict], bytes] = _get,
    budget_s: float = BUDGET_S,
    pause_s: float = PAUSE_S,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Look up the concepts whose cache entry is missing or stale, within the time budget. Returns counts."""
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    store = cache.setdefault("concepts", {})
    todo = [c for c in dict.fromkeys(concepts) if not _fresh(store.get(c), now)]
    start, done, found, failed = clock(), 0, 0, 0

    def read(concept: str) -> tuple[str, dict | None, Exception | None]:
        try:
            html = fetch(CONCEPT_URL.format(concept), {}).decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            return concept, None, e
        return concept, concept_media(html, concept), None

    # a few pages at a time (they are large and slow), with a pause between rounds
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for at in range(0, len(todo), WORKERS):
            if clock() - start > budget_s:
                break
            if at:
                sleep(pause_s)
            for concept, media, error in pool.map(read, todo[at : at + WORKERS]):
                done += 1
                if error is not None:
                    failed += 1
                    log(f"  image: store concept {concept} unavailable ({error}); kept the cached entry")
                    continue
                store[concept] = (
                    {**media, "source": "playstation", "checked": stamp} if media else {"miss": True, "checked": stamp}
                )
                found += bool(media)
    # Steam for the concepts the store has no artwork for
    missing = [
        c for c in dict.fromkeys(concepts) if (store.get(c) or {}).get("miss") and not store[c].get("steam_checked")
    ]
    steam = {}
    if missing and clock() - start <= budget_s:
        try:
            steam = steam_apps(missing[:200], fetch)
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, KeyError) as e:
            log(f"  image: Wikidata unavailable ({e})")
            missing = []
        for c in missing[:200]:
            app = steam.get(c)
            if app:
                base = STEAM_ART.format(app)
                store[c] = {
                    "portrait": base + "library_600x900.jpg",
                    "wide": base + "header.jpg",
                    "source": "steam",
                    "steam_app": app,
                    "checked": stamp,
                }
            else:
                store[c]["steam_checked"] = stamp
    left = len(todo) - done
    log(
        f"  images: {done} store pages read ({found} with artwork, {failed} failed), {len(steam)} via Steam, {left} left"
    )
    return {"read": done, "found": found, "failed": failed, "steam": len(steam), "left": left}


def image_for(game_concepts: list[str], curated: dict | None, cache: dict) -> dict | None:
    """The picture a game shows: {square, wide, portrait, source, page, sizing}; None without one."""
    if curated is not None and "image" in curated:
        img = curated["image"]
        if not img:
            return None
        return {
            "square": img.get("square") or img.get("url"),
            "wide": img.get("wide"),
            "portrait": img.get("portrait"),
            "source": img.get("source") or "data/games.json",
            "page": img.get("page"),
            "sizing": "w" if SONY_CDN.match(img.get("square") or img.get("url") or "") else None,
        }
    for concept in game_concepts:
        entry = (cache.get("concepts") or {}).get(concept) or {}
        if entry.get("source") == "playstation":
            return {
                "square": entry.get("square"),
                "wide": entry.get("wide"),
                "portrait": entry.get("portrait"),
                "source": "PlayStation Store",
                "page": CONCEPT_URL.format(concept),
                "sizing": "w",
            }
        if entry.get("source") == "steam":
            return {
                "square": None,
                "wide": entry.get("wide"),
                "portrait": entry.get("portrait"),
                "source": "Steam",
                "page": f"https://store.steampowered.com/app/{entry['steam_app']}/",
                "sizing": None,
            }
    return None
