"""Text mining: title IDs, names, engines, stages, error signatures and issue/PR references."""

from __future__ import annotations

import base64
import hashlib
import re

from .config import STAGES

TITLE_RE = re.compile(r"\b(?:PPSA|CUSA)\d{5}\b")  # PS5 title IDs, and PS4 ones for the PS4 executables people try
# A PlayStation content ID names the region and the store product: "UP1004-PPSA04264_00-GTAVFULLGAMEDISC"
CONTENT_ID_RE = re.compile(
    r"\b(?P<region>[A-Z]{2})\d{4}-(?P<title>(?:PPSA|CUSA)\d{5})_00(?:-(?P<label>[A-Z0-9]{16}))?\b"
)
MD_NOISE = re.compile(r"[*_`\[\]]|\]\([^)]*\)")
NAME_TOKEN = re.compile(r"[A-Z0-9À-ɏ][\w'’&.!:+\-]*")
NAME_CONNECT = {"of", "the", "and", "&", "a", "in", "for", "to", "de", "-", "–", ":", "vs.", "x", "or"}
# A connector right before the title ID joins it to a list ("Astro Bot, Epic Mickey and PPSA15186"), so the
# words before it name other games. Punctuation connectors ("Name - PPSA…", "Name: PPSA…") do not.
NAME_JOINERS = {"of", "the", "and", "&", "a", "in", "for", "to", "de", "vs.", "x", "or"}
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
    r"\b(?:RTX|GTX|GPU|CPU|Radeon|Laptop|Engine \d|NVIDIA|AMD|Vulkan)\b|(?:PPSA|CUSA)\d{5}|0x[0-9a-f]", re.I
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
    (re.compile(r"\bRE Engine\b"), "RE Engine"),
    (re.compile(r"\bFrostbite\b"), "Frostbite"),
    (re.compile(r"\bid ?Tech(?: \d+)?\b"), "id Tech"),
    (re.compile(r"\bCryEngine\b"), "CryEngine"),
    (re.compile(r"\bCocos2[dD]\b"), "Cocos2d"),
    (re.compile(r"\bMonoGame\b"), "MonoGame"),
    (re.compile(r"\bFNA\b"), "FNA"),
    (re.compile(r"\bRen'Py\b"), "Ren'Py"),
    (re.compile(r"\bRPG ?Maker\b"), "RPG Maker"),
    (re.compile(r"\bDefold\b"), "Defold"),
    (re.compile(r"\bClickteam(?: Fusion)?\b"), "Clickteam Fusion"),
    (re.compile(r"\bSource 2\b"), "Source 2"),
]
OS_RULES = [
    (re.compile(r"\bWindows\b|MinGW|MSVC"), "Windows"),
    (
        re.compile(
            r"\bLinux\b|CachyOS|Fedora|Ubuntu|Arch Linux|bubblewrap|RADV|"
            r"SteamOS|Steam Deck|Bazzite|NixOS|Debian|openSUSE|Pop!_OS|Linux Mint|Gentoo|Manjaro"
        ),
        "Linux",
    ),
    (
        re.compile(r"\bmacOS\b|MoltenVK|Apple M[1-4]\b|MacBook|Mac mini|Sonoma|Sequoia"),
        "macOS",
    ),
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
# "they do not by themselves establish late startup or gameplay": a negated claim verb reaches further than
# the plain negation window
NEGATED_CLAIM = re.compile(
    r"\b(?:not|cannot|can't|doesn't|didn't|isn't|aren't)\b[^.;]{0,50}?"
    r"\b(?:establish(?:es)?|prove[sn]?|demonstrates?|confirms?|imply|implies|indicates?|claims?)\b[^.;]{0,50}$",
    re.I,
)
# "PS5 hardware/render equivalence and a title hitting these cases have not been measured": the keyword is
# followed by its own negation
NEGATED_AFTER = re.compile(
    r"^[^.;]{0,100}?\b(?:(?:have|has|had|is|are|was|were) not|haven't|hasn't|isn't|aren't|wasn't|weren't)"
    r"(?: yet)?(?: been)? (?:measured|tested|verified|established|confirmed|checked|shown|reached|"
    r"observed|validated|demonstrated)\b",
    re.I,
)
# a sentence about a CPU-only check or a test suite is not a title run: "CPU offsets disagree with addrlib",
# "full 870-test suite: 865 pass"
CPU_TEST = re.compile(
    r"\bCPU[- ]?(?:only|side|tests?|offsets?|reference|model|path)\b|\bunit[- ]tests?\b|\btest[- ]suite\b|"
    r"\b\d+-tests?\b|\bsynthetic (?:test|config|case)",
    re.I,
)
SENTENCE_END = re.compile(r"[.;!?](?:\s|$)")
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
# A lone capitalised word that opens a sentence right before a title ID is the sentence's first word, not a title:
# "Does PPSA01317 stop earlier?", "Not PPSA18605", "Retried PPSA20612 on another machine". Function words and
# verb forms; a real one-word title ("Returnal PPSA01285 crashes") is not matched.
SENTENCE_OPENER = re.compile(
    r"(?:Does|Do|Did|Is|Are|Was|Were|Can|Could|Will|Would|Should|Has|Have|Had|Not|No|Yes|Also|Still|Now|Then|"
    r"Same|Both|Only|Just|Maybe|Why|How|What|When|Where|Which|Who|If|So|But|And|Or|Since|See|Re)|"
    r"[A-Z][a-z]{2,}(?:ed|ing)",
)
STOP_WORDS = re.compile(
    r"\b(?:stops?|stopped|stuck|hangs?|halts?|freezes|crash(?:es|ed)?|aborts?|dies|faults?|segfaults?|fails?|failed|same (?:error|stop|crash|message)|refused|throws?)\b",
    re.I,
)
REPORT_FIELD = re.compile(r"\s*[-*]?\s*(?:title id|title|game|titles? tested|tested title)\s*:", re.I)
STAGE_RULES = [
    ("Playable", re.compile(r"(?<!un)(?<!not )\bplayable\b", re.I)),
    (
        "Ingame",
        re.compile(
            r"\bin-game\b|\bingame\b|\bgameplay\b|\b(?:first|tutorial) level\b|\bminutes of play\b|"
            r"\bhub world\b",
            re.I,
        ),
    ),
    (
        "Menus",
        re.compile(
            r"\b(?:main|title|start|pause|home) (?:menu|screen)\b|\bmenus?\b|"
            r"\bselect screens?\b|\bcharacter creat(?:or|ion)s?\b",
            re.I,
        ),
    ),
    (
        "Presents",
        re.compile(
            r"\bloading screen\b|\bblack (?:screen|frames?)\b|\bboots? to black\b|\bintro\b|\bcutscenes?\b|"
            r"\bintro (?:video|movie)\b|\bsplash\b|(?<!/)\brenders?\b(?!\s+(?:target|pass|equivalence|path|queue|thread|state|graph|backend|api|test|offset)s?\b)|\bdraws? (?:its|the) (?:full |complete )?(?:ui|screen|frame)|"
            r"\b\d+ ?fps\b|\bpresents\b",
            re.I,
        ),
    ),
    ("First draw", re.compile(r"\bfirst (?:draw|frame|presentation)\b", re.I)),
    ("Starts", re.compile(r"\bboots?\b|\bstarts up\b", re.I)),
]
PATCHED_BUILD = re.compile(
    # "with #2054", "with the fix", "with this PR", "with both patches"; not "with all 20 registries"
    r"\bwith (?:#|PR|AlxcBTW/|the fix|(?:this|these|both|all)(?:\s+(?:the|of the|two|three|\d+))?\s+"
    r"(?:fix(?:es)?|patch(?:es)?|PRs?|pull requests?|changes?|commits?|branch(?:es)?)\b)|"
    r"\bplus #|\+ ?#\d|\bon #\d+'s branch|\bthis branch\b|"
    r"\blocal(?:ly)?\b|\bfork\b|\bhack\b|#\d+ (?:took|takes|gets|brings)\b|\b(?:integration|test|testing|bring-up|working) (?:branch|stack)\b|\bstacked\b|"
    # "on oneandonlydean's astrobot branch", "on my audio branch"
    r"\b(?:my|our|their|his|her|[\w-]+'s)\s+(?:[\w-]+\s+)?branch\b|"
    # "on `main` de5e541d plus this PR", "main + the patch"
    r"(?:\bplus|\+)\s+(?:this|that|these|those|the|my|our)\s+(?:PR|PRs|pull request|change|changes|patch|patches|fix|branch)\b",
    re.I,
)
# A line that says it ran on main: "on current main", "main at 262c031", "tested on main after the merge".
MAIN_BUILD = re.compile(
    r"\b(?:on|with|current|latest|today's|plain|clean|stock|upstream)\s+`?main`?(?![\w-])|"
    r"(?<![\w-])`?main`?\s+(?:at|@)\s+`?[0-9a-f]{7,40}\b|(?<![\w-])main\s+\(`?[0-9a-f]{7,40}`?\)",
    re.I,
)
# A line that links a CI run reports a build on the runner, not a title run: "Windows was last built
# and tested on the earlier base (fork run [37987888113](…/actions/runs/37987888113): Windows 511/511)".
CI_RUN = re.compile(r"github\.com/[\w.\-]+/[\w.\-]+/actions/runs/\d+")
# "different from the description (PPSA01317 menu load, warm caches)": a parenthesis right after a
# reference to the thread's description restates that text; it is not a report of its own.
DESCRIPTION_REF = re.compile(
    r"\b(?:the|this|that|its|your|their|[\w-]+'s)\s+(?:(?:PR|pull request|issue|original)\s+)?(?:description|body)\s*$",
    re.I,
)
PAREN = re.compile(r"\([^()]*\)")

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
IMPORT_NID_RE = re.compile(r"FAIL: unresolved ELF import\s+`?[A-Za-z0-9+\-_]{11}(?![A-Za-z0-9+\-_])")
MODULE_RE = re.compile(r"Failed to load module:\s*\S*?[\\/]?(?P<lib>[\w.\-]+\.s?prx)")
UNDEF_RE = re.compile(r"undefined symbol:\s*`?(?P<nid>[A-Za-z0-9+\-_]{11})")
QUOTED_RE = re.compile(r"[\"“]([^\"”]{20,160})[\"”]")
SIG_CUT = re.compile(r"`|\s\|\s|\|$|[\"”]|\s\(#\d|\s—\s|\s–\s")

ISSUE_URL_RE = re.compile(r"https://github\.com/(?P<repo>[\w.\-]+/[\w.\-]+)/(?:issues|pull)/(?P<num>\d+)(?![\w/])")
SHORT_REF_RE = re.compile(r"(?<![\w/#&])(?:(?P<repo>[\w.\-]+/[\w.\-]+))?#(?P<num>\d{1,6})\b")
CLOSING_RE = re.compile(
    r"(?i)\b(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?)\b:?\s+(?P<refs>(?:(?:[\w.\-]+/[\w.\-]+)?#\d+|https://github\.com/[\w.\-]+/[\w.\-]+/issues/\d+)(?:\s*(?:,|and|&)\s*(?:(?:[\w.\-]+/[\w.\-]+)?#\d+|https://github\.com/[\w.\-]+/[\w.\-]+/issues/\d+))*)"
)
# The PR template's checklist line: "- [x] Unblocks: PPSA99011 #4808; PPSA99995 (same stop)". The issues on that line are
# the blockers the PR claims to fix. An unticked box ("- [ ] Unblocks: #N") is a template left as it was: no claim.
# "Depends on: #N" is a different line and never matches; a "depends on" inside the line ends the claim.
UNBLOCKS_RE = re.compile(
    r"(?im)^[ \t]*(?:[-*+][ \t]+)?(?:\[(?P<box>[ xX])\][ \t]+)?\**unblock(?:s|ed)?\**[ \t]*:\**[ \t]*(?P<rest>.*)$"
)
DEPENDS_RE = re.compile(r"(?i)\b(?:depends?\s+on|blocked\s+by)\b")
# "..., addressing #5001." names the issue the PR is for. Not "addressing review feedback from #123" (a word
# between), and a PR number in that place is no blocker anyway.
ADDRESSING_RE = re.compile(
    r"(?i)\baddress(?:es|ed|ing)\s+(?P<refs>(?:(?:[\w.\-]+/[\w.\-]+)?#\d+|https://github\.com/[\w.\-]+/[\w.\-]+/issues/\d+)(?:\s*(?:,|and|&)\s*(?:(?:[\w.\-]+/[\w.\-]+)?#\d+|https://github\.com/[\w.\-]+/[\w.\-]+/issues/\d+))*)"
)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
# A PR that stands in for an earlier one: "This is #1872 again", "Resubmission of #2174", "resubmits PR #1745",
# "Reopened as a new PR of #2106", "Replaces #2481", "Supersedes #1855". Not "superseded by" or "follow-up to".
RESUBMITS_RE = re.compile(
    r"(?i)\bis\s+(?:PR\s+)?#(\d+)\s+again\b|\bresubmi(?:ssion|ts|tted)\s+(?:of\s+)?(?:PR\s+)?#(\d+)|"
    r"\breopened as (?:a )?new PR (?:of|for)\s+#(\d+)|\b(?:replaces|supersedes)\s+(?:PR\s+)?#(\d+)"
)
# A PR that carries an earlier one, also from a fork: "Carries #2738", "Carried from #2909", "carry of #N",
# "Carries AlxcBTW/AnyPS5#26". Only these forms: "carries the fix for #2701" names what is fixed, not a PR.
CARRIES_RE = re.compile(
    r"(?i)\b(?:carries|carried\s+from|carry\s+of)\s+\[?(?:PR\s+)?(?:(?P<repo>[\w.\-]+/[\w.\-]+))?#(?P<num>\d+)\b"
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
    if out and out[0].lower() in NAME_JOINERS:
        return None
    if ":" in out[1:]:
        # a colon with spaces on both sides is a label separator ("Claude Code Report : Commandos: Origins"),
        # unlike the colon inside a title ("Commandos: Origins")
        out = out[: out.index(":", 1)]
    # nothing before the words, or a sentence end / bullet just before them
    before = tokens[: len(tokens) - len(out)]
    sentence_start = not before or before[-1][-1] in ".!?:" or before[-1] == "-"
    while out and (
        out[-1].lower() in NAME_CONNECT
        or out[-1].lower().rstrip(":") in NAME_LABELS
        or out[-1].lower() in NAME_LEAD_VERBS
    ):
        out.pop()
    while out and out[0].lower() in NAME_CONNECT:
        out.pop(0)
    if len(out) == 1 and sentence_start and SENTENCE_OPENER.fullmatch(out[0]):
        return None
    return clean_name(" ".join(reversed(out)))


def name_after(line: str, end: int) -> str | None:
    rest = strip_md(line[end:])
    m = re.match(r"\s*\(([^,;)]{2,48})[,;)]", rest)
    if m:
        cand = m.group(1).strip()
        if any(rx.fullmatch(cand) for rx, _ in ENGINE_RULES):
            return None  # "PPSA18391 (Clickteam Fusion)": the engine, not the title
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
    if re.search(r"['’]s?$", words[-1]) and not re.search(r"s['’]$", words[-1]):
        return None  # "Cyberpunk's PPSA03974 build": a possessive owns something, it is not the title
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
    if rest.startswith("FAIL: unresolved ELF import") and not IMPORT_NID_RE.match(rest):
        # the prefix quoted without its NID ("post the `FAIL: unresolved ELF import ...` line") names no stop
        return None
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


def unblocking_refs(text: str, default_repo: str) -> list[tuple[str, int]]:
    """Issues (repository, number) that a PR claims to unblock: the ticked "Unblocks:" checklist line, and
    "addressing #N". Not "Depends on: #N", not an unticked template line, not other mentions."""
    text = HTML_COMMENT_RE.sub("", text or "")
    out = []
    for m in UNBLOCKS_RE.finditer(text):
        if (m.group("box") or "x") == " ":
            continue
        rest = m.group("rest")
        cut = DEPENDS_RE.search(rest)
        out += refs_in(rest[: cut.start()] if cut else rest, default_repo)
    for m in ADDRESSING_RE.finditer(text):
        out += refs_in(m.group("refs"), default_repo)
    return out


def resubmitted_refs(text: str) -> list[int]:
    """Numbers of the PRs (same repository) that a PR's text says it resubmits or replaces."""
    return [int(next(g for g in m.groups() if g)) for m in RESUBMITS_RE.finditer(text or "")]


def carried_refs(text: str, default_repo: str) -> list[tuple[str, int]]:
    """The PRs (repository, number) that a PR's text says it carries; a fork PR keeps its repository."""
    return [(m.group("repo") or default_repo, int(m.group("num"))) for m in CARRIES_RE.finditer(text or "")]


def sentence_of(line: str, pos: int) -> str:
    """The sentence of a line that holds the offset `pos`."""
    start = 0
    for m in SENTENCE_END.finditer(line, 0, pos):
        start = m.end()
    end = SENTENCE_END.search(line, pos)
    return line[start : end.start() if end else len(line)]


def stage_in(line: str, title_pos: int) -> tuple[str, str] | None:
    """Highest stage keyword in a line that is not negated; returns (stage, phrase)."""
    best = None
    for stage, rx in STAGE_RULES:
        for m in rx.finditer(line):
            before = line[max(0, m.start() - 40) : m.start()]
            if NEGATION.search(before) or NEGATED_CLAIM.search(line[max(0, m.start() - 110) : m.start()]):
                continue
            if NEGATED_AFTER.search(line[m.end() :]):
                continue
            if CPU_TEST.search(sentence_of(line, m.start())):
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


def run_text(text: str) -> str:
    """The text without the lines that link a CI run: what the OS and GPU of its title runs are read from."""
    return "\n".join(line for line in text.splitlines() if not CI_RUN.search(line))


def restated_spans(line: str) -> list[tuple[int, int]]:
    """The parentheses in a line that restate the thread's description, as (start, end) offsets."""
    return [m.span() for m in PAREN.finditer(line) if DESCRIPTION_REF.search(strip_md(line[: m.start()]))]


def blank(line: str, spans: list[tuple[int, int]]) -> str:
    """The line with each span replaced by spaces, so the offsets of everything else stay put."""
    for a, b in spans:
        line = line[:a] + " " * (b - a) + line[b:]
    return line


# "with #3497", "plus #2054 and #2101", "main + #3497": PRs a run had on top of main
PATCH_PRS = re.compile(r"(?:\bwith|\bplus|\+|\band)\s+(?:PRs?\s+)?#(\d+)", re.I)
SELF_REF = re.compile(
    r"(?:\b(?:with|plus|on)|\+)\s+(?:this|these)\s+(?:PR|pull request|changes?|patch(?:es)?|branch|fix(?:es)?)\b"
    r"|\bthis branch\b|\b(?:my|our)\s+(?!(?:integration|test|testing|bring-up|working)\b)(?:[\w-]+\s+)?branch\b",
    re.I,
)
# "main at 262c031", "main (f4b715109)", "`main` 1be0a7ce": the commit of main a run used
MAIN_COMMIT = re.compile(r"(?<![\w-])`?main`?\s*(?:at\s+|@\s*|\(\s*)?`?([0-9a-f]{7,40})\b", re.I)


def build_of(text: str, kind: str, number: int) -> str:
    """What a report ran on, as the page labels it (see build_detail)."""
    return build_detail(text, kind, number)["build"]


def build_detail(text: str, kind: str, number: int) -> dict:
    """What a report ran on, and so whether its stage can count. `build_kind` is

    - `main`: main itself. Issue and discussion text is taken as main unless it names patches or a branch;
      PR text only when it says main and names no patches;
    - `prs`: main plus the PRs in `prs` (a PR's own branch, or "with #3497"); it counts once all are merged;
    - `patched`: local patches, a fork, a hack, a stack or someone's branch; it never counts.

    `build` is the label the page shows, `commit` the main commit the text names, if any."""
    commit = MAIN_COMMIT.search(text)
    out = {"build": "main", "build_kind": "main", "prs": [], "commit": commit.group(1) if commit else None}
    own = number if kind == "pr" else None
    named = sorted({int(n) for n in PATCH_PRS.findall(text)} - {own})
    patched = PATCHED_BUILD.search(text)
    # patched by more than PR numbers: local changes, a fork, a hack or a named branch; in PR text, "with this
    # PR" or "this branch" is the PR itself
    rest = PATCH_PRS.sub(" ", text)
    other = PATCHED_BUILD.search(SELF_REF.sub(" ", rest) if kind == "pr" else rest)
    if kind == "pr":
        if MAIN_BUILD.search(text) and not patched:
            return out
        prs = [number] + named
        if other:
            return {**out, "build": f"PR #{number} + patches", "build_kind": "patched", "prs": prs}
        label = f"PR #{number}" + (" + " + ", ".join(f"#{n}" for n in named) if named else "")
        return {**out, "build": label, "build_kind": "prs", "prs": prs}
    if not patched:
        return out
    if named and not other:
        return {**out, "build": "main + " + ", ".join(f"#{n}" for n in named), "build_kind": "prs", "prs": named}
    return {**out, "build": "main + patches", "build_kind": "patched", "prs": named}


# In a fork's thread "#N" means the fork's own issue or PR; upstream ones are written in full or, being numbered
# far above any fork's, as a bare number of four digits ("#2054", "boykopovar/AnyPS5#361", "#3816 upstream").
FORK_UPSTREAM_REF = re.compile(r"(?:\b(?P<repo>[\w.\-]+/[\w.\-]+))?#(?P<num>\d{1,6})\b")


def upstream_refs(text: str, upstream: str, fork_floor: int = 1000) -> list[int]:
    """The upstream issue and PR numbers a fork's text names."""
    out = []
    for m in FORK_UPSTREAM_REF.finditer(text or ""):
        repo, num = m.group("repo"), int(m.group("num"))
        if (repo and repo.lower() == upstream.lower()) or (not repo and num >= fork_floor):
            out.append(num)
    return sorted(set(out))


def fork_build(line: str, recipe: list[int], upstream: str) -> dict:
    """A report in a working-group thread: a patched stack, never main. `prs` are the upstream PRs it names
    (in the line, else in the thread's recipe); the evaluation keeps the ones still open."""
    named = upstream_refs(line, upstream) or list(recipe)
    commit = MAIN_COMMIT.search(line)
    return {
        "build": "a working group's stack",
        "build_kind": "patched",
        "prs": named,
        "commit": commit.group(1) if commit else None,
    }


def is_quote(line: str) -> bool:
    """A Markdown blockquote line: someone else's words, not the writer's own report."""
    return line.lstrip().startswith(">")


def content_ids(text: str) -> list[dict]:
    """PlayStation content IDs in a text: {title, region, content_id}."""
    return [
        {"title": m.group("title"), "region": m.group("region"), "content_id": m.group(0)}
        for m in CONTENT_ID_RE.finditer(text or "")
    ]


FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
# Crash lines that count only inside a fenced log block, where they cannot be prose.
CODE_SIG = re.compile(
    r"(?:LowLevelFatalError|Assertion failed|assertion failed|Unhandled exception|Segmentation fault|"
    r"EXCEPTION_ACCESS_VIOLATION|Fatal error:)[^\n]*"
)


def code_blocks(text: str) -> list[list[str]]:
    """The lines of every fenced code block (``` or ~~~); an unclosed block runs to the end."""
    return [lines for lines, _ in code_blocks_with_lead(text)]


def code_blocks_with_lead(text: str) -> list[tuple[list[str], str]]:
    """Every fenced code block with its lead: the paragraph right before it ("On main a29ef592 it stops
    with:"), which says what the logged run was built from."""
    blocks: list[tuple[list[str], str]] = []
    cur: list[str] | None = None
    fence, lead = "", ""
    prose: list[str] = []
    for line in text.splitlines():
        m = FENCE.match(line)
        if cur is None:
            if m:
                cur, fence = [], m.group(1)
                # the last paragraph before the fence: skip blank lines, then read back to the next blank one
                para: list[str] = []
                for prev in reversed(prose):
                    if not prev.strip():
                        if para:
                            break
                        continue
                    para.insert(0, prev)
                lead = "\n".join(para[-5:])
            else:
                prose.append(line)
            continue
        if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not m.group(2).strip():
            blocks.append((cur, lead))
            cur = None
            prose.append("")
            continue
        cur.append(line)
    if cur:
        blocks.append((cur, lead))
    return blocks


def block_stop(lines: list[str]) -> dict | None:
    """The last error line in a fenced log block: where that run stopped."""
    found = None
    for idx, line in enumerate(lines):
        sig = None
        if SIG_START.search(line):
            sig = signature_from(line, lines[idx + 1] if idx + 1 < len(lines) else "")
        if not sig:
            m = CODE_SIG.search(line)
            core = normalise_message(m.group(0)) if m else ""
            if len(core) >= 16:
                sig = {"family": "crash", "key": core.lower(), "display": core}
        if sig:
            found = sig
    return found


BOT_LOGINS = re.compile(r"\[bot\]$|^(?:github-actions|dependabot|copilot-pull-request-reviewer|coderabbitai)$", re.I)


def is_bot(login: str | None) -> bool:
    return bool(login and BOT_LOGINS.search(login))
