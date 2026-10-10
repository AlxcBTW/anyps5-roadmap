"""Text mining: title IDs, names, engines, stages, error signatures and issue/PR references."""

from __future__ import annotations

import base64
import hashlib
import re

from .config import STAGES


TITLE_RE = re.compile(r"\bPPSA\d{5}\b")
MD_NOISE = re.compile(r"[*_`\[\]]|\]\([^)]*\)")
NAME_TOKEN = re.compile(r"[A-Z0-9À-ɏ][\w'’&.!:+\-]*")
NAME_CONNECT = {"of", "the", "and", "&", "a", "in", "for", "to", "de", "-", "–", ":", "vs.", "x"}
NAME_LABELS = {"title", "game", "titles", "another", "also", "tested", "with", "on", "in", "and", "from", "see"}
NAME_REJECT = {
    "windows",
    "linux",
    "macos",
    "nvidia",
    "amd",
    "intel",
    "ue4",
    "ue5",
    "unity",
    "rtx",
    "gtx",
    "rx",
    "main",
    "the",
    "title",
    "game",
    "id",
    "release",
    "build",
    "ps5",
    "ps4",
    "anyps5",
    "fps",
    "log",
    "logs",
    "with",
    "on",
    "and",
    "or",
    "pr",
    "issue",
    "retail",
    "homebrew",
    "app",
    "a",
    "an",
    "it",
    "this",
    "that",
    "note",
    "update",
    "result",
    "fix",
    "tested",
}
NAME_REJECT_FIRST = {
    "unblocks",
    "unblock",
    "fixes",
    "fix",
    "blocks",
    "needs",
    "needed",
    "affects",
    "stops",
    "tested",
    "with",
    "without",
    "from",
    "for",
    "after",
    "before",
    "both",
    "all",
    "same",
    "unreal",
    "unity",
    "runmultipleframes:",
}
NAME_REJECT_ANY = re.compile(
    r"\b(?:RTX|GTX|GPU|CPU|Radeon|Laptop|Engine \d|NVIDIA|AMD|Vulkan)\b|PPSA\d{5}|0x[0-9a-f]", re.I
)
ENGINE_RULES = [
    (re.compile(r"\bUE ?5\b|Unreal Engine 5"), "Unreal Engine 5"),
    (re.compile(r"\bUE ?4\b|Unreal Engine 4"), "Unreal Engine 4"),
    (re.compile(r"\bUE\b|\bUnreal\b"), "Unreal Engine"),
    (re.compile(r"\bUnity\b"), "Unity"),
    (re.compile(r"NativeAOT"), ".NET NativeAOT"),
    (re.compile(r"\bGameMaker\b"), "GameMaker"),
    (re.compile(r"\bGodot\b"), "Godot"),
    (re.compile(r"\bConstruct\b"), "Construct"),
    (re.compile(r"ps5-opengl"), "Mesa (OpenGL)"),
    (re.compile(r"\bDecima\b"), "Decima"),
]
OS_RULES = [
    (re.compile(r"\bWindows\b|MinGW|MSVC"), "Windows"),
    (re.compile(r"\bLinux\b|CachyOS|Fedora|Ubuntu|Arch Linux|bubblewrap|RADV"), "Linux"),
    (re.compile(r"\bmacOS\b|MoltenVK"), "macOS"),
]
GPU_RULES = [
    (re.compile(r"\bRTX\b|\bGTX\b|NVIDIA|GeForce"), "NVIDIA"),
    (re.compile(r"\bRX ?\d{3,4}\b|Radeon|RADV|\bAMD\b(?! RDNA)|gfx1[01]\d\d\b"), "AMD"),
    (re.compile(r"Intel Arc|\bArc\b|\bIris\b|UHD Graphics|HD Graphics|\bIntel\b"), "Intel"),
    (re.compile(r"lavapipe|llvmpipe"), "software"),
]
NEGATION = re.compile(
    r"\b(?:never|not|no|nothing|without|cannot|can't|doesn't|does not|didn't|fails? to|before|instead of|until)\b[^.;]{0,30}$",
    re.I,
)
# "loads story mode until …", "right after loading its first level": the title got to the
# loading step, not into the stage the keyword names
LOADING_CONTEXT = re.compile(r"\b(?:loads?|loading|into the|towards?)\b[^.;]{0,30}$", re.I)
# leading verbs that are not part of a title's name: "Adds LEGO Party! (PPSA29141)",
# "Seen in PPSA22520 (Animal Well)"
NAME_LEAD_VERBS = {
    "adds",
    "add",
    "lists",
    "list",
    "seen",
    "measured",
    "tested",
    "implements",
    "supports",
    "runs",
    "boots",
    "brings",
    "takes",
    "took",
    "makes",
    "lets",
    "gets",
}
STOP_WORDS = re.compile(
    r"\b(?:stops?|stopped|stuck|hangs?|halts?|freezes|crash(?:es|ed)?|aborts?|dies|faults?|segfaults?|fails?|failed|same (?:error|stop|crash|message)|refused|throws?)\b",
    re.I,
)
REPORT_FIELD = re.compile(r"\s*[-*]?\s*(?:title id|title|game|titles? tested|tested title)\s*:", re.I)
STAGE_RULES = [
    ("Playable", re.compile(r"(?<!un)(?<!not )\bplayable\b", re.I)),
    (
        "Ingame",
        re.compile(r"\bin-game\b|\bingame\b|\bgameplay\b|\b(?:first|tutorial) level\b|\bminutes of play\b", re.I),
    ),
    ("Menus", re.compile(r"\b(?:main|title|start|pause|home) (?:menu|screen)\b|\bmenus?\b", re.I)),
    (
        "Presents",
        re.compile(
            r"\bloading screen\b|\bblack (?:screen|frames?)\b|\bintro (?:video|movie)\b|\bsplash\b|\brenders?\b|\bdraws? (?:its|the) (?:full |complete )?(?:ui|screen|frame)|\b\d+ ?fps\b|\bpresents\b",
            re.I,
        ),
    ),
    ("First draw", re.compile(r"\bfirst (?:draw|frame|presentation)\b", re.I)),
    ("Starts", re.compile(r"\bboots?\b|\bstarts up\b", re.I)),
]
PATCHED_BUILD = re.compile(
    r"\bwith (?:#|PR|AlxcBTW/|the fix|this|these|both|all)|\bplus #|\+ ?#\d|\bon #\d+'s branch|\bthis branch\b|"
    r"\blocal(?:ly)?\b|\bfork\b|\bhack\b|#\d+ (?:took|takes|gets|brings)\b|\b(?:integration|test|testing|bring-up|working) (?:branch|stack)\b|\bstacked\b",
    re.I,
)

SIG_START = re.compile(
    r"FAIL: unresolved ELF import|Failed to load module:|undefined symbol:|what\(\):|presentation failed:|AGC graphics:|ShaderRecompiler::Recompile:"
)
SIG_WRAPPER = re.compile(
    r"^(?:what\(\):|presentation failed:|terminate called[^:]*:|(?:compute|pixel|vertex|geometry|hull|domain|mesh|task|export) shader 0x[0-9a-fA-F]+:|"
    r"AGC graphics:|AGC driver:|ShaderRecompiler::Recompile:|shader info collection failed:)\s*",
    re.I,
)
SIG_KEEP_PREFIX = ("AGC graphics:", "AGC driver:", "ShaderRecompiler::Recompile:")
IMPORT_RE = re.compile(
    r"FAIL: unresolved ELF import\s+`?(?P<nid>[A-Za-z0-9+\-_]{11})`?(?:\s*\(`?(?P<sym>[\w:]+)`?\))?\s+from\s+`?(?P<lib>[\w.\-]+?)(?:\.s?prx)?`?"
    r"(?=[`'\"\s)|.,;]|$)(?:[`'\"]*\s*\(`(?P<sym2>[\w:]+)`\))?"
)
MODULE_RE = re.compile(r"Failed to load module:\s*\S*?[\\/]?(?P<lib>[\w.\-]+\.s?prx)")
UNDEF_RE = re.compile(r"undefined symbol:\s*`?(?P<nid>[A-Za-z0-9+\-_]{11})")
QUOTED_RE = re.compile(r"[\"“]([^\"”]{20,160})[\"”]")
SIG_CUT = re.compile(r"`|\s\|\s|\|$|[\"”]|\s\(#\d|\s—\s|\s–\s")

ISSUE_URL_RE = re.compile(r"https://github\.com/(?P<repo>[\w.\-]+/[\w.\-]+)/(?:issues|pull)/(?P<num>\d+)(?![\w/])")
SHORT_REF_RE = re.compile(r"(?<![\w/#&])(?:(?P<repo>[\w.\-]+/[\w.\-]+))?#(?P<num>\d{1,6})\b")
CLOSING_RE = re.compile(
    r"(?i)\b(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?)\b:?\s+(?P<refs>(?:(?:[\w.\-]+/[\w.\-]+)?#\d+|https://github\.com/[\w.\-]+/[\w.\-]+/issues/\d+)(?:\s*(?:,|and|&)\s*(?:(?:[\w.\-]+/[\w.\-]+)?#\d+|https://github\.com/[\w.\-]+/[\w.\-]+/issues/\d+))*)"
)
REGISTER_RE = re.compile(r"\b(?:SPI|PA|CB|DB|VGT|SQ|GE|COMPUTE|SX|TA|IA|GRBM|RLC)_[A-Z0-9_]{3,}\b")

TRACKER_TITLES = 7  # an issue naming this many titles is treated as a tracker
LINE_TITLE_LIMIT = 2  # a stop line naming more titles than this is a table summary


def strip_md(text: str) -> str:
    text = re.sub(r"\]\([^)]*\)", "", text)
    return re.sub(r"[*_`\[\]>]", "", text)


def name_before(line: str, pos: int) -> str | None:
    tokens = strip_md(line[:pos]).replace("(", " ( ").split()
    if tokens and tokens[-1] == "(":
        tokens.pop()
    out: list[str] = []
    for tok in reversed(tokens):
        if tok == "(" or tok.endswith(",") or tok.endswith(";") or tok.endswith("."):
            break
        low = tok.lower().rstrip(":")
        if tok.endswith(":") and low in NAME_LABELS | {"title id", "id"}:
            break
        if NAME_TOKEN.fullmatch(tok) or tok.lower() in NAME_CONNECT:
            out.append(tok)
            if len(out) >= 7:
                break
        else:
            break
    # out holds the words last-to-first, so out[-1] is the first word of the name
    while out and (
        out[-1].lower() in NAME_CONNECT
        or out[-1].lower().rstrip(":") in NAME_LABELS
        or out[-1].lower() in NAME_LEAD_VERBS
    ):
        out.pop()
    while out and out[0].lower() in NAME_CONNECT:
        out.pop(0)
    return clean_name(" ".join(reversed(out)))


def name_after(line: str, end: int) -> str | None:
    rest = strip_md(line[end:])
    m = re.match(r"\s*\(([^,;)]{2,48})[,;)]", rest)
    if m:
        cand = m.group(1).strip()
        if not re.match(r"v?\d+\.\d+|0x|UE\d|\d+ ?(?:fps|s)\b", cand, re.I):
            return clean_name(cand)
        return None
    tokens = rest.split()
    out = []
    for tok in tokens:
        bare = tok.rstrip(",.;:)")
        if NAME_TOKEN.fullmatch(bare) or (out and bare.lower() in NAME_CONNECT):
            out.append(bare)
            if bare != tok or len(out) >= 6:
                break
        else:
            break
    while out and out[-1].lower() in NAME_CONNECT:
        out.pop()
    return clean_name(" ".join(out))


def clean_name(name: str | None) -> str | None:
    if not name:
        return None
    name = name.strip(" :-–—,()")
    words = name.split()
    if not words or not re.search(r"[A-Za-z]{2}", name) or len(name) < 3 or len(name) > 60:
        return None
    if all(w.lower().rstrip(":") in NAME_REJECT for w in words):
        return None
    if words[0].lower() in NAME_REJECT_FIRST or NAME_REJECT_ANY.search(name) or not re.match(r"[A-Z0-9À-ɏ]", name):
        return None
    if words[0].lower() in NAME_REJECT and len(words) == 1:
        return None
    if re.fullmatch(r"v?\d[\d.]*", words[0]) and len(words) == 1:
        return None
    return name


def title_context(line: str, pos: int, length: int) -> str:
    """The parenthesis that encloses the title ID, or the one right after it."""
    open_ = line.rfind("(", 0, pos)
    close_before = line.rfind(")", 0, pos)
    if open_ > close_before:
        end = line.find(")", pos)
        return line[open_ : end + 1 if end >= 0 else len(line)]
    m = re.match(r"\s*\*{0,2}\s*\(([^)]*)\)", line[pos + length :])
    return m.group(1) if m else ""


def classify(rules, text: str) -> str | None:
    for rx, value in rules:
        if rx.search(text):
            return value
    return None


def normalise_message(msg: str) -> str:
    msg = re.sub(r"0x[0-9a-fA-F]{4,}", "0x…", msg)
    msg = re.sub(r"(?<![\w.])\d{4,}(?![\w.])", "N", msg)
    msg = re.sub(r"\s+", " ", msg).strip()
    while msg and msg[-1] in ".,;:'\"`":
        msg = msg[:-1].rstrip()
    while msg.endswith(")") and msg.count(")") > msg.count("("):
        msg = msg[:-1].rstrip()
    if len(msg) > 150:
        msg = msg[:150].rsplit(" ", 1)[0] + " …"
    return msg


NID_SUFFIX = bytes.fromhex("518D64A635DED8C1E6B039B1C3E55230")
NID_ALPHABET = str.maketrans("/", "-")


def compute_nid(symbol: str) -> str:
    """PS4/PS5 symbol NID, as core/libs/nid/src/NidCompute.cpp computes it."""
    digest = hashlib.sha1(symbol.encode("utf-8") + NID_SUFFIX).digest()[:8][::-1]
    return base64.b64encode(digest).decode("ascii")[:11].translate(NID_ALPHABET)


def import_signature(nid: str, symbol: str | None, library: str | None) -> dict:
    """Import stops are keyed by NID, so a Linux `undefined symbol` line and a
    Windows `FAIL: unresolved ELF import` line for the same function match."""
    sig = {
        "family": "import",
        "key": f"unresolved import {nid}".lower(),
        "nid": nid,
        "symbol": symbol,
        "library": library,
    }
    return name_import(sig)


def name_import(sig: dict) -> dict:
    sym, lib = sig.get("symbol"), sig.get("library")
    sig["display"] = f"unresolved ELF import {sig['nid']}{f' ({sym})' if sym else ''}{f' from {lib}' if lib else ''}"
    return sig


def stop_title(sig: dict) -> str:
    """A short human title for a crash site known only by its signature."""
    if sig.get("family") == "import" and sig.get("nid"):
        what = f"{sig['symbol']} ({sig['nid']})" if sig.get("symbol") else f"NID {sig['nid']}"
        return f"{what} is not exported" + (f" by {sig['library']}" if sig.get("library") else "")
    if sig.get("family") == "import" and sig.get("library"):
        return f"Module {sig['library']} is missing"
    return sig["display"]


def signature_key(text: str | None) -> str | None:
    """Key for a curated signature string, written either as a log line or as plain text."""
    if not text:
        return None
    sig = signature_from(text)
    if sig:
        return sig["key"]
    rest = text
    while w := SIG_WRAPPER.match(rest):
        rest = rest[w.end() :]
    return normalise_message(rest).lower() or None


def signature_from(line: str, next_line: str = "") -> dict | None:
    m = SIG_START.search(line)
    if not m:
        return None
    rest = line[m.start() :]
    im = IMPORT_RE.match(rest)
    if im:
        sym = im.group("sym") or im.group("sym2")
        return import_signature(im.group("nid"), sym, im.group("lib"))
    mm = MODULE_RE.match(rest)
    if mm:
        lib = mm.group("lib")
        return {
            "family": "import",
            "key": f"missing module {lib}".lower(),
            "display": f"Failed to load module {lib}",
            "library": lib,
        }
    um = UNDEF_RE.match(rest)
    if um:
        return import_signature(um.group("nid"), None, None)
    families, kept = [], ""
    while True:
        w = SIG_WRAPPER.match(rest)
        if not w:
            break
        tag = w.group(0).strip()
        families.append(tag.split()[0].rstrip(":").lower())
        for keep in SIG_KEEP_PREFIX:
            if tag.startswith(keep):
                kept = keep
        rest = rest[w.end() :]
    if not rest.strip() and next_line:
        rest = next_line.strip()
    cut = SIG_CUT.search(rest)
    if cut:
        rest = rest[: cut.start()]
    core = normalise_message(rest)
    if len(core) < 12 or not re.search(r"[a-z]{3}", core):
        return None
    fam = (
        "recompile"
        if "shaderrecompiler::recompile" in families
        else "agc"
        if "agc" in families
        else "present"
        if "presentation" in families
        else "exception"
    )
    return {"family": fam, "key": core.lower(), "display": (kept + " " + core).strip()}


def signatures_in(text: str) -> list[tuple[int, dict]]:
    lines = text.splitlines()
    out = []
    for idx, line in enumerate(lines):
        if SIG_START.search(line):
            sig = signature_from(line, lines[idx + 1] if idx + 1 < len(lines) else "")
            if sig:
                out.append((idx, sig))
    return out


def sig_match(a: str, b: str) -> bool:
    if not a or not b:
        return False
    short, long_ = sorted((a, b), key=len)
    return len(short) >= 24 and long_.startswith(short)


def refs_in(text: str, default_repo: str) -> list[tuple[str, int]]:
    out = []
    for m in ISSUE_URL_RE.finditer(text):
        out.append((m.group("repo"), int(m.group("num"))))
    scrubbed = ISSUE_URL_RE.sub(" ", text)
    for m in SHORT_REF_RE.finditer(scrubbed):
        out.append((m.group("repo") or default_repo, int(m.group("num"))))
    return out


def closing_refs(text: str, default_repo: str) -> list[tuple[str, int]]:
    out = []
    for m in CLOSING_RE.finditer(text or ""):
        out += refs_in(m.group("refs"), default_repo)
    return out


def stage_in(line: str, title_pos: int) -> tuple[str, str] | None:
    """Highest stage keyword in a line that is not negated; returns (stage, phrase)."""
    best = None
    for stage, rx in STAGE_RULES:
        for m in rx.finditer(line):
            before = line[max(0, m.start() - 40) : m.start()]
            if NEGATION.search(before):
                continue
            if abs(m.start() - title_pos) > 220:
                continue
            idx = STAGES.index(stage)
            if (STOP_WORDS.search(before) or LOADING_CONTEXT.search(before)) and idx > 0:
                idx -= 1
            if best is None or idx > best[0]:
                best = (idx, m.group(0))
            break
    return (STAGES[best[0]], best[1]) if best else None


def clip(text: str, n: int) -> str:
    """Shorten at a word boundary and mark the cut with an ellipsis."""
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0].rstrip(",;:-–—(")
    return cut + "…"
