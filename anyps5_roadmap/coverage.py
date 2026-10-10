"""Coverage: RDNA ISA decode, HLE libraries (progress.json), PM4 packets and registers."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import TYPE_CHECKING

from .config import DRIVER_DIR, PM4_HEADER, PM4_SOURCE, PROGRESS_URL

if TYPE_CHECKING:  # used in annotations only
    from .model import Model
    from .upstream import Upstream


def parse_pm4_opcodes(header: str) -> list[dict]:
    return [{"opcode": int(v, 16), "name": n} for v, n in re.findall(r"\{\s*0x([0-9A-Fa-f]+)\s*,\s*\"(\w+)\"\s*\}", header)]


def parse_unsupported_reason(source: str) -> dict:
    """Classify opcodes from Pm4::UnsupportedReason(): {opcode: (status, reason)}.

    A case group that ends in `return {};` is handled; one that ends in a string
    is rejected with that reason; a group with an `if (...) return "..."` before
    `return {};` is handled conditionally. Custom NOP sub-opcodes are returned
    under keys ("custom", n).
    """
    m = re.search(r"UnsupportedReason\([^)]*\)\s*\{", source)
    if not m:
        return {}
    depth, i = 0, m.end() - 1
    for i in range(m.end() - 1, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                break
    body = source[m.end():i]
    out: dict = {}
    custom = re.search(r"if \(opcode == 0x10\)\s*\{(.*?)\n    \}", body, re.S)
    rest = body
    if custom:
        rest = body[:custom.start()] + body[custom.end():]
        for grp in re.finditer(r"((?:case [^:]+:\s*)+)(.*?)(?=case |default:|\}\s*$)", custom.group(1), re.S):
            values = [int(x, 0) for x in re.findall(r"case (0x[0-9a-fA-F]+|\d+):", grp.group(1))]
            status, reason = _classify_case(grp.group(2))
            for v in values:
                out[("custom", v)] = (status, reason)
    for grp in re.finditer(r"((?:case 0x[0-9a-fA-F]+:\s*)+)(.*?)(?=case 0x|default:)", rest, re.S):
        values = [int(x, 16) for x in re.findall(r"case 0x([0-9a-fA-F]+):", grp.group(1))]
        status, reason = _classify_case(grp.group(2))
        for v in values:
            out[v] = (status, reason)
    d = re.search(r"default:\s*return\s*\"([^\"]*)\"", rest)
    out["default"] = ("rejected", d.group(1) if d else None)
    if ("custom", 0) in out:
        out[0x10] = out[("custom", 0)]  # a plain NOP is custom sub-opcode 0
    return out


def _classify_case(code: str) -> tuple[str, str | None]:
    strings = re.findall(r"return\s*\"([^\"]*)\"", code)
    empty = re.search(r"return\s*\{\s*\}", code)
    if empty and strings:
        cond = re.search(r"if\s*\((.+?)\)\s*return", code, re.S)
        return "conditional", (f"rejected only when {cond.group(1).strip()}: " if cond else "") + strings[0]
    if empty:
        return "handled", None
    if strings:
        return "rejected", strings[0]
    return "unknown", None


CUSTOM_PM4 = {0x05: "DRAW_RESET", 0x06: "WAIT_FLIP_DONE", 0x09: "DISPATCH_RESET", 0x0b: "PUSH_MARKER", 0x0c: "POP_MARKER",
              0x14: "ACQUIRE_MEM_CUSTOM", 0x15: "WRITE_DATA_CUSTOM", 0x17: "FLIP", 0x18: "RELEASE_MEM_CUSTOM",
              0x19: "DMA_DATA_CUSTOM", 0x1a: "CONTEXT_STATE"}


NOT_REGISTER = re.compile(r"_BIT$|^SQ_(?:RSRC|SEL|BUF|IMG)_|_FMT_|_TYPE_\d")


def mention_count(names: list[str], texts: dict[int, str]) -> dict[str, list[int]]:
    out = {}
    for name in names:
        rx = re.compile(r"(?<![A-Za-z0-9_])(?:IT_|PKT3_)?" + re.escape(name) + r"(?![A-Za-z0-9_])")
        out[name] = sorted(n for n, t in texts.items() if rx.search(t))
    return out


def build_coverage(model: Model, upstream: Upstream, progress: dict | None, log) -> dict:
    texts = {n: info["text"] for n, info in model.issue_info.items()}
    cov: dict = {"isa": None, "hle": None, "pm4": None, "registers": None}
    if progress:
        sh = progress.get("shaders", {})
        cov["isa"] = {"done": sh.get("done"), "total": sh.get("total"), "percent": sh.get("percent"),
                      "groups": [{"encoding": g["name"], "done": g["done"], "todo": g["todo"],
                                  "percent": round(100 * g["done"] / max(1, g["done"] + g["todo"]), 1),
                                  "todo_names": g.get("todo_names", [])} for g in sh.get("groups", [])],
                      "extra": sh.get("extra", []), "source": PROGRESS_URL}
        lib = progress.get("libraries", {})
        groups = []
        for g in lib.get("groups", []):
            todo = g.get("todo_names", [])
            asked = {}
            for name in todo:
                rx = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])")
                hits = sorted(n for n, t in texts.items() if rx.search(t))
                if hits:
                    asked[name] = hits
            groups.append({"library": g["name"], "label": g.get("label"), "done": g["done"], "todo": g["todo"],
                           "percent": round(100 * g["done"] / max(1, g["done"] + g["todo"]), 1),
                           "requested": asked, "todo_names": todo})
        groups.sort(key=lambda g: (-len(g["requested"]), -g["todo"], g["library"]))
        cov["hle"] = {"done": lib.get("done"), "total": lib.get("total"), "percent": lib.get("percent"), "groups": groups, "source": PROGRESS_URL}
    header = upstream.raw(PM4_HEADER)
    source = upstream.show(PM4_SOURCE) or (upstream.raw(PM4_SOURCE) if not upstream.checkout else None)
    if header:
        ops = parse_pm4_opcodes(header)
        reasons = parse_unsupported_reason(source or "")
        exec_files = [f for f in upstream.files(DRIVER_DIR + "/Execution/src") if f.endswith(".cpp")]
        names = [o["name"] for o in ops] + list(CUSTOM_PM4.values())
        mentions = mention_count(names, texts)
        refs = {}
        for o in ops:
            pat = r"(opcode|op) == 0x0*%x\b|case 0x0*%x:" % (o["opcode"], o["opcode"])
            hits = upstream.grep(pat, DRIVER_DIR + "/Execution/src")
            refs[o["opcode"]] = sorted(hits)
        rows = []
        for o in ops:
            status, reason = reasons.get(o["opcode"], reasons.get("default", ("unknown", None))) if reasons else ("unknown", None)
            rows.append({"opcode": o["opcode"], "hex": f"0x{o['opcode']:02X}", "name": o["name"], "kind": "type-3",
                         "status": status, "reason": reason, "source_files": refs.get(o["opcode"], []),
                         "issues": mentions.get(o["name"], [])})
        for sub, name in CUSTOM_PM4.items():
            status, reason = reasons.get(("custom", sub), ("rejected", "custom packet has no implemented contract")) if reasons else ("unknown", None)
            rows.append({"opcode": sub, "hex": f"NOP·0x{sub:02X}", "name": name, "kind": "custom", "status": status,
                         "reason": reason, "source_files": [], "issues": mentions.get(name, [])})
        counts = Counter(r["status"] for r in rows if r["kind"] == "type-3")
        cov["pm4"] = {"rows": rows, "counts": dict(counts), "total": len(ops),
                      "rule": "status from the case groups of Pm4::UnsupportedReason() in " + PM4_SOURCE +
                              "; source_files lists Execution/src files that compare `opcode == 0xNN` or use `case 0xNN:`",
                      "header": PM4_HEADER, "source": PM4_SOURCE, "classified": bool(reasons)}
    reg_counts: Counter = Counter()
    reg_issues: dict[str, list[int]] = defaultdict(list)
    for n, info in model.issue_info.items():
        for r in info["registers"]:
            reg_counts[r] += 1
            reg_issues[r].append(n)
    regs = []
    for name, count in [(n, c) for n, c in reg_counts.most_common() if not NOT_REGISTER.search(n)][:30]:
        hits = upstream.grep(r"\b%s\b" % name, DRIVER_DIR) if upstream.checkout else {}
        regs.append({"name": name, "issue_count": count, "issues": sorted(reg_issues[name]), "source_files": len(hits)})
    cov["registers"] = regs
    return cov
