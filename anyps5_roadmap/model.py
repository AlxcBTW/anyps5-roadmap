"""The model: merges mined and curated facts into titles, blockers, chains and the ranking."""

from __future__ import annotations

import datetime as dt
import re
from collections import Counter, defaultdict

from .config import STAGES, VERIFY_FROM
from .mine import (
    GPU_RULES, LINE_TITLE_LIMIT, OS_RULES, ENGINE_RULES, PATCHED_BUILD, QUOTED_RE, REGISTER_RE, REPORT_FIELD, SIG_START,
    STOP_WORDS, TITLE_RE, TRACKER_TITLES, classify, clean_name, clip, closing_refs, compute_nid, name_after, name_before,
    name_import, normalise_message, refs_in, sig_match, signature_from, signature_key, signatures_in, stage_in,
    stop_title, strip_md, title_context,
)


def pr_state(state: str | None, merged: bool | None, draft: bool | None) -> str:
    if merged or state == "MERGED":
        return "merged"
    if state == "CLOSED":
        return "closed"
    if draft:
        return "draft"
    return "open" if state == "OPEN" else (state or "unknown").lower()


def key_of(repo: str, number: int) -> str:
    return f"{repo}#{number}"


def short_ref(key: str, upstream: str) -> str:
    repo, num = key.split("#")
    return f"#{num}" if repo == upstream else f"{repo.split('/')[0]}#{num}"


class Model:
    def __init__(self, raw: dict, curated: dict, repo: str, now: dt.datetime, compat_md: str | None = None,
                 progress: dict | None = None):
        self.raw, self.curated, self.repo, self.now = raw, curated, repo, now
        self.issues = {i["number"]: i for i in raw["issues"]}
        self.prs: dict[str, dict] = {}
        self.links: dict[int, dict[str, str]] = defaultdict(dict)   # issue -> {pr key: fixes|mentions}
        self.titles: dict[str, dict] = {}
        self.blockers: dict[str, dict] = {}
        self.issue_info: dict[int, dict] = {}
        self.compat_md = compat_md
        self.gaps: list[str] = []
        self.nid_names = self._nid_index(progress)
        self._index_prs()
        self._link()
        self._mine_issues()
        self._mine_prs()
        self._mine_compat()
        self._apply_curated_titles()
        self._build_blockers()
        self._build_chains()
        self._rank()

    # -- NIDs -----------------------------------------------------------------
    def _nid_index(self, progress: dict | None) -> dict[str, str]:
        """Map NIDs back to names: every identifier in issue/PR text plus the
        function names in progress.json, hashed with the NID algorithm."""
        names: set[str] = set()
        for g in ((progress or {}).get("libraries") or {}).get("groups", []):
            names.update(g.get("done_names", []))
            names.update(g.get("todo_names", []))
        ident = re.compile(r"(?<![\w+\-])[A-Za-z_][A-Za-z0-9_]{2,63}(?![\w+\-])")
        for item in self.raw["issues"] + self.raw["prs"]:
            names.update(ident.findall(item.get("title") or ""))
            names.update(ident.findall(item.get("body") or ""))
            for c in item.get("comments", []) if isinstance(item.get("comments"), list) else []:
                names.update(ident.findall(c.get("body") or ""))
        return {compute_nid(n): n for n in names}

    def resolve_sig(self, sig: dict) -> dict:
        if sig.get("family") == "import" and sig.get("nid") and not sig.get("symbol"):
            name = self.nid_names.get(sig["nid"])
            if name:
                sig["symbol"] = name
                name_import(sig)
        return sig

    # -- PRs and links ------------------------------------------------------
    def _put_pr(self, repo, number, title, url, state, merged, draft, updated, labels=None, author=None):
        key = key_of(repo, number)
        cur = self.prs.get(key, {})
        rec = {
            "key": key, "repo": repo, "number": number, "title": title or cur.get("title"),
            "url": url or cur.get("url") or f"https://github.com/{repo}/pull/{number}",
            "state": pr_state(state, merged, draft) if state else cur.get("state", "unknown"),
            "updated": updated or cur.get("updated"), "labels": labels if labels is not None else cur.get("labels", []),
            "author": author or cur.get("author"),
        }
        self.prs[key] = rec
        return rec

    def _index_prs(self):
        for p in self.raw.get("external_prs", {}).values():
            self._put_pr(p["repo"], p["number"], p.get("title"), p.get("url"), p.get("state"), p.get("merged"), p.get("draft"), p.get("updatedAt"))
        for i in self.raw["issues"]:
            for x in i["xrefs"] + i["closed_by"]:
                if x.get("kind", "pr") == "pr" and key_of(x["repo"], x["number"]) not in self.prs:
                    self._put_pr(x["repo"], x["number"], x.get("title"), x.get("url"), x.get("state"), x.get("merged"), x.get("draft"), x.get("updatedAt"))
        for p in self.raw["prs"]:
            rec = self._put_pr(self.repo, p["number"], p["title"], p["url"], p["state"], p["merged"], p["isDraft"], p["updatedAt"], p["labels"], p.get("author"))
            rec["merged_at"] = p.get("mergedAt")

    def _add_link(self, issue: int, pr_key: str, kind: str):
        if issue not in self.issues or pr_key not in self.prs:
            return
        if self.links[issue].get(pr_key) != "fixes":
            self.links[issue][pr_key] = kind

    def _link(self):
        for i in self.raw["issues"]:
            for x in i["closed_by"]:
                self._add_link(i["number"], key_of(x["repo"], x["number"]), "fixes")
            for x in i["xrefs"]:
                if x["kind"] == "pr":
                    self._add_link(i["number"], key_of(x["repo"], x["number"]), "fixes" if x.get("willClose") else "mentions")
        for p in self.raw["prs"]:
            pk = key_of(self.repo, p["number"])
            text = f"{p['title']}\n{p.get('body') or ''}"
            closing = {(r, n) for r, n in closing_refs(text, self.repo)}
            closing |= {(c["repo"], c["number"]) for c in p.get("closes", [])}
            for r, n in closing:
                if r == self.repo:
                    self._add_link(n, pk, "fixes")
            for r, n in refs_in(text, self.repo):
                if r == self.repo and n != p["number"]:
                    self._add_link(n, pk, "mentions")

    # -- titles -------------------------------------------------------------
    def title(self, tid: str) -> dict:
        if tid not in self.titles:
            self.titles[tid] = {
                "id": tid, "names": Counter(), "engines": Counter(), "kinds": Counter(),
                "evidence": [], "assoc": {}, "mentions": [], "stops": [], "curated": False,
                "name": None, "engine": None, "kind": None, "paths": None, "chain": [], "open_chain": [],
            }
        return self.titles[tid]

    def _associate(self, tid: str, issue: int, level: str, url: str, date: str):
        t = self.title(tid)
        order = ["mention", "report", "stop-line", "signature", "tracker-row", "dependency", "curated"]
        cur = t["assoc"].get(issue)
        if cur is None or order.index(level) > order.index(cur["level"]):
            t["assoc"][issue] = {"level": level, "url": url, "date": date}

    def _sources(self, item: dict, kind: str):
        number = item["number"]
        yield {"kind": kind, "number": number, "url": item["url"], "date": item["createdAt"], "author": item.get("author"),
               "text": f"{item['title']}\n{item.get('body') or ''}", "part": "body"}
        for c in item.get("comments", []) if isinstance(item.get("comments"), list) else []:
            yield {"kind": kind, "number": number, "url": c["url"], "date": c["createdAt"], "author": c.get("author"),
                   "text": c.get("body") or "", "part": "comment"}

    def _mine_text(self, src: dict, info: dict | None):
        text = src["text"]
        lines = text.splitlines()
        src_os = classify(OS_RULES, text)
        src_gpu = classify(GPU_RULES, text)
        for idx, line in enumerate(lines):
            ids = list(dict.fromkeys(TITLE_RE.findall(line)))
            sig = signature_from(line, lines[idx + 1] if idx + 1 < len(lines) else "") if SIG_START.search(line) else None
            if sig:
                self.resolve_sig(sig)
            if not ids:
                continue
            for tid in ids:
                t = self.title(tid)
                pos = line.find(tid)
                n = name_before(line, pos)
                if not n or len(n) < 3:
                    n = name_after(line, pos + len(tid))
                if not n and idx > 0 and re.match(r"\W*title id\W*:", strip_md(line), re.I):
                    # "Game: Silent Hill: The Short Message" on the line before "Title ID: PPSA10112"
                    m = re.match(r"\W*(?:game|title)\W*:\s*(.+)", strip_md(lines[idx - 1]), re.I)
                    n = clean_name(m.group(1).strip()) if m else None
                if n:
                    t["names"][n] += 1
                if len(ids) == 1:
                    # engine and kind only from the parenthesis that holds or follows the ID,
                    # e.g. "Stray (PPSA02100, UE4)" or "PPSA03001 (v01.007.000, Unreal Engine 4)"
                    ctx = title_context(line, pos, len(tid))
                    eng = classify(ENGINE_RULES, ctx)
                    if eng:
                        t["engines"][eng] += 1
                    if re.search(r"\bretail\b", ctx, re.I):
                        t["kinds"]["retail"] += 1
                    if re.search(r"homebrew|github\.com/[\w.\-]+/[\w.\-]+", ctx, re.I) or tid.startswith("PPSA99"):
                        t["kinds"]["homebrew"] += 1
                t["mentions"].append({"kind": src["kind"], "number": src["number"], "url": src["url"], "date": src["date"]})
                if len(ids) <= LINE_TITLE_LIMIT:
                    os_ = classify(OS_RULES, line) or src_os
                    gpu = classify(GPU_RULES, line) or src_gpu
                    build = ("PR #%d" % src["number"]) if src["kind"] == "pr" else ("main + patches" if PATCHED_BUILD.search(line) else "main")
                    st = stage_in(line, pos)
                    quote = clip(re.sub(r"\s+", " ", strip_md(line)).strip(), 280)
                    if st:
                        t["evidence"].append({"stage": st[0], "os": os_, "gpu": gpu, "build": build, "url": src["url"], "date": src["date"],
                                              "note": f"“{st[1]}”", "quote": quote, "origin": "mined", "verified": False})
                    if sig:
                        floor = "Converts" if sig["family"] == "import" else "Starts"
                        t["evidence"].append({"stage": floor, "os": os_, "gpu": gpu, "build": build, "url": src["url"], "date": src["date"],
                                              "note": "stops at: " + sig["display"], "quote": quote, "origin": "mined", "verified": False})
                        t["stops"].append({"sig": sig, "url": src["url"], "date": src["date"], "issue": src["number"] if src["kind"] == "issue" else None,
                                           "os": os_, "gpu": gpu})
                if info is None:
                    continue
                if info["tracker"]:
                    continue
                # "report": the issue is about this title (ID in the issue title, or a
                # "Title:" / "Game:" field in the body). A bare mention, e.g. a
                # measurement on some title, is kept but does not enter the chain.
                if src["part"] == "body" and (idx == 0 or REPORT_FIELD.match(strip_md(line))):
                    self._associate(tid, src["number"], "report", src["url"], src["date"])
                elif len(ids) <= LINE_TITLE_LIMIT and (sig or STOP_WORDS.search(line)):
                    self._associate(tid, src["number"], "stop-line", src["url"], src["date"])
                else:
                    self._associate(tid, src["number"], "mention", src["url"], src["date"])

    def _mine_issues(self):
        for number, issue in self.issues.items():
            texts = [issue["title"], issue.get("body") or ""] + [c["body"] for c in issue["comments"]]
            all_ids = set()
            for t in texts:
                all_ids.update(TITLE_RE.findall(t))
            head = f"{issue['title']}\n{issue.get('body') or ''}"
            sigs = [self.resolve_sig(s) for _, s in signatures_in(head)]
            for q in QUOTED_RE.findall(issue["title"]):
                core = normalise_message(q)
                if re.search(r"[a-z]{3} [a-z]{3}", core):
                    sigs.insert(0, {"family": "title", "key": core.lower(), "display": core})
            counts = Counter(s["key"] for s in sigs)
            primary = None
            if sigs:
                best = max(counts.values())
                primary = next(s for s in sigs if counts[s["key"]] == best)
                if sigs[0]["family"] == "title":
                    # prefer a full log line that the quoted title fragment belongs to
                    full = next((s for s in sigs[1:] if sig_match(s["key"], sigs[0]["key"]) or sigs[0]["key"] in s["key"]), None)
                    primary = full or sigs[0]
            later = [self.resolve_sig(s) for t in texts[2:] for _, s in signatures_in(t)]
            registers = Counter()
            for t in texts:
                for r in set(REGISTER_RE.findall(t)):
                    registers[r] += 1
            self.issue_info[number] = {
                "titles": sorted(all_ids), "tracker": len(all_ids) >= TRACKER_TITLES,
                "signature": primary, "signatures": list({s["key"]: s for s in sigs + later}.values())[:12],
                "text": "\n".join(texts), "registers": registers,
            }
            for src in self._sources(issue, "issue"):
                self._mine_text(src, self.issue_info[number])

    def _mine_prs(self):
        for p in self.raw["prs"]:
            self._mine_text({"kind": "pr", "number": p["number"], "url": p["url"], "date": p["createdAt"],
                             "author": p.get("author"), "text": f"{p['title']}\n{p.get('body') or ''}", "part": "body"}, None)

    def _mine_compat(self):
        if not self.compat_md:
            return
        header = []
        for line in self.compat_md.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if "ID" in cells and "Game" in cells:
                header = cells
                continue
            ids = TITLE_RE.findall(line)
            if not ids or not header:
                continue
            row = dict(zip(header, cells))
            t = self.title(ids[0])
            if row.get("Game"):
                t["names"][row["Game"]] += 5
            for os_name in ("Windows", "Linux", "macOS"):
                status = row.get(os_name, "")
                st = stage_in(status, 0) if status and status != "?" else None
                if st:
                    t["evidence"].append({"stage": st[0], "os": os_name, "gpu": None, "build": "main",
                                          "url": f"https://github.com/{self.repo}/blob/main/docs/user/COMPATIBILITY.md",
                                          "date": None, "note": f"COMPATIBILITY.md: {status}", "quote": line.strip(),
                                          "origin": "upstream", "verified": True})

    def _apply_curated_titles(self):
        for ct in self.curated.get("titles", []):
            t = self.title(ct["id"])
            t["curated"] = True
            for k in ("name", "engine", "kind", "paths"):
                if ct.get(k):
                    t[k] = ct[k]
            for ev in ct.get("evidence", []):
                t["evidence"].append({**{"os": None, "gpu": None, "build": "main", "note": "", "quote": None}, **ev,
                                      "origin": "curated", "verified": True})
        self._apply_stage_reviews()
        for t in self.titles.values():
            if not t["name"] and t["names"]:
                top = t["names"].most_common()
                best = max(c for _, c in top)
                t["name"] = max((n for n, c in top if c == best), key=len)
            if not t["engine"] and t["engines"]:
                t["engine"] = t["engines"].most_common(1)[0][0]
            if not t["kind"] and t["kinds"]:
                t["kind"] = t["kinds"].most_common(1)[0][0]

    # -- blockers -----------------------------------------------------------
    def _issue_prs(self, number: int) -> list[dict]:
        out = []
        for key, kind in self.links.get(number, {}).items():
            pr = self.prs[key]
            out.append({"key": key, "ref": short_ref(key, self.repo), "url": pr["url"], "title": pr["title"],
                        "state": pr["state"], "link": kind, "updated": pr["updated"], "origin": "mined"})
        rank = {"open": 0, "draft": 1, "merged": 2, "closed": 3, "unknown": 4}
        out.sort(key=lambda p: (p["link"] != "fixes", rank.get(p["state"], 4), -(int(p["key"].split("#")[1]))))
        return out

    def _area(self, issue: dict | None, prs: list[dict], sig: dict | None) -> str | None:
        votes = Counter()
        for p in prs:
            if p["link"] == "fixes" or p["state"] == "open":
                for label in self.prs[p["key"]]["labels"]:
                    if label in ("shader", "agc", "libkernel", "relinker", "libc", "prx"):
                        votes[label] += 2 if p["link"] == "fixes" else 1
        if votes:
            return votes.most_common(1)[0][0]
        title = (issue or {}).get("title", "")
        for rx, area in [(r"^(Recompiler|Structurizer|Shader|SPIR-V|v_|s_)", "shader"), (r"^(AGC|Layered|Vulkan|NVIDIA|Intel)", "agc"),
                         (r"^Relinker", "relinker"), (r"^(libkernel|Kernel)", "libkernel"), (r"^(libc|LibcInternal)", "libc")]:
            if re.search(rx, title, re.I):
                return area
        if sig:
            if sig["family"] == "recompile":
                return "shader"
            if sig["family"] in ("agc", "present"):
                return "agc"
            if sig["family"] == "import":
                lib = (sig.get("library") or "").lower()
                sym = sig.get("symbol") or ""
                if lib.startswith("libkernel") or (not lib and re.match(r"(pthread_|sig|_umtx|sysctl|sched_|sceKernel|cpuset|_?fstat|kqueue|kevent|mmap|munmap)", sym)):
                    return "libkernel"
                if "libc" in lib or "posix" in lib or (not lib and sym and not sym.startswith("sce")):
                    return "libc"
                return "prx"
        return None

    def _build_blockers(self):
        curated_by_issue = {}
        for cb in self.curated.get("blockers", []):
            bid = str(cb["id"])
            issue = self.issues.get(cb.get("issue")) if cb.get("issue") else None
            if cb.get("issue") and not issue:
                self.gaps.append(f"curated blocker {bid}: issue #{cb['issue']} not in the fetched window")
            prs = []
            for ref in cb.get("fix_prs", []) + cb.get("related_prs", []):
                key = key_of(ref.get("repo", self.repo), int(ref["number"]))
                pr = self.prs.get(key) or self._put_pr(ref.get("repo", self.repo), int(ref["number"]), None, None, None, None, None, None)
                prs.append({"key": key, "ref": short_ref(key, self.repo), "url": pr["url"], "title": pr["title"], "state": pr["state"],
                            "link": "fixes" if ref in cb.get("fix_prs", []) else "related", "updated": pr["updated"],
                            "note": ref.get("note"), "origin": "curated"})
            mined = self._issue_prs(cb["issue"]) if issue else []
            seen = {p["key"] for p in prs}
            prs += [p for p in mined if p["key"] not in seen]
            info = self.issue_info.get(cb.get("issue"), {})
            sig = info.get("signature")
            status = cb.get("status")
            if not status:
                if issue:
                    status = "open" if issue["state"] == "OPEN" else "resolved"
                else:
                    status = "resolved" if any(p["state"] == "merged" and p["link"] == "fixes" and not p.get("note") for p in prs) else "open"
            self.blockers[bid] = {
                "id": bid, "issue": cb.get("issue"), "url": issue["url"] if issue else (prs[0]["url"] if prs else (cb.get("sources") or [None])[0]),
                "title": cb.get("title") or (issue["title"] if issue else bid),
                "signature": cb.get("signature") or (sig["display"] if sig else None),
                "signature_key": signature_key(cb.get("signature")) or (sig["key"] if sig else None),
                "area": cb.get("area") or self._area(issue, prs, sig), "status": status,
                "prs": prs, "next": cb.get("next"), "help_wanted": cb.get("help_wanted"), "notes": cb.get("notes"),
                "owner": cb.get("owner") or (", ".join(issue.get("assignees", [])) if issue else None) or None,
                "origin": "curated", "tracker": False,
                "created": issue["createdAt"] if issue else None,
                "last_activity": max([d for d in [issue["updatedAt"] if issue else None] + [p["updated"] for p in prs] if d] or [None], key=lambda d: d or ""),
                "labels": issue["labels"] if issue else [],
            }
            if cb.get("issue"):
                curated_by_issue[cb["issue"]] = bid
        ignored = {int(x["issue"]) for x in self.curated.get("not_blockers", [])}
        self.not_blockers = {int(x["issue"]): x.get("reason", "") for x in self.curated.get("not_blockers", [])}
        for number, issue in self.issues.items():
            if number in curated_by_issue or number in ignored:
                continue
            info = self.issue_info[number]
            has_titles = any(number in t["assoc"] and t["assoc"][number]["level"] != "mention" for t in self.titles.values())
            if not (info["signature"] or has_titles):
                continue
            prs = self._issue_prs(number)
            sig = info["signature"]
            self.blockers[str(number)] = {
                "id": str(number), "issue": number, "url": issue["url"], "title": issue["title"],
                "signature": sig["display"] if sig else None, "signature_key": sig["key"] if sig else None,
                "area": self._area(issue, prs, sig), "status": "open" if issue["state"] == "OPEN" else "resolved",
                "prs": prs, "next": None, "help_wanted": None, "notes": None,
                "owner": ", ".join(issue.get("assignees", [])) or None, "origin": "mined", "tracker": info["tracker"],
                "created": issue["createdAt"],
                "last_activity": max([issue["updatedAt"]] + [p["updated"] for p in prs if p["updated"]]),
                "labels": issue["labels"],
            }
        self.issue_to_blocker = {b["issue"]: bid for bid, b in self.blockers.items() if b["issue"]}

    # -- chains -------------------------------------------------------------
    def _build_chains(self):
        deps = self.raw.get("dependencies", {})
        sig_index = [(b["signature_key"], bid) for bid, b in self.blockers.items()
                     if b["signature_key"] and b["status"] == "open" and not b["tracker"]]
        curated_chains = {ct["id"]: ct.get("blockers", []) for ct in self.curated.get("titles", [])}
        for tid, t in self.titles.items():
            steps: list[dict] = []
            seen: set[str] = set()

            def add(bid, origin, why, scope=None, at=None):
                if bid in seen or bid not in self.blockers:
                    return
                seen.add(bid)
                step = {"blocker": bid, "origin": origin, "why": why, "scope": scope}
                if at is None:
                    steps.append(step)
                else:
                    steps.insert(at, step)

            for step in curated_chains.get(tid, []):
                add(str(step["id"]), "curated", step.get("why", "curated"), step.get("scope"))
            # the latest recorded stop decides which mined blocker comes first
            latest = sorted(t["stops"], key=lambda s: s["date"] or "", reverse=True)
            for stop in latest[:1]:
                hit = next((bid for key, bid in sig_index if sig_match(key, stop["sig"]["key"]) or key == stop["sig"]["key"]), None)
                if hit:
                    add(hit, "mined", "latest recorded stop matches its signature")
                    if self.blockers[hit]["issue"]:
                        t["assoc"].setdefault(self.blockers[hit]["issue"], {"level": "signature", "url": stop["url"], "date": stop["date"]})
                elif stop["issue"] and self.issue_info.get(stop["issue"], {}).get("tracker"):
                    vid = self._virtual_blocker(stop["issue"], stop)
                    sig_index.append((self.blockers[vid]["signature_key"], vid))
                    add(vid, "mined", f"latest recorded stop, listed in tracker #{stop['issue']}")
            strong = sorted(((n, a) for n, a in t["assoc"].items() if a["level"] != "mention"),
                            key=lambda na: self.issues.get(na[0], {}).get("createdAt", ""))
            for number, a in strong:
                bid = self.issue_to_blocker.get(number)
                if not bid:
                    continue
                # GitHub-native dependencies: what blocks this issue comes first
                for dep in deps.get(str(number), []):
                    dbid = self.issue_to_blocker.get(dep["number"]) if dep.get("repo", self.repo) == self.repo else None
                    if dbid:
                        add(dbid, "github", f"#{number} is blocked by #{dep['number']} (GitHub dependency)")
                add(bid, "mined", {"report": "reported on this issue", "stop-line": "a comment names it at this stop",
                                   "signature": "stop signature matches", "tracker-row": "tracker row"}.get(a["level"], a["level"]))
            t["chain"] = steps

    def _virtual_blocker(self, number: int, stop: dict) -> str:
        """A crash site that only lives as a row in a tracker issue becomes its own
        blocker, keyed by signature, so one tracker does not swallow every title."""
        sig = stop["sig"]
        slug = sig.get("symbol") or sig.get("nid") or sig.get("library") or re.sub(r"\W+", "-", sig["key"])[:40].strip("-")
        bid = f"{number}~{slug}"
        if bid in self.blockers:
            return bid
        prs = []
        symbol = sig.get("symbol")
        if symbol and len(symbol) >= 4:
            rx = re.compile(r"(?<![\w])" + re.escape(symbol) + r"(?![\w])")
            for pr in self.prs.values():
                if pr["repo"] == self.repo and pr["title"] and rx.search(pr["title"]):
                    prs.append({"key": pr["key"], "ref": short_ref(pr["key"], self.repo), "url": pr["url"], "title": pr["title"],
                                "state": pr["state"], "link": "related", "updated": pr["updated"], "origin": "mined"})
        rank = {"open": 0, "draft": 1, "merged": 2, "closed": 3}
        prs.sort(key=lambda p: (rank.get(p["state"], 4), -(int(p["key"].split("#")[1]))))
        merged_after = any(p["state"] == "merged" and (self.prs[p["key"]].get("merged_at") or "") > (stop["date"] or "") for p in prs)
        parent = self.issues[number]
        self.blockers[bid] = {
            "id": bid, "issue": None, "parent": number, "url": stop["url"],
            "title": stop_title(sig), "signature": sig["display"], "signature_key": sig["key"],
            "area": self._area(None, prs, sig), "status": "resolved" if merged_after or parent["state"] != "OPEN" else "open",
            "prs": prs[:6], "next": None, "help_wanted": None, "notes": f"Tracked as a row in #{number}: {parent['title']}",
            "owner": None, "origin": "mined", "tracker": False, "created": stop["date"],
            "last_activity": max([stop["date"] or ""] + [p["updated"] or "" for p in prs]) or None, "labels": [],
        }
        return bid

    @staticmethod
    def paths(t: dict) -> dict[str, list[dict]]:
        """Chains per OS/GPU path. A step with a scope applies only to the paths it names."""
        names = t.get("paths") or ["any"]
        return {p: [s for s in t["chain"] if not s.get("scope") or p in s["scope"]] for p in names}

    def _apply_stage_reviews(self):
        """Hand verdicts on mined stages (data/blockers.json stage_reviews). The quoted
        source is dropped for that title; confirmed and downgraded verdicts add a
        curated stage with its own source and quote."""
        for rv in self.curated.get("stage_reviews", []):
            t = self.title(rv["title"])
            claim = rv["claim_url"].rstrip("/")
            t["evidence"] = [e for e in t["evidence"]
                             if not (e["origin"] == "mined" and (e["url"] or "").split("#")[0].rstrip("/") == claim)]
            t.setdefault("reviews", []).append({k: rv.get(k) for k in ("claim", "claim_url", "verdict", "stage", "url", "quote", "reason")})
            if rv["verdict"] in ("confirmed", "downgraded"):
                t["evidence"].append({"stage": rv["stage"], "os": rv.get("os"), "gpu": rv.get("gpu"), "build": rv.get("build") or "main",
                                      "url": rv["url"], "date": rv.get("date"), "note": rv["quote"], "quote": rv["quote"],
                                      "origin": "curated", "verified": True, "review": rv["verdict"]})

    def best_stage(self, t: dict) -> dict | None:
        """The best verified stage. Curated evidence wins; without it, upstream and mined
        evidence count, but a mined stage of Menus or higher only counts once a person
        has reviewed it (see unverified_claim)."""
        pool = [e for e in t["evidence"] if e["origin"] == "curated"]
        if not pool:
            pool = [e for e in t["evidence"] if e["origin"] == "upstream" or STAGES.index(e["stage"]) < VERIFY_FROM]
        if not pool:
            return None
        origin_rank = {"curated": 2, "upstream": 1, "mined": 0}
        best = max(pool, key=lambda e: (STAGES.index(e["stage"]), origin_rank.get(e["origin"], 0), e.get("date") or ""))
        return {**best, "verified": best["origin"] in ("curated", "upstream")}

    def unverified_claim(self, t: dict) -> dict | None:
        """The highest mined stage of Menus or higher that nobody has reviewed yet, when it
        is above the best verified stage. Shown as a claim, never sorted or ranked on."""
        best = self.best_stage(t)
        floor = STAGES.index(best["stage"]) if best else -1
        claims = [e for e in t["evidence"] if e["origin"] == "mined" and STAGES.index(e["stage"]) >= VERIFY_FROM
                  and STAGES.index(e["stage"]) > floor]
        if not claims:
            return None
        c = max(claims, key=lambda e: (STAGES.index(e["stage"]), e.get("date") or ""))
        return {"stage": c["stage"], "url": c["url"], "quote": c.get("quote") or c.get("note")}

    def _rank(self):
        for b in self.blockers.values():
            b.update({"frontier": 0, "one_fix_away": 0, "total": 0, "titles": [], "frontier_titles": [], "one_fix_titles": []})
        for tid, t in self.titles.items():
            best = self.best_stage(t)
            done = best is not None and best["stage"] == "Playable"
            t["open_chain"] = [s for s in t["chain"] if self.blockers[s["blocker"]]["status"] == "open"]
            listed = set()
            for s in t["open_chain"]:
                b = self.blockers[s["blocker"]]
                if s["blocker"] not in listed:
                    b["total"] += 1
                    b["titles"].append(tid)
                    listed.add(s["blocker"])
            if done:
                continue
            front, single = set(), set()
            for scope, chain in self.paths(t).items():
                open_steps = [s["blocker"] for s in chain if self.blockers[s["blocker"]]["status"] == "open"]
                if open_steps:
                    front.add(open_steps[0])
                    if len(set(open_steps)) == 1:
                        single.add(open_steps[0])
            for bid in front:
                self.blockers[bid]["frontier"] += 1
                self.blockers[bid]["frontier_titles"].append(tid)
            for bid in single:
                self.blockers[bid]["one_fix_away"] += 1
                self.blockers[bid]["one_fix_titles"].append(tid)
        for b in self.blockers.values():
            b["score"] = 3 * b["one_fix_away"] + 2 * b["frontier"] + b["total"]

    def ranking(self) -> list[dict]:
        open_ = [b for b in self.blockers.values() if b["status"] == "open"]
        return sorted(open_, key=lambda b: (-b["score"], -b["total"], b["origin"] != "curated", -(b["issue"] or 0)))
