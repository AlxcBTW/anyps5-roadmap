"""The model: merges mined and curated facts into titles, blockers, chains and the ranking."""

from __future__ import annotations

import datetime as dt
import re
from collections import Counter, defaultdict

from . import evaluate
from .config import TAGS
from .identity import PLACEHOLDER_IDS, CatalogEntry, Identity, TitleNames, resolve
from .mine import (
    ENGINE_RULES,
    GPU_RULES,
    LINE_TITLE_LIMIT,
    MAIN_BUILD,
    MAIN_COMMIT,
    OS_RULES,
    QUOTED_RE,
    REGISTER_RE,
    REPORT_FIELD,
    SIG_START,
    STOP_WORDS,
    TITLE_RE,
    TRACKER_TITLES,
    blank,
    block_stop,
    bring_up_form,
    build_detail,
    carried_refs,
    classify,
    clean_name,
    clip,
    closing_refs,
    code_blocks_with_lead,
    compute_nid,
    content_ids,
    fork_build,
    is_bot,
    is_quote,
    name_after,
    name_before,
    name_import,
    normalise_message,
    refs_in,
    restated_spans,
    resubmitted_refs,
    run_text,
    sig_match,
    signature_from,
    signature_key,
    signatures_in,
    stage_in,
    stop_title,
    strip_md,
    title_context,
    unblocking_refs,
    upstream_refs,
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
    def __init__(
        self,
        raw: dict,
        curated: dict,
        repo: str,
        now: dt.datetime,
        progress: dict | None = None,
        catalog: dict[str, CatalogEntry] | None = None,
        games: dict | None = None,
    ):
        """`catalog` is the parsed PlayStation title list and `games` data/games.json; both may be empty."""
        self.raw, self.curated, self.repo, self.now = raw, curated, repo, now
        self.catalog = catalog or {}
        self.games_curated = games or {}
        self.placeholders: set[str] = set()
        self.issues = {i["number"]: i for i in raw["issues"]}
        self.prs: dict[str, dict] = {}
        self.links: dict[int, dict[str, str]] = defaultdict(dict)  # issue -> {pr key: fixes|mentions}
        # issue -> pr key -> how the link is known: closing (GitHub's closing references),
        # xref (a timeline cross-reference) or text (a reference read from PR text)
        self.link_via: dict[int, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        self.titles: dict[str, dict] = {}
        self.blockers: dict[str, dict] = {}
        self.issue_info: dict[int, dict] = {}
        self.gaps: list[str] = []
        self.nid_names = self._nid_index(progress)
        self._index_prs()
        self._link()
        self._index_resubmissions()
        self._mine_issues()
        self._mine_prs()
        self._mine_discussions()
        self._mine_working_groups()
        self._apply_curated_titles()
        self._resolve_games()
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
            for key in ("comments", "reviews", "review_comments"):
                for c in item.get(key) if isinstance(item.get(key), list) else []:
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
            "key": key,
            "repo": repo,
            "number": number,
            "title": title or cur.get("title"),
            "url": url or cur.get("url") or f"https://github.com/{repo}/pull/{number}",
            "state": pr_state(state, merged, draft) if state else cur.get("state", "unknown"),
            "updated": updated or cur.get("updated"),
            "labels": labels if labels is not None else cur.get("labels", []),
            "author": author or cur.get("author"),
        }
        self.prs[key] = rec
        return rec

    def _index_prs(self):
        for p in self.raw.get("external_prs", {}).values():
            self._put_pr(
                p["repo"],
                p["number"],
                p.get("title"),
                p.get("url"),
                p.get("state"),
                p.get("merged"),
                p.get("draft"),
                p.get("updatedAt"),
            )
        for i in self.raw["issues"]:
            for x in i["xrefs"] + i["closed_by"]:
                if x.get("kind", "pr") == "pr" and key_of(x["repo"], x["number"]) not in self.prs:
                    self._put_pr(
                        x["repo"],
                        x["number"],
                        x.get("title"),
                        x.get("url"),
                        x.get("state"),
                        x.get("merged"),
                        x.get("draft"),
                        x.get("updatedAt"),
                    )
        for p in self.raw["prs"]:
            rec = self._put_pr(
                self.repo,
                p["number"],
                p["title"],
                p["url"],
                p["state"],
                p["merged"],
                p["isDraft"],
                p["updatedAt"],
                p["labels"],
                p.get("author"),
            )
            rec["merged_at"] = p.get("mergedAt")

    def _add_link(self, issue: int, pr_key: str, kind: str, via: str):
        if issue not in self.issues or pr_key not in self.prs:
            return
        if self.links[issue].get(pr_key) != "fixes":
            self.links[issue][pr_key] = kind
        self.link_via[issue][pr_key].add(via)

    def _link(self):
        for i in self.raw["issues"]:
            for x in i["closed_by"]:
                self._add_link(i["number"], key_of(x["repo"], x["number"]), "fixes", "closing")
            for x in i["xrefs"]:
                if x["kind"] == "pr":
                    kind = "fixes" if x.get("willClose") else "mentions"
                    self._add_link(i["number"], key_of(x["repo"], x["number"]), kind, "xref")
        for p in self.raw["prs"]:
            pk = key_of(self.repo, p["number"])
            for c in p.get("closes", []):
                if c["repo"] == self.repo:
                    self._add_link(c["number"], pk, "fixes", "closing")
            # the PR's own timeline: an upstream issue (or a comment on it) that names this PR
            for x in p.get("xrefs", []):
                if x["kind"] == "issue" and x["repo"] == self.repo:
                    self._add_link(x["number"], pk, "mentions", "xref")
            text = f"{p['title']}\n{p.get('body') or ''}"
            for r, n in closing_refs(text, self.repo):
                if r == self.repo:
                    self._add_link(n, pk, "fixes", "text")
            for r, n in unblocking_refs(text, self.repo):
                if r == self.repo and n != p["number"]:
                    self._add_link(n, pk, "fixes", "unblocks")
            for r, n in refs_in(text, self.repo):
                if r == self.repo and n != p["number"]:
                    self._add_link(n, pk, "mentions", "text")

    def _index_resubmissions(self):
        """PRs that say they resubmit, replace or carry a PR closed without merge ("This is #1872 again",
        "Resubmission of #2174", "Replaces #2481", "Carries #2738") or carry a fork PR ("Carries
        AlxcBTW/AnyPS5#26"): earlier PR key, lower case -> keys of the PRs that stand in for it."""
        self.stand_ins: dict[str, list[str]] = defaultdict(list)
        for p in self.raw["prs"]:
            new = key_of(self.repo, p["number"])
            text = f"{p['title']}\n{p.get('body') or ''}"
            olds = [key_of(self.repo, n) for n in resubmitted_refs(text)]
            olds += [key_of(repo, n) for repo, n in carried_refs(text, self.repo)]
            for old in olds:
                if old.lower() != new.lower() and self._replaceable(old) and new not in self.stand_ins[old.lower()]:
                    self.stand_ins[old.lower()].append(new)

    def _replaceable(self, key: str) -> bool:
        """Another PR can stand in for an upstream PR closed without merge, and for a fork PR in any state."""
        repo, num = key.split("#")
        if repo.lower() != self.repo.lower():
            return True
        return self.prs.get(key_of(self.repo, int(num)), {}).get("state") == "closed"

    def _with_stand_ins(self, prs: list[dict]) -> list[dict]:
        """A fix PR closed without merge, or a fork fix PR, lives on in the PR that resubmits or carries it,
        which becomes a fix PR too. A partial fix (a note starting with "partial") stays partial in its
        resubmission."""
        out, seen = list(prs), {p["key"] for p in prs}
        queue = [p for p in prs if p["link"] == "fixes" and self._replaceable(p["key"])]
        while queue:
            old = queue.pop(0)
            for key in self.stand_ins.get(old["key"].lower(), []):
                if key in seen:
                    continue
                seen.add(key)
                pr = self.prs[key]
                note = old.get("note") if (old.get("note") or "").startswith("partial") else None
                rec = {
                    "key": key,
                    "ref": short_ref(key, self.repo),
                    "url": pr["url"],
                    "title": pr["title"],
                    "state": pr["state"],
                    "link": "fixes",
                    "updated": pr["updated"],
                    "note": note,
                    "origin": "mined",
                    "via": ["resubmission"],
                    "resubmits": old["ref"],
                }
                at = out.index(old) + 1  # next to the PR it stands in for, so a short list still shows it
                while at < len(out) and out[at].get("resubmits") == old["ref"]:
                    at += 1
                out.insert(at, rec)
                if pr["state"] == "closed":
                    queue.append(rec)
        return out

    # -- titles -------------------------------------------------------------
    def title(self, tid: str) -> dict:
        if tid not in self.titles:
            self.titles[tid] = {
                "id": tid,
                "names": Counter(),
                "engines": Counter(),
                "kinds": Counter(),
                "evidence": [],
                "assoc": {},
                "mentions": [],
                "stops": [],
                "curated": False,
                "name": None,
                "engine": None,
                "kind": None,
                "paths": None,
                "chain": [],
                "open_chain": [],
                "tags": [],
                "tag_sources": [],
                "content_ids": {},
                "game": None,
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
        yield {
            "kind": kind,
            "number": number,
            "url": item["url"],
            "date": item["createdAt"],
            "author": item.get("author"),
            "text": f"{item['title']}\n{item.get('body') or ''}",
            "part": "body",
        }
        for key, part in (("comments", "comment"), ("reviews", "review"), ("review_comments", "review")):
            for c in item.get(key) if isinstance(item.get(key), list) else []:
                if is_bot(c.get("author")):
                    continue
                yield {
                    "kind": kind,
                    "number": number,
                    "url": c["url"],
                    "date": c["createdAt"],
                    "author": c.get("author"),
                    "text": c.get("body") or "",
                    "part": part,
                }

    def _mine_text(self, src: dict, info: dict | None):
        text = src["text"]
        lines = text.splitlines()
        runs = run_text(text)
        src_os = classify(OS_RULES, runs)
        src_gpu = classify(GPU_RULES, runs)
        for c in content_ids(text):
            if c["title"] not in PLACEHOLDER_IDS:
                self.title(c["title"])["content_ids"][c["content_id"]] = c["region"]
        for idx, line in enumerate(lines):
            ids = [i for i in dict.fromkeys(TITLE_RE.findall(line)) if i not in PLACEHOLDER_IDS]
            self.placeholders.update(i for i in TITLE_RE.findall(line) if i in PLACEHOLDER_IDS)
            sig = (
                signature_from(line, lines[idx + 1] if idx + 1 < len(lines) else "") if SIG_START.search(line) else None
            )
            if sig:
                self.resolve_sig(sig)
            if not ids:
                continue
            if is_quote(line):
                # a blockquote repeats someone else's words: the title is mentioned, nothing more
                for tid in ids:
                    self.title(tid)["mentions"].append(
                        {"kind": src["kind"], "number": src["number"], "url": src["url"], "date": src["date"]}
                    )
                continue
            # what the line says itself: a restatement of the description is read for no title
            restated = restated_spans(line)
            own_line = blank(line, restated)
            for tid in ids:
                t = self.title(tid)
                pos = line.find(tid)
                own = not any(a <= pos < b for a, b in restated)
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
                t["mentions"].append(
                    {"kind": src["kind"], "number": src["number"], "url": src["url"], "date": src["date"]}
                )
                if own and len(ids) <= LINE_TITLE_LIMIT:
                    os_ = classify(OS_RULES, own_line) or src_os
                    gpu = classify(GPU_RULES, own_line) or src_gpu
                    build = self._build(own_line, src)
                    st = stage_in(own_line, pos)
                    quote = clip(re.sub(r"\s+", " ", strip_md(line)).strip(), 280)
                    if st:
                        t["evidence"].append(
                            {
                                "stage": st[0],
                                "os": os_,
                                "gpu": gpu,
                                **build,
                                "url": src["url"],
                                "date": src["date"],
                                "note": f"“{st[1]}”",
                                "quote": quote,
                                "origin": "mined",
                                "verified": False,
                                "author": src.get("author"),
                                "part": src["part"],
                            }
                        )
                    if sig:
                        floor = "Converts" if sig["family"] == "import" else "Starts"
                        t["evidence"].append(
                            {
                                "stage": floor,
                                "os": os_,
                                "gpu": gpu,
                                **build,
                                "url": src["url"],
                                "date": src["date"],
                                "note": "stops at: " + sig["display"],
                                "quote": quote,
                                "origin": "mined",
                                "verified": False,
                                "author": src.get("author"),
                                "part": src["part"],
                            }
                        )
                        t["stops"].append(
                            {
                                "sig": sig,
                                "url": src["url"],
                                "date": src["date"],
                                "issue": src["number"] if src["kind"] == "issue" else None,
                                "os": os_,
                                "gpu": gpu,
                                "build": build["build"],
                            }
                        )
                if info is None:
                    continue
                if info["tracker"]:
                    continue
                # "report": the issue is about this title (ID in the issue title, or a
                # "Title:" / "Game:" field in the body). A bare mention, e.g. a
                # measurement on some title, is kept but does not enter the chain.
                if src["part"] == "body" and (idx == 0 or REPORT_FIELD.match(strip_md(line))):
                    self._associate(tid, src["number"], "report", src["url"], src["date"])
                elif own and len(ids) <= LINE_TITLE_LIMIT and (sig or STOP_WORDS.search(own_line)):
                    self._associate(tid, src["number"], "stop-line", src["url"], src["date"])
                else:
                    self._associate(tid, src["number"], "mention", src["url"], src["date"])
        self._mine_code_blocks(src, info)

    def _mine_code_blocks(self, src: dict, info: dict | None):
        """A fenced log with one title ID: its last error line is where that title stopped,
        even when the ID and the error are on different lines. An ID-less issue comment may
        use its issue title when that title names exactly one title ID."""
        text = src["text"]
        raw_ids = TITLE_RE.findall(text)
        ids = [i for i in dict.fromkeys(raw_ids) if i not in PLACEHOLDER_IDS]
        issue_title_fallback = False
        if info and info["tracker"]:
            return
        if not ids and not raw_ids and info and src["kind"] == "issue" and src["part"] == "comment":
            issue_title = self.issues[src["number"]].get("title") or ""
            title_ids = [i for i in dict.fromkeys(TITLE_RE.findall(issue_title)) if i not in PLACEHOLDER_IDS]
            if len(title_ids) == 1:
                ids = title_ids
                issue_title_fallback = True
        if len(ids) != 1:
            return
        blocks = code_blocks_with_lead(text)
        if not blocks:
            return
        t = self.title(ids[0])
        seen = {s["sig"]["key"] for s in t["stops"] if s["url"] == src["url"]}
        runs = run_text(text)
        os_, gpu = classify(OS_RULES, runs), classify(GPU_RULES, runs)
        for block, lead in blocks:
            # what the logged run was built from: the paragraph that introduces the log, not the whole thread
            build = self._build(lead, src)
            if (
                issue_title_fallback
                and build["build_kind"] == "main"
                and not MAIN_BUILD.search(lead)
                and not MAIN_COMMIT.search(lead)
            ):
                continue
            sig = block_stop(block)
            if not sig or sig["key"] in seen:
                continue
            seen.add(sig["key"])
            self.resolve_sig(sig)
            t["evidence"].append(
                {
                    "stage": "Converts" if sig["family"] == "import" else "Starts",
                    "os": os_,
                    "gpu": gpu,
                    **build,
                    "url": src["url"],
                    "date": src["date"],
                    "note": "stops at: " + sig["display"] + " (log block)",
                    "quote": clip(sig["display"], 280),
                    "origin": "mined",
                    "verified": False,
                    "author": src.get("author"),
                    "part": src["part"],
                }
            )
            t["stops"].append(
                {
                    "sig": sig,
                    "url": src["url"],
                    "date": src["date"],
                    "issue": src["number"] if src["kind"] == "issue" else None,
                    "os": os_,
                    "gpu": gpu,
                    "via": "log block",
                    "build": build["build"],
                }
            )

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
                    full = next(
                        (s for s in sigs[1:] if sig_match(s["key"], sigs[0]["key"]) or sigs[0]["key"] in s["key"]), None
                    )
                    primary = full or sigs[0]
            later = [self.resolve_sig(s) for t in texts[2:] for _, s in signatures_in(t)]
            registers = Counter()
            for t in texts:
                for r in sorted(set(REGISTER_RE.findall(t))):
                    registers[r] += 1
            self.issue_info[number] = {
                "titles": sorted(all_ids),
                "tracker": len(all_ids) >= TRACKER_TITLES,
                "signature": primary,
                "signatures": list({s["key"]: s for s in sigs + later}.values())[:12],
                "text": "\n".join(texts),
                "registers": registers,
            }
            for src in self._sources(issue, "issue"):
                self._mine_text(src, self.issue_info[number])

    def _mine_prs(self):
        for p in self.raw["prs"]:
            for src in self._sources(p, "pr"):
                self._mine_text(src, None)

    def _build(self, text: str, src: dict) -> dict:
        """What a report ran on; a working group's thread is always a patched stack (mine.fork_build)."""
        if src["kind"] == "fork":
            return fork_build(text, src.get("recipe") or [], self.repo)
        return build_detail(text, src["kind"], src["number"])

    def _mine_working_groups(self):
        """Working-group threads (config.WORKING_GROUPS) follow one title on a patched stack, so every report in
        them is off main. Lines that name a title ID are read as everywhere else. In a thread whose title names
        exactly one title ID, a line that names the title by name or by its initials ("Sword of the Sea", "SotS")
        in a comment about no other title counts for it, outside quotes and fenced logs. The upstream PRs the
        thread's opening post names are its recipe."""
        for g in self.raw.get("working_groups", []):
            ids = [i for i in dict.fromkeys(TITLE_RE.findall(g["title"])) if i not in PLACEHOLDER_IDS]
            subject = ids[0] if len(ids) == 1 else None
            recipe = upstream_refs(g.get("body") or "", self.repo)
            name = name_before(g["title"], g["title"].find(subject)) if subject else None
            words = re.findall(r"[\w']+", name or "")
            spoken = [re.escape(name)] if name else []
            if len(words) >= 3:
                spoken.append(re.escape("".join(w[0] for w in words)))  # "SotS"
            said = re.compile(r"(?<![\w])(?:" + "|".join(spoken) + r")(?![\w])", re.I) if spoken else None
            for src in self._sources(g, "fork"):
                src["recipe"] = recipe
                self._mine_text(src, None)
                if subject and said:
                    self._mine_subject(src, subject, said)

    def _mine_subject(self, src: dict, tid: str, said: re.Pattern):
        text = src["text"]
        if any(i != tid for i in TITLE_RE.findall(text)):
            return  # the comment is about other titles too
        t = self.title(tid)
        t["mentions"].append({"kind": src["kind"], "number": src["number"], "url": src["url"], "date": src["date"]})
        runs = run_text(text)
        os_, gpu = classify(OS_RULES, runs), classify(GPU_RULES, runs)
        fenced = False
        for line in text.splitlines():
            if re.match(r"\s*(`{3,}|~{3,})", line):
                fenced = not fenced
                continue
            if fenced or is_quote(line) or TITLE_RE.search(line):
                continue
            named = said.search(line)
            st = stage_in(line, named.start()) if named else None
            if not st:
                continue
            t["evidence"].append(
                {
                    "stage": st[0],
                    "os": classify(OS_RULES, line) or os_,
                    "gpu": classify(GPU_RULES, line) or gpu,
                    **self._build(line, src),
                    "url": src["url"],
                    "date": src["date"],
                    "note": f"“{st[1]}”",
                    "quote": clip(re.sub(r"\s+", " ", strip_md(line)).strip(), 280),
                    "origin": "mined",
                    "verified": False,
                    "author": src.get("author"),
                    "part": src["part"],
                }
            )

    def _mine_bring_up_form(self, src: dict, date: str):
        """A Game bring-up form puts the stage under "Furthest point", lines away from the title ID, so
        the line-based mining misses it. The first post is edited as the title progresses: `date` is its last edit."""
        form = bring_up_form(src["text"])
        if not form or not form["stage"]:
            return
        ids = [i for i in dict.fromkeys(TITLE_RE.findall(form["title"])) if i not in PLACEHOLDER_IDS]
        if len(ids) != 1:
            return
        t = self.title(ids[0])
        if any(e["url"] == src["url"] and e["stage"] == form["stage"] for e in t["evidence"]):
            return
        runs = run_text(src["text"])
        t["evidence"].append(
            {
                "stage": form["stage"],
                "os": classify(OS_RULES, form["system"]) or classify(OS_RULES, runs),
                "gpu": classify(GPU_RULES, form["system"]) or classify(GPU_RULES, runs),
                **self._build(form["commit"], src),
                "url": src["url"],
                "date": date,
                "note": f"“{form['point']}”",
                "quote": clip(
                    " ".join(strip_md(f"Furthest point: {form['point']}. AnyPS5 commit: {form['commit']}").split()), 280
                ),
                "origin": "mined",
                "verified": False,
                "author": src.get("author"),
                "part": src["part"],
            }
        )

    def _mine_discussions(self):
        """Discussions (a "Game bring-up" thread per title, say) are read for titles, stages and stops like
        PR text, but never become blockers."""
        for d in self.raw.get("discussions", []):
            for src in self._sources(d, "discussion"):
                self._mine_text(src, None)
                if src["part"] == "body":
                    self._mine_bring_up_form(src, d.get("editedAt") or src["date"])

    def _apply_curated_titles(self):
        for ct in self.curated.get("titles", []):
            t = self.title(ct["id"])
            t["curated"] = True
            t["curated_name"] = ct.get("name")
            for k in ("engine", "kind", "paths"):
                if ct.get(k):
                    t[k] = ct[k]
            for ev in ct.get("evidence", []):
                t["evidence"].append(
                    {
                        **{"os": None, "gpu": None, "build": "main", "note": "", "quote": None},
                        **ev,
                        "origin": "curated",
                        "verified": True,
                    }
                )
        self._apply_stage_reviews()
        self._apply_title_tags()
        for t in self.titles.values():
            for e in t["evidence"]:
                # only upstream PRs can be merged; an issue number or an unknown one is no PR to wait for
                if e.get("prs"):
                    e["prs"] = [n for n in e["prs"] if key_of(self.repo, n) in self.prs]
            t["evidence"] = evaluate.dedupe(t["evidence"])
            if not t["engine"] and t["engines"]:
                t["engine"] = t["engines"].most_common(1)[0][0]
            if not t["kind"] and t["kinds"]:
                t["kind"] = t["kinds"].most_common(1)[0][0]

    def _resolve_games(self):
        """Which title IDs are one game (identity.py), and each title's own name: curated, else the
        PlayStation title list's, else the most common mined one."""
        self.identity: Identity = resolve(
            {tid: TitleNames(t.get("curated_name"), t["names"]) for tid, t in self.titles.items()},
            self.games_curated,
            self.catalog,
        )
        for tid, t in self.titles.items():
            own = self.identity.titles.get(tid, {})
            t["name"], t["name_origin"] = own.get("name"), own.get("origin")
            t["concept"], t["region"] = own.get("concept"), own.get("region")
            t["content_id"] = own.get("content_id") or next(iter(t["content_ids"]), None)
            if not t["region"] and t["content_ids"]:
                t["region"] = next(iter(t["content_ids"].values()))
            if own.get("concept") and not any(
                ct["id"] == tid and ct.get("kind") for ct in self.curated.get("titles", [])
            ):
                t["kind"] = "retail"  # sold on the PlayStation Store
            t["game"] = self.identity.of.get(tid)
        self.gaps += [
            f"{tid} is a placeholder title ID and names no title; reports that use it are skipped."
            for tid in sorted(self.placeholders)
        ]

    def _apply_title_tags(self):
        """What kind of game a title is (data/blockers.json title_tags), keyed by title ID. Tags describe a title
        the map already lists; they never add one, and a title that leaves the window keeps its entry for later."""
        for entry in self.curated.get("title_tags", []):
            t = self.titles.get(entry["title"])
            if t is not None:
                t["tags"] = [tag for tag in TAGS if tag in entry["tags"]]
                t["tag_sources"] = list(entry["sources"])

    # -- blockers -----------------------------------------------------------
    def _issue_prs(self, number: int) -> list[dict]:
        out = []
        for key, kind in self.links.get(number, {}).items():
            pr = self.prs[key]
            out.append(
                {
                    "key": key,
                    "ref": short_ref(key, self.repo),
                    "url": pr["url"],
                    "title": pr["title"],
                    "state": pr["state"],
                    "link": kind,
                    "updated": pr["updated"],
                    "origin": "mined",
                    "via": sorted(self.link_via[number][key]),
                }
            )
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
        for rx, area in [
            (r"^(Recompiler|Structurizer|Shader|SPIR-V|v_|s_)", "shader"),
            (r"^(AGC|Layered|Vulkan|NVIDIA|Intel)", "agc"),
            (r"^Relinker", "relinker"),
            (r"^(libkernel|Kernel)", "libkernel"),
            (r"^(libc|LibcInternal)", "libc"),
        ]:
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
                if lib.startswith("libkernel") or (
                    not lib
                    and re.match(
                        r"(pthread_|sig|_umtx|sysctl|sched_|sceKernel|cpuset|_?fstat|kqueue|kevent|mmap|munmap)", sym
                    )
                ):
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
                pr = self.prs.get(key) or self._put_pr(
                    ref.get("repo", self.repo), int(ref["number"]), None, None, None, None, None, None
                )
                prs.append(
                    {
                        "key": key,
                        "ref": short_ref(key, self.repo),
                        "url": pr["url"],
                        "title": pr["title"],
                        "state": pr["state"],
                        "link": "fixes" if ref in cb.get("fix_prs", []) else "related",
                        "updated": pr["updated"],
                        "note": ref.get("note"),
                        "origin": "curated",
                    }
                )
            mined = self._issue_prs(cb["issue"]) if issue else []
            seen = {p["key"] for p in prs}
            prs += [p for p in mined if p["key"] not in seen]
            prs = self._with_stand_ins(prs)
            info = self.issue_info.get(cb.get("issue"), {})
            sig = info.get("signature")
            status = cb.get("status")
            if not status:
                if issue:
                    status = "open" if issue["state"] == "OPEN" else "resolved"
                else:
                    status = (
                        "resolved"
                        if any(p["state"] == "merged" and p["link"] == "fixes" and not p.get("note") for p in prs)
                        else "open"
                    )
            self.blockers[bid] = {
                "id": bid,
                "issue": cb.get("issue"),
                "url": issue["url"] if issue else (prs[0]["url"] if prs else (cb.get("sources") or [None])[0]),
                "title": cb.get("title") or (issue["title"] if issue else bid),
                "signature": cb.get("signature") or (sig["display"] if sig else None),
                "signature_key": signature_key(cb.get("signature")) or (sig["key"] if sig else None),
                "area": cb.get("area") or self._area(issue, prs, sig),
                "status": status,
                "prs": prs,
                "next": cb.get("next"),
                "help_wanted": cb.get("help_wanted"),
                "notes": cb.get("notes"),
                "owner": cb.get("owner") or (", ".join(issue.get("assignees", [])) if issue else None) or None,
                "origin": "curated",
                "tracker": False,
                "created": issue["createdAt"] if issue else None,
                "last_activity": max(
                    [d for d in [issue["updatedAt"] if issue else None] + [p["updated"] for p in prs] if d] or [None],
                    key=lambda d: d or "",
                ),
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
            has_titles = any(
                number in t["assoc"] and t["assoc"][number]["level"] != "mention" for t in self.titles.values()
            )
            if not (info["signature"] or has_titles):
                continue
            prs = self._with_stand_ins(self._issue_prs(number))
            sig = info["signature"]
            self.blockers[str(number)] = {
                "id": str(number),
                "issue": number,
                "url": issue["url"],
                "title": issue["title"],
                "signature": sig["display"] if sig else None,
                "signature_key": sig["key"] if sig else None,
                "area": self._area(issue, prs, sig),
                "status": "open" if issue["state"] == "OPEN" else "resolved",
                "prs": prs,
                "next": None,
                "help_wanted": None,
                "notes": None,
                "owner": ", ".join(issue.get("assignees", [])) or None,
                "origin": "mined",
                "tracker": info["tracker"],
                "created": issue["createdAt"],
                "last_activity": max([issue["updatedAt"]] + [p["updated"] for p in prs if p["updated"]]),
                "labels": issue["labels"],
            }
        self.issue_to_blocker = {b["issue"]: bid for bid, b in self.blockers.items() if b["issue"]}

    # -- chains -------------------------------------------------------------
    def _build_chains(self):
        deps = self.raw.get("dependencies", {})
        sig_index = [
            (b["signature_key"], bid)
            for bid, b in self.blockers.items()
            if b["signature_key"] and b["status"] == "open" and not b["tracker"]
        ]
        curated_chains = {ct["id"]: ct.get("blockers", []) for ct in self.curated.get("titles", [])}
        excluded = {ct["id"]: {str(x["id"]) for x in ct.get("excluded", [])} for ct in self.curated.get("titles", [])}
        for tid, t in self.titles.items():
            skip = excluded.get(tid, set())
            steps: list[dict] = []
            seen: set[str] = set()

            def add(bid, origin, why, scope=None, at=None, steps=steps, seen=seen, skip=skip):
                if bid in seen or bid in skip or bid not in self.blockers:
                    return
                seen.add(bid)
                step = {"blocker": bid, "origin": origin, "why": why, "scope": scope}
                if at is None:
                    steps.append(step)
                else:
                    steps.insert(at, step)

            for step in curated_chains.get(tid, []):
                add(str(step["id"]), "curated", step.get("why", "curated"), step.get("scope"))
            # the latest stop recorded on main decides which mined blocker comes first; a stop on a
            # PR branch or a patched build can sit behind blockers that main still hits
            on_main = [s for s in t["stops"] if s.get("build", "main") == "main"]
            latest = sorted(on_main, key=lambda s: s["date"] or "", reverse=True)
            # the newest stop that names a known open blocker or a tracker row; newer stops
            # that match nothing (an unknown crash site, a quoted placeholder) are passed over
            for stop in latest:
                hit = next(
                    (
                        bid
                        for key, bid in sig_index
                        if bid not in skip and (sig_match(key, stop["sig"]["key"]) or key == stop["sig"]["key"])
                    ),
                    None,
                )
                if hit:
                    add(hit, "mined", "latest recorded stop matches its signature")
                    if self.blockers[hit]["issue"]:
                        t["assoc"].setdefault(
                            self.blockers[hit]["issue"],
                            {"level": "signature", "url": stop["url"], "date": stop["date"]},
                        )
                    break
                if stop["issue"] and self.issue_info.get(stop["issue"], {}).get("tracker"):
                    vid = self._virtual_blocker(stop["issue"], stop)
                    sig_index.append((self.blockers[vid]["signature_key"], vid))
                    add(vid, "mined", f"latest recorded stop, listed in tracker #{stop['issue']}")
                    break
            strong = sorted(
                ((n, a) for n, a in t["assoc"].items() if a["level"] != "mention"),
                key=lambda na: self.issues.get(na[0], {}).get("createdAt", ""),
            )
            for number, a in strong:
                bid = self.issue_to_blocker.get(number)
                if not bid:
                    continue
                # GitHub-native dependencies: what blocks this issue comes first
                for dep in deps.get(str(number), []):
                    dbid = self.issue_to_blocker.get(dep["number"]) if dep.get("repo", self.repo) == self.repo else None
                    if dbid:
                        add(dbid, "github", f"#{number} is blocked by #{dep['number']} (GitHub dependency)")
                add(
                    bid,
                    "mined",
                    {
                        "report": "reported on this issue",
                        "stop-line": "a comment names it at this stop",
                        "signature": "stop signature matches",
                        "tracker-row": "tracker row",
                    }.get(a["level"], a["level"]),
                )
            t["chain"] = steps

    def _virtual_blocker(self, number: int, stop: dict) -> str:
        """A crash site that only lives as a row in a tracker issue becomes its own
        blocker, keyed by signature, so one tracker does not swallow every title."""
        sig = stop["sig"]
        slug = (
            sig.get("symbol") or sig.get("nid") or sig.get("library") or re.sub(r"\W+", "-", sig["key"])[:40].strip("-")
        )
        bid = f"{number}~{slug}"
        if bid in self.blockers:
            return bid
        prs = []
        symbol = sig.get("symbol")
        if symbol and len(symbol) >= 4:
            rx = re.compile(r"(?<![\w])" + re.escape(symbol) + r"(?![\w])")
            for pr in self.prs.values():
                if pr["repo"] == self.repo and pr["title"] and rx.search(pr["title"]):
                    prs.append(
                        {
                            "key": pr["key"],
                            "ref": short_ref(pr["key"], self.repo),
                            "url": pr["url"],
                            "title": pr["title"],
                            "state": pr["state"],
                            "link": "related",
                            "updated": pr["updated"],
                            "origin": "mined",
                        }
                    )
        rank = {"open": 0, "draft": 1, "merged": 2, "closed": 3}
        prs.sort(key=lambda p: (rank.get(p["state"], 4), -(int(p["key"].split("#")[1]))))
        merged_after = any(
            p["state"] == "merged" and (self.prs[p["key"]].get("merged_at") or "") > (stop["date"] or "") for p in prs
        )
        parent = self.issues[number]
        self.blockers[bid] = {
            "id": bid,
            "issue": None,
            "parent": number,
            "url": stop["url"],
            "title": stop_title(sig),
            "signature": sig["display"],
            "signature_key": sig["key"],
            "area": self._area(None, prs, sig),
            "status": "resolved" if merged_after or parent["state"] != "OPEN" else "open",
            "prs": prs[:6],
            "next": None,
            "help_wanted": None,
            "notes": f"Tracked as a row in #{number}: {parent['title']}",
            "owner": None,
            "origin": "mined",
            "tracker": False,
            "created": stop["date"],
            "last_activity": max([stop["date"] or ""] + [p["updated"] or "" for p in prs]) or None,
            "labels": [],
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
        curated stage with its own source and quote. A claim_url with a comment or review
        anchor drops that comment only; without one, the whole issue or PR thread."""
        for rv in self.curated.get("stage_reviews", []):
            t = self.title(rv["title"])
            claim = rv["claim_url"].rstrip("/")

            def reviewed(url: str | None, claim=claim) -> bool:
                url = (url or "").rstrip("/")
                return url == claim if "#" in claim else url.split("#")[0].rstrip("/") == claim

            t["evidence"] = [e for e in t["evidence"] if not (e["origin"] == "mined" and reviewed(e["url"]))]
            t.setdefault("reviews", []).append(
                {k: rv.get(k) for k in ("claim", "claim_url", "verdict", "stage", "url", "quote", "reason")}
            )
            if rv["verdict"] in ("confirmed", "downgraded"):
                t["evidence"].append(
                    {
                        "stage": rv["stage"],
                        "os": rv.get("os"),
                        "gpu": rv.get("gpu"),
                        "build": rv.get("build") or "main",
                        "url": rv["url"],
                        "date": rv.get("date"),
                        "note": rv["quote"],
                        "quote": rv["quote"],
                        "origin": "curated",
                        "verified": True,
                        "review": rv["verdict"],
                    }
                )

    def merged(self, number: int) -> bool:
        """Whether upstream PR `number` is merged now (unknown PRs, outside the window, are not)."""
        return self.prs.get(key_of(self.repo, number), {}).get("state") == "merged"

    def best_stage(self, t: dict) -> dict | None:
        """The best qualifying stage of a title or a game (see evaluate.py)."""
        return evaluate.best_stage(t["evidence"], self.merged)

    def unverified_claim(self, t: dict) -> dict | None:
        return evaluate.unverified_claim(t["evidence"], self.best_stage(t), self.merged)

    def branch_stage(self, t: dict) -> dict | None:
        best = self.best_stage(t)
        return evaluate.branch_stage(
            t["evidence"], self.merged, best, evaluate.unverified_claim(t["evidence"], best, self.merged)
        )

    def confidence(self, t: dict) -> dict:
        return evaluate.confidence(t["evidence"], self.merged)

    def members(self, gid: str) -> list[dict]:
        """The titles of a game, the one that leads first: the furthest, then one with a known stop, then the one
        with the most reports, then the lowest ID. Its chain decides where the game stops first."""
        game = self.identity.games[gid]
        titles = [self.titles[t] for t in game.title_ids if t in self.titles]

        def lead(t):
            best = self.best_stage(t)
            return (
                evaluate.rank(best["stage"] if best else None),
                bool(t["chain"]),
                len(t["evidence"]),
                [-ord(c) for c in t["id"]],
            )

        return sorted(titles, key=lead, reverse=True)

    def game_chain(self, gid: str) -> list[dict]:
        """A game's chain: the leading title's steps, then the steps only its other title IDs know, each step
        with the title it comes from."""
        chain, seen = [], set()
        for t in self.members(gid):
            for step in t["chain"]:
                if step["blocker"] not in seen:
                    seen.add(step["blocker"])
                    chain.append({**step, "title": t["id"]})
        return chain

    def game_paths(self, gid: str) -> dict[str, list[dict]]:
        """A game's chain per OS/GPU path (the paths of all of its title IDs)."""
        names = list(dict.fromkeys(p for t in self.members(gid) for p in (t.get("paths") or [])))
        return self.paths({"paths": names or None, "chain": self.game_chain(gid)})

    def _rank(self):
        """Per blocker: the games that list it (any title ID of the game), that it stops first on a path of the
        game's chain, and for which it is the only open stop on such a path. A game at Playable counts only
        toward the total. The title IDs behind the counts are kept in `titles`, `frontier_titles` and
        `one_fix_titles`."""
        for b in self.blockers.values():
            b.update(
                {
                    "frontier": 0,
                    "one_fix_away": 0,
                    "total": 0,
                    "titles": [],
                    "frontier_titles": [],
                    "one_fix_titles": [],
                    "games": [],
                    "frontier_games": [],
                    "one_fix_games": [],
                }
            )
        is_open = {bid for bid, b in self.blockers.items() if b["status"] == "open"}
        for t in self.titles.values():
            t["open_chain"] = [step for step in t["chain"] if step["blocker"] in is_open]
        for gid in self.identity.games:
            members = self.members(gid)
            for t in members:
                for step in t["open_chain"]:
                    b = self.blockers[step["blocker"]]
                    if t["id"] not in b["titles"]:
                        b["titles"].append(t["id"])
                    if gid not in b["games"]:
                        b["games"].append(gid)
            evidence = [e for t in members for e in t["evidence"]]
            best = evaluate.best_stage(evidence, self.merged)
            if best and best["stage"] == "Playable":
                continue
            front, single = set(), set()
            for chain in self.game_paths(gid).values():
                open_steps = [step for step in chain if step["blocker"] in is_open]
                if open_steps:
                    front.add((open_steps[0]["blocker"], open_steps[0]["title"]))
                    if len({step["blocker"] for step in open_steps}) == 1:
                        single.add((open_steps[0]["blocker"], open_steps[0]["title"]))
            for key, bids in (("frontier", front), ("one_fix", single)):
                for bid, tid in bids:
                    b = self.blockers[bid]
                    if tid not in b[f"{key}_titles"]:
                        b[f"{key}_titles"].append(tid)
                    if gid not in b[f"{key}_games"]:
                        b[f"{key}_games"].append(gid)
        for b in self.blockers.values():
            b["total"], b["frontier"], b["one_fix_away"] = (
                len(b["games"]),
                len(b["frontier_games"]),
                len(b["one_fix_games"]),
            )
            b["score"] = 3 * b["one_fix_away"] + 2 * b["frontier"] + b["total"]

    def ranking(self) -> list[dict]:
        open_ = [b for b in self.blockers.values() if b["status"] == "open"]
        return sorted(open_, key=lambda b: (-b["score"], -b["total"], b["origin"] != "curated", -(b["issue"] or 0)))
