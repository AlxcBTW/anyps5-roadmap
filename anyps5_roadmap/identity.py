"""Game identity: which title IDs are one game, and what that game is called.

A game is one entity: a canonical name, the title IDs it ships under (PPSA for PS5, CUSA for PS4; the
region variants of one game share an entity) and the other names people write it as (aliases). Three
signals decide, strongest first:

1. data/games.json: a person's word. A curated game lists its title IDs, its name and aliases, and
   `distinct` keeps games apart that look alike.
2. The PlayStation title list (andshrew/PlayStation-Titles, built from the PlayStation Store): every PS5
   title ID with its store concept, official name, region and content ID. Title IDs of one concept are
   one game; the store name is the title ID's own name.
3. The name key: a name with case, symbols, punctuation, accents, a leading "The", region, platform and
   edition suffixes, roman numerals and known abbreviations normalised away ("GTA V" and "Grand Theft
   Auto V" share the key "grand theft auto 5").

Two titles merge on their name key only when both names are trusted (curated or from the store) or both
are mined. A mined name that matches a listed game, a name that is another one minus its subtitle, a
name that starts another one and a near-identical spelling go to the review list instead: they are
never merged by themselves. Every merge carries the reasons it rests on.

`resolve()` is the whole interface; `name_key()` is exported for tests and the tag matcher.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

TITLE_ID = re.compile(r"\b(?:PPSA|CUSA)\d{5}\b")
# IDs that stand for no title: the template ID of content-ID examples ("UP0000-PPSA00000_00-LABEL")
PLACEHOLDER_IDS = frozenset({"PPSA00000", "CUSA00000"})
CONCEPT_URL = "https://store.playstation.com/en-us/concept/{}"
CATALOG_SOURCE = "https://github.com/andshrew/PlayStation-Titles"
REGIONS = {"UP": "US", "EP": "EU", "JP": "JP", "HP": "Asia", "KP": "KR", "IP": "Intl"}
REGION_ORDER = ["UP", "EP", "JP", "HP", "KP", "IP"]

# Short forms people write for long names: the first word (or the first word with a number glued on,
# "GTA5", "RE4", "FFVII") is replaced by the full name. `True` marks the ambiguous ones that expand only
# before a number, so "RE4" is Resident Evil 4 while "Re:Zero" stays what it is.
ABBREVIATIONS: dict[str, tuple[str, bool]] = {
    "gta": ("Grand Theft Auto", False),
    "cod": ("Call of Duty", False),
    "tlou": ("The Last of Us", False),
    "gow": ("God of War", False),
    "mgs": ("Metal Gear Solid", False),
    "rdr": ("Red Dead Redemption", False),
    "hzd": ("Horizon Zero Dawn", False),
    "hfw": ("Horizon Forbidden West", False),
    "nfs": ("Need for Speed", False),
    "dmc": ("Devil May Cry", False),
    "dbz": ("Dragon Ball Z", False),
    "re": ("Resident Evil", True),
    "gt": ("Gran Turismo", True),
    "ff": ("Final Fantasy", True),
    "kh": ("Kingdom Hearts", True),
    "dq": ("Dragon Quest", True),
    "sf": ("Street Fighter", True),
    "mk": ("Mortal Kombat", True),
    "bg": ("Baldur's Gate", True),
    "sh": ("Silent Hill", True),
}
ROMAN = {
    "ii": "2",
    "iii": "3",
    "iv": "4",
    "vi": "6",
    "vii": "7",
    "viii": "8",
    "ix": "9",
    "xi": "11",
    "xii": "12",
    "xiii": "13",
    "xiv": "14",
    "xv": "15",
    "xvi": "16",
    "xvii": "17",
    "xviii": "18",
    "xix": "19",
    "xx": "20",
}
# single letters are numerals only at the end of a name or of its main part: "Grand Theft Auto V",
# "The Last of Us Part I", but not "Raiden III x MIKADO MANIAX"; X is left alone (Mega Man X)
ROMAN_LAST = {"i": "1", "v": "5"}
SYMBOLS = re.compile(r"[™®©℠]")
# a parenthesis or a trailing phrase that names a region, a platform or a kind of build, not the game
REGION_WORDS = (
    r"(?:eu|us|usa|na|jp|jpn|japan|asia|europe|uk|intl|international|homebrew|demo|ps5|ps4|ps4 and ps5|ps5 and ps4)"
)
PAREN_SUFFIX = re.compile(r"\(\s*" + REGION_WORDS + r"(?:\s*(?:,|/|and)\s*" + REGION_WORDS + r")*\s*\)")
PLATFORM_SUFFIX = re.compile(
    r"(?:\s+(?:for\s+)?(?:ps5|ps4|playstation\s*5|playstation\s*4)(?:\s+and\s+(?:ps5|ps4))?(?:\s+(?:edition|version))?)+$"
)
EDITION_SUFFIX = re.compile(
    r"\s+(?:(?:standard|deluxe|digital deluxe|digital|premium|gold|ultimate|complete|collectors|collector s|launch|"
    r"day one|special|game of the year|goty|cross gen|crossgen)\s+(?:edition|version|bundle)|goty|cross gen bundle)$"
)
SUBTITLE_SPLIT = re.compile(r"\s*(?::|\s[-–—]\s|\s[-–—]|[-–—]\s)\s*")


@dataclass(frozen=True)
class NameKey:
    """A name reduced to what identifies the game. `base` is the key of the part before a subtitle
    (None without one); `notes` say which spellings were normalised, for merge reasons."""

    key: str
    base: str | None
    notes: tuple[str, ...]
    abbreviated: bool

    @property
    def compact(self) -> str:
        """The key without spaces: "3D MiniGolf" and "3DMiniGolf", "Super Hot" and "SUPERHOT" are one name."""
        return self.key.replace(" ", "")


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKC", SYMBOLS.sub(" ", text))
    decomposed = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in decomposed if not unicodedata.combining(c))
    text = text.lower().replace("&", " and ").replace("+", " and ")
    return re.sub(r"['’`´]", "", text)


def _words(text: str) -> list[str]:
    return [w for w in re.split(r"[\W_]+", text) if w]


def _part_key(part: str, notes: list[str], first_part: bool) -> tuple[str, bool]:
    """The key of one part of a name (the main part or a subtitle)."""
    words = _words(part)
    abbreviated = False
    if words:
        first = words[0]
        glued = re.fullmatch(r"([a-z]+?)(\d+|[ivx]+)", first)
        head, tail = (glued.group(1), glued.group(2)) if glued and glued.group(1) in ABBREVIATIONS else (first, None)
        if head in ABBREVIATIONS:
            full, needs_number = ABBREVIATIONS[head]
            nxt = tail or (words[1] if len(words) > 1 else "")
            if not needs_number or re.fullmatch(r"\d+|[ivx]+", nxt or ""):
                notes.append(f"{head.upper()} = {full}")
                words = _words(_fold(full)) + ([tail] if tail else []) + words[1:]
                abbreviated = True
    out = []
    for i, w in enumerate(words):
        if w in ROMAN:
            notes.append(f"{w.upper()} = {ROMAN[w]}")
            w = ROMAN[w]
        elif w in ROMAN_LAST and i == len(words) - 1 and i > 0:
            notes.append(f"{w.upper()} = {ROMAN_LAST[w]}")
            w = ROMAN_LAST[w]
        out.append(w)
    if out and out[0] == "the" and len(out) > 1:
        out = out[1:]
        if first_part:
            notes.append("leading The")
    return " ".join(out), abbreviated


def name_key(name: str | None) -> NameKey | None:
    """The key two names of one game share. None for an empty name."""
    if not name or not name.strip():
        return None
    notes: list[str] = []
    text = _fold(name)
    if SYMBOLS.search(name):
        notes.append("™ ® ©")
    stripped = PAREN_SUFFIX.sub(" ", text)
    if stripped != text:
        notes.append("region or platform in parentheses")
        text = stripped
    parts = [p for p in SUBTITLE_SPLIT.split(text.strip()) if p.strip()]
    if not parts:
        return None
    keys: list[str] = []
    abbreviated = False
    for i, part in enumerate(parts):
        k, abbr = _part_key(part, notes, i == 0)
        abbreviated = abbreviated or (abbr and i == 0)
        if k:
            keys.append(k)
    key = " ".join(keys)
    for rx, note in ((PLATFORM_SUFFIX, "platform suffix"), (EDITION_SUFFIX, "edition suffix")):
        trimmed = rx.sub("", key).strip()
        if trimmed and trimmed != key:
            key = trimmed
            notes.append(note)
    if not key:
        return None
    base = keys[0] if len(keys) > 1 and keys[0] != key else None
    return NameKey(key, base, tuple(dict.fromkeys(notes)), abbreviated)


def slug(name: str | None) -> str:
    text = unicodedata.normalize("NFKD", _fold(name or ""))
    text = "".join(c for c in text if c.isascii())
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:60].strip("-")


# -- the PlayStation title list ---------------------------------------------------------------------


@dataclass(frozen=True)
class CatalogEntry:
    title_id: str
    concept: str | None
    name: str | None
    content_id: str | None
    region: str | None  # UP, EP, JP, HP, KP or IP

    @property
    def region_name(self) -> str | None:
        return REGIONS.get(self.region or "", self.region)


def parse_catalog(text: str | None) -> dict[str, CatalogEntry]:
    """PS5_Titles.tsv (or PS4_Titles.tsv) of andshrew/PlayStation-Titles: titleId, conceptId, name,
    contentId, region, publisherId. One entry per title ID; a US or EU row wins over others."""
    out: dict[str, CatalogEntry] = {}
    if not text:
        return out
    lines = text.splitlines()
    head = [h.strip() for h in lines[0].split("\t")] if lines else []
    col = {h: i for i, h in enumerate(head)}
    if not {"titleId", "conceptId", "name"} <= set(col):
        return out
    for line in lines[1:]:
        cells = line.split("\t")
        if len(cells) < len(head):
            cells += [""] * (len(head) - len(cells))
        tid = cells[col["titleId"]].strip().split("_")[0]
        if not TITLE_ID.fullmatch(tid):
            continue
        region = cells[col["region"]].strip() if "region" in col else ""
        entry = CatalogEntry(
            tid,
            cells[col["conceptId"]].strip() or None,
            cells[col["name"]].strip() or None,
            cells[col["contentId"]].strip() if "contentId" in col else None,
            region or None,
        )
        cur = out.get(tid)
        if cur is None or _region_rank(entry.region) < _region_rank(cur.region):
            out[tid] = entry
    return out


def _region_rank(region: str | None) -> int:
    return REGION_ORDER.index(region) if region in REGION_ORDER else len(REGION_ORDER)


# -- resolving --------------------------------------------------------------------------------------


@dataclass
class TitleNames:
    """What the pipeline knows about one title ID's name: a curated name and the mined ones."""

    curated: str | None = None
    mined: Counter = field(default_factory=Counter)


@dataclass
class Game:
    id: str
    name: str | None
    name_origin: str | None  # curated, store or mined
    title_ids: list[str]
    aliases: list[str]
    concepts: list[str]
    curated: dict | None  # the data/games.json entry, when there is one


@dataclass
class Identity:
    games: dict[str, Game]
    of: dict[str, str]  # title ID -> game id
    titles: dict[str, dict]  # title ID -> its own name, origin, region, concept, content ID
    merges: list[dict]
    review: list[dict]
    dropped: list[str]  # placeholder IDs that stand for no title

    def game_of(self, tid: str) -> Game | None:
        gid = self.of.get(tid)
        return self.games.get(gid) if gid else None


TRUSTED = ("curated", "store")


def display_name(name: str | None) -> str | None:
    """A store name as the page shows it: without ™, ® and © and with single spaces."""
    if not name:
        return name
    return re.sub(r"\s+", " ", SYMBOLS.sub("", name)).strip() or None


def related(a: str | None, b: str | None) -> bool:
    """Whether two names can name one game: the same key, one the other without its subtitle, one starting the
    other, or near-identical spellings. A name in another script cannot be compared and counts as related."""
    if not a or not b or not (_latin(a) and _latin(b)):
        return True
    ka, kb = name_key(a), name_key(b)
    if not ka or not kb:
        return True
    x, y = ka.key, kb.key
    short, long_ = sorted((x.split(), y.split()), key=len)
    rest = iter(long_)
    return (
        f" {x} " in f" {y} "  # "UFC 6" in "EA SPORTS UFC 6"
        or f" {y} " in f" {x} "
        # every word of one, in order, in the other: "Broken Sword Reforged"
        or (len(short) >= 2 and all(w in rest for w in short))
        or ka.base == y
        or kb.base == x
        or difflib.SequenceMatcher(None, x, y).ratio() >= 0.75
    )


# a mined name used this often that is unrelated to the store's name for the ID: a homebrew app that reuses
# a retail title ID (XashPS5 on the ID of "Mars Base"), so the store entry does not describe it
REUSED_ID_MENTIONS = 3


def _top_mined(names: TitleNames) -> tuple[str | None, int]:
    if not names.mined:
        return None, 0
    top = names.mined.most_common()
    best = max(c for _, c in top)
    return max((n for n, c in top if c == best), key=len), best


def _store_entry(
    tid: str, names: TitleNames, catalog: dict[str, CatalogEntry]
) -> tuple[CatalogEntry | None, dict | None]:
    """The PlayStation title list's entry for a title ID, unless the title is something else: a curated name,
    or a name people use often, that has nothing to do with the store's name. Returns the entry that applies
    and, when one was set aside, a review item that says so."""
    entry = catalog.get(tid)
    if not entry or not entry.name:
        return entry, None
    store = display_name(entry.name)
    if names.curated:
        if related(names.curated, store):
            return entry, None
        return None, None  # a person named it; the store entry is another product on the same ID
    mined, count = _top_mined(names)
    if mined and count >= REUSED_ID_MENTIONS and not related(mined, store):
        return None, {
            "kind": "reused-id",
            "title_ids": [tid],
            "names": [mined, store],
            "note": f"reports call {tid} “{mined}” ({count} times) but the PlayStation Store lists it as “{store}”; "
            "the store entry is set aside. Name it in data/blockers.json with a source.",
        }
    return entry, None


def _title_name(names: TitleNames, entry: CatalogEntry | None) -> tuple[str | None, str | None]:
    if names.curated:
        return names.curated, "curated"
    if entry and entry.name:
        return display_name(entry.name), "store"
    mined, _ = _top_mined(names)
    return (mined, "mined") if mined else (None, None)


class _Groups:
    """Union-find over title IDs with cannot-link pairs and the reasons each union rests on."""

    def __init__(self, ids, apart: list[set[str]]):
        self.parent = {i: i for i in ids}
        self.members = {i: {i} for i in ids}
        self.apart = [s for s in apart if len(s) > 1]
        self.reasons: dict[str, list[str]] = {i: [] for i in ids}

    def find(self, i: str) -> str:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def kept_apart(self, a: str, b: str) -> bool:
        ma, mb = self.members[self.find(a)], self.members[self.find(b)]
        return any(s & ma and s & mb for s in self.apart)

    def union(self, a: str, b: str, reason: str) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return True
        if self.kept_apart(a, b):
            return False
        if len(self.members[ra]) < len(self.members[rb]):
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.members[ra] |= self.members.pop(rb)
        self.reasons[ra] += self.reasons.pop(rb) + [reason]
        return True

    def groups(self) -> list[tuple[list[str], list[str]]]:
        return [(sorted(m), list(dict.fromkeys(self.reasons[r]))) for r, m in self.members.items()]


def _style(name: str) -> int:
    """How a name is written: shouting (all-caps words) and capitalised small words cost a point each, so
    "Astro Bot" is preferred over the store's "ASTRO BOT" and "Cult of the Lamb" over "Cult Of The Lamb"."""
    words = name.split()
    # a one-word name in capitals is a brand ("DREDGE", "DOOM"); several words in capitals are the store shouting
    shouting = sum(1 for w in words if len(w) > 3 and w.isupper() and w.lower() not in ROMAN) if len(words) > 1 else 0
    small = sum(1 for w in words[1:] if w in ("Of", "The", "And", "In", "On", "A", "An", "To", "For"))
    return -(shouting + small)


def _spelling(name: str | None) -> str:
    """A name as it reads, apart from case, symbols, apostrophes and spacing."""
    return " ".join(_words(_fold(name or "")))


def _latin(name: str) -> bool:
    letters = [c for c in name if c.isalpha()]
    return bool(letters) and sum(1 for c in letters if c.isascii()) >= len(letters) / 2


def _pick_name(cands: list[dict], curated_name: str | None) -> tuple[str | None, str | None]:
    """The canonical name among the candidates of one game: {name, origin, key, region, count}."""
    if curated_name:
        return curated_name, "curated"
    if not cands:
        return None, None
    trusted = [c for c in cands if c["origin"] in TRUSTED]
    trusted_keys = {c["key"].compact for c in trusted if c["key"]}
    pool = [
        c
        for c in cands
        if c["origin"] in TRUSTED or not trusted_keys or (c["key"] and c["key"].compact in trusted_keys)
    ]
    if trusted and not any(_latin(c["name"]) for c in trusted):
        # the store names the ID in another script (an Asian region ID): the name people write wins
        pool += [c for c in cands if c["origin"] == "mined" and c.get("top") and _latin(c["name"])]
    origin_rank = {"curated": 2, "store": 1, "mined": 0}

    # the spelling people use most of the official name (the store's own spelling counting twice), and of that
    # spelling the best-written form: "Cult of the Lamb" over the store's "Cult Of The Lamb"
    uses: Counter = Counter()
    for c in pool:
        uses[_spelling(c["name"]).replace(" ", "")] += c["count"]

    def score(c):
        k = c["key"]
        return (
            c["origin"] == "curated",
            not (k and k.abbreviated),
            _latin(c["name"]),
            uses[_spelling(c["name"]).replace(" ", "")],
            _style(c["name"]),
            c["count"],
            origin_rank[c["origin"]],
            -_region_rank(c.get("region")),
            -len(c["name"]),
            c["name"],
        )

    best = max(pool, key=score)
    return best["name"], best["origin"]


def _numbers_only(a: str, b: str) -> bool:
    """Whether two keys differ only in numbers: sequels ("hades" and "hades 2") are different games."""
    wa, wb = a.split(), b.split()
    na = [w for w in wa if not w.isdigit()]
    nb = [w for w in wb if not w.isdigit()]
    return na == nb and wa != wb


def _prefix(a: str, b: str) -> bool:
    return b.startswith(a + " ") and len(a) >= 4


def resolve(
    titles: dict[str, TitleNames],
    overrides: dict | None = None,
    catalog: dict[str, CatalogEntry] | None = None,
) -> Identity:
    """Group title IDs into games. `titles` maps every title ID the pipeline saw to its names;
    `overrides` is data/games.json; `catalog` the parsed PlayStation title list (empty offline)."""
    overrides = overrides or {}
    catalog = catalog or {}
    curated_games = overrides.get("games", [])
    dropped = sorted(t for t in titles if t in PLACEHOLDER_IDS)
    ids = sorted(t for t in titles if t not in PLACEHOLDER_IDS)
    for cg in curated_games:
        for tid in cg.get("title_ids", []):
            if tid not in titles and tid not in PLACEHOLDER_IDS:
                ids.append(tid)  # a curated game names title IDs the snapshot has not seen yet
    ids = sorted(set(ids))
    names = {t: titles.get(t) or TitleNames() for t in ids}
    info: dict[str, dict] = {}
    review: list[dict] = []
    for tid in ids:
        entry, note = _store_entry(tid, names[tid], catalog)
        if note:
            review.append(note)
        name, origin = _title_name(names[tid], entry)
        info[tid] = {
            "name": name,
            "origin": origin,
            "key": name_key(name),
            "concept": entry.concept if entry else None,
            "region": entry.region if entry else None,
            "content_id": entry.content_id if entry else None,
            "store_name": display_name(entry.name) if entry else None,
        }

    apart = [set(d.get("title_ids", [])) for d in overrides.get("distinct", [])]
    groups = _Groups(ids, apart)

    # 1. a person's word
    for cg in curated_games:
        members = [t for t in cg.get("title_ids", []) if t in info]
        for other in members[1:]:
            groups.union(members[0], other, "listed together in data/games.json")
    # 2. one store concept
    by_concept: dict[str, list[str]] = {}
    for tid, i in info.items():
        if i["concept"]:
            by_concept.setdefault(i["concept"], []).append(tid)
    for concept, members in sorted(by_concept.items()):
        for other in members[1:]:
            groups.union(members[0], other, f"same PlayStation Store concept ({concept})")
    # 3. one name key, when both names are trusted or both are mined
    by_key: dict[str, list[str]] = {}
    for tid, i in info.items():
        if i["key"]:
            by_key.setdefault(i["key"].compact, []).append(tid)
    for _key, members in sorted(by_key.items()):
        trusted = [t for t in members if info[t]["origin"] in TRUSTED]
        mined = [t for t in members if info[t]["origin"] == "mined"]
        for side in (trusted, mined):
            for other in side[1:]:
                a, b = info[side[0]], info[other]
                groups.union(side[0], other, _key_reason(a["name"], a["key"], b["name"], b["key"]))
        if trusted and mined:
            for tid in mined:
                if groups.find(tid) != groups.find(trusted[0]) and not groups.kept_apart(tid, trusted[0]):
                    review.append(
                        {
                            "kind": "mined-name",
                            "title_ids": [tid, trusted[0]],
                            "names": [info[tid]["name"], info[trusted[0]]["name"]],
                            "note": f"{tid} is not in the PlayStation title list; its mined name matches "
                            f"{info[trusted[0]]['name']} ({trusted[0]}). Merge it in data/games.json only "
                            "with a source that ties the ID to the game.",
                        }
                    )

    # the games
    curated_by_id = {t: cg for cg in curated_games for t in cg.get("title_ids", [])}
    games: dict[str, Game] = {}
    of: dict[str, str] = {}
    merges: list[dict] = []
    for members, reasons in sorted(groups.groups()):
        cg = next((curated_by_id[t] for t in members if t in curated_by_id), None)
        cands = []
        for tid in members:
            i = info[tid]
            if i["name"]:
                cands.append(
                    {
                        "name": i["name"],
                        "origin": i["origin"],
                        "key": i["key"],
                        "region": i["region"],
                        "count": names[tid].mined.get(i["name"], 0) + (2 if i["origin"] in TRUSTED else 0),
                    }
                )
            if i["origin"] != "store" and i["store_name"]:
                cands.append(
                    {
                        "name": i["store_name"],
                        "origin": "store",
                        "key": name_key(i["store_name"]),
                        "region": i["region"],
                        "count": 2,
                    }
                )
            top, _ = _top_mined(names[tid])
            for n, c in names[tid].mined.items():
                if n != i["name"]:
                    cands.append(
                        {"name": n, "origin": "mined", "key": name_key(n), "region": None, "count": c, "top": n == top}
                    )
        name, origin = _pick_name(cands, (cg or {}).get("name"))
        game_key = name_key(name)
        keys = {info[t]["key"].compact for t in members if info[t]["origin"] in TRUSTED and info[t]["key"]}
        keys |= {game_key.compact} if game_key else set()
        # a curated alias always counts; a store or mined name only when it is a spelling of the game's name
        named = list((cg or {}).get("aliases", []))
        named += [
            c["name"]
            for c in sorted(cands, key=lambda c: (-c["count"], c["name"]))
            if c["key"] and (c["key"].compact in keys or (c.get("top") and c["name"] == name))
        ]
        aliases: list[str] = []
        spelled = {_spelling(name)}
        for alias in named:
            if _spelling(alias) not in spelled:
                spelled.add(_spelling(alias))
                aliases.append(alias)
        gid = slug(name) or members[0].lower()
        if gid in games:
            gid = f"{gid}-{members[0].lower()}"
        concepts = sorted({info[t]["concept"] for t in members if info[t]["concept"]})
        games[gid] = Game(gid, name, origin, members, aliases[:8], concepts, cg)
        for t in members:
            of[t] = gid
        if len(members) > 1:
            merges.append(
                {
                    "game": gid,
                    "name": name,
                    "title_ids": members,
                    "names": {t: info[t]["name"] for t in members},
                    "reasons": reasons,
                }
            )

    review += _review_pairs(games, info, apart)
    # one entry per pair of games (or per title, for a set-aside store entry), the strongest kind first
    seen: set[frozenset] = set()
    unique = []
    for r in review:
        pair = frozenset(of.get(t, t) for t in r["title_ids"])
        if (len(pair) < 2 and r["kind"] != "reused-id") or pair in seen:
            continue
        seen.add(pair)
        r["games"] = sorted(pair)
        unique.append(r)
    titles_out = {tid: {k: info[tid][k] for k in ("name", "origin", "concept", "region", "content_id")} for tid in ids}
    return Identity(games, of, titles_out, merges, unique, dropped)


def _key_reason(name_a: str | None, key_a: NameKey | None, name_b: str | None, key_b: NameKey | None) -> str:
    if name_a == name_b:
        return f"same name ({name_a})"
    notes = list(dict.fromkeys((key_a.notes if key_a else ()) + (key_b.notes if key_b else ())))
    how = f" after {'; '.join(notes)}" if notes else " apart from case, spacing and punctuation"
    return f"“{name_a}” and “{name_b}” agree{how}"


def _review_pairs(games: dict[str, Game], info: dict[str, dict], apart: list[set[str]]) -> list[dict]:
    """Pairs of games that may be one: a name that is another minus its subtitle, a name that starts
    another one, or a near-identical spelling. Two games with different store concepts are different games;
    two games kept apart in data/games.json are not listed."""
    out = []
    items = []
    for g in games.values():
        keys = [name_key(g.name)] + [name_key(a) for a in g.aliases]
        items.append((g, [k for k in keys if k]))
    for i, (a, ka) in enumerate(items):
        for b, kb in items[i + 1 :]:
            if a.concepts and b.concepts and set(a.concepts) != set(b.concepts):
                continue
            ids = set(a.title_ids) | set(b.title_ids)
            if any(s <= ids or (s & set(a.title_ids) and s & set(b.title_ids)) for s in apart):
                continue
            kind = None
            for x in ka[:1]:
                for y in kb[:1]:
                    if x.compact == y.compact or _numbers_only(x.key, y.key):
                        continue
                    if (x.base and x.base == y.key) or (y.base and y.base == x.key):
                        kind = "subtitle"
                    elif _prefix(x.key, y.key) or _prefix(y.key, x.key):
                        rest = (y.key[len(x.key) :] if len(y.key) > len(x.key) else x.key[len(y.key) :]).split()
                        if not all(w.isdigit() for w in rest):
                            kind = "prefix"
                    elif difflib.SequenceMatcher(None, x.key, y.key).ratio() >= 0.88:
                        kind = "similar"
            if kind:
                note = {
                    "subtitle": "one name is the other without its subtitle",
                    "prefix": "one name starts the other",
                    "similar": "the names are spelled almost the same",
                }[kind]
                out.append(
                    {
                        "kind": kind,
                        "title_ids": [a.title_ids[0], b.title_ids[0]],
                        "names": [a.name, b.name],
                        "note": f"{note}; at least one of them is not in the PlayStation title list",
                    }
                )
    return out
