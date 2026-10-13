"""Fixture tests for the extraction and ranking logic. No network, no gh."""

import datetime as dt
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import roadmap as r  # noqa: E402
from anyps5_roadmap import mine  # noqa: E402

FIX = HERE / "fixtures"
NOW = dt.datetime(2026, 10, 10, 12, 0, tzinfo=dt.UTC)


class Extraction(unittest.TestCase):
    def test_nid_matches_upstream_algorithm(self):
        self.assertEqual(r.compute_nid("pthread_sigmask"), "JZKw5+Wrnaw")
        self.assertEqual(r.compute_nid("siglongjmp"), "pebqbE5ws8s")

    def test_windows_and_linux_import_lines_share_a_key(self):
        win = r.signature_from("FAIL: unresolved ELF import JZKw5+Wrnaw from libkernel.prx` (`pthread_sigmask`) |")
        lin = r.signature_from("stops at `undefined symbol: JZKw5+Wrnaw`")
        self.assertEqual(win["key"], lin["key"])
        self.assertEqual(win["symbol"], "pthread_sigmask")
        self.assertEqual(win["library"], "libkernel")

    def test_an_import_prefix_without_its_nid_is_no_signature(self):
        quoted = "If someone with the title can post the `FAIL: unresolved ELF import ...` line from main, I'll add it."
        self.assertIsNone(r.signature_from(quoted))
        self.assertIsNone(r.signature_from("stops at: FAIL: unresolved ELF import"))
        self.assertEqual(
            r.signature_from("FAIL: unresolved ELF import VANhIWcqYak")["display"].split()[-1], "VANhIWcqYak"
        )

    def test_wrappers_and_addresses_are_normalised(self):
        a = r.signature_from(
            "presentation failed: compute shader 0x2006410000: AGC graphics: storage image access to "
            "depth/stencil surface 0x20183b0000 is not implemented"
        )
        b = r.signature_from(
            "  what():  AGC graphics: storage image access to depth/stencil surface 0x53a500000 is not implemented"
        )
        self.assertEqual(a["key"], b["key"])
        self.assertEqual(
            a["display"], "AGC graphics: storage image access to depth/stencil surface 0x… is not implemented"
        )

    def test_signature_keeps_balanced_parentheses_and_cuts_markdown(self):
        s = r.signature_from(
            "`ShaderRecompiler::Recompile: shader info collection failed: packed pixel ancillary input has an "
            "unsupported live use (used by SelectU32 ? ?)`. #1904 made all four compile"
        )
        self.assertTrue(s["key"].endswith("(used by selectu32 ? ?)"), s["key"])
        self.assertEqual(s["family"], "recompile")

    def test_title_names(self):
        line = "**Title:** Disney Epic Mickey: Rebrushed (PPSA15657 v01.000.000, retail, UE4)."
        self.assertEqual(r.name_before(line, line.find("PPSA")), "Disney Epic Mickey: Rebrushed")
        line = "Another title: Taxi Chaos 2 (PPSA30279 v01.007.000, Unreal Engine) stops here"
        self.assertEqual(r.name_before(line, line.find("PPSA")), "Taxi Chaos 2")
        line = "- **PPSA02929 (Dreaming Sarah, Construct)**: on main it segfaults"
        self.assertEqual(r.name_after(line, line.find("PPSA") + 9), "Dreaming Sarah")
        line = "On Windows with an RTX 5090 Laptop GPU (PPSA01317) it boots"
        self.assertIsNone(r.name_before(line, line.find("PPSA")))

    def test_stage_keywords_respect_negation_and_stops(self):
        self.assertEqual(r.stage_in("Hollow Knight (PPSA12544) reaches gameplay in tut_01", 15)[0], "Ingame")
        self.assertIsNone(r.stage_in("it never reaches the main menu", 0))
        self.assertIsNone(r.stage_in("No title calls these during the runs I have, so nothing was tested in-game.", 0))
        # a loading step is not the stage it loads
        self.assertEqual(
            r.stage_in("renders the main menu and Settings, and loads story mode until the first shader", 0)[0], "Menus"
        )
        self.assertEqual(r.stage_in("PPSA05684 crashed right after loading its first level.", 0)[0], "Menus")

    def test_os_names_map_distros_and_macs(self):
        linux = [
            "SteamOS",
            "Steam Deck",
            "Bazzite",
            "NixOS",
            "Debian",
            "openSUSE",
            "Pop!_OS",
            "Linux Mint",
            "Gentoo",
            "Manjaro",
        ]
        for name in linux:
            with self.subTest(name=name):
                self.assertEqual(r.classify(r.OS_RULES, f"tested on {name}"), "Linux")
        macos = ["Apple M1", "Apple M2", "Apple M3", "Apple M4", "MacBook", "Mac mini", "Sonoma", "Sequoia"]
        for name in macos:
            with self.subTest(name=name):
                self.assertEqual(r.classify(r.OS_RULES, f"tested on {name}"), "macOS")
        self.assertEqual(r.classify(r.OS_RULES, "tested on Windows 11"), "Windows")
        self.assertEqual(r.classify(r.OS_RULES, "tested on Ubuntu 24.04"), "Linux")
        for bare in ["deck", "mint", "arch"]:
            with self.subTest(bare=bare):
                self.assertIsNone(r.classify(r.OS_RULES, f"my {bare} runs it"))

    def test_engine_names(self):
        cases = {
            "RE Engine": "RE Engine",
            "Frostbite": "Frostbite",
            "id Tech": "id Tech",
            "id Tech 7": "id Tech",
            "CryEngine": "CryEngine",
            "Cocos2d": "Cocos2d",
            "MonoGame": "MonoGame",
            "FNA": "FNA",
            "Ren'Py": "Ren'Py",
            "RPG Maker": "RPG Maker",
            "Defold": "Defold",
            "Clickteam Fusion": "Clickteam Fusion",
            "Source 2": "Source 2",
            "UE 5.3": "Unreal Engine 5",
            "Unreal Engine 5.4": "Unreal Engine 5",
        }
        for engine, expected in cases.items():
            with self.subTest(engine=engine):
                line = f"Some Game (PPSA01234, {engine})"
                self.assertEqual(r.classify(r.ENGINE_RULES, line), expected)
        self.assertEqual(r.classify(r.ENGINE_RULES, "Some Game (PPSA01234, UE5)"), "Unreal Engine 5")
        line = "Some Game (PPSA01234, Unity 2022.3 IL2CPP)"
        self.assertEqual(r.classify(r.ENGINE_RULES, line), "Unity")

    def test_stage_report_phrasings(self):
        self.assertEqual(r.stage_in("PPSA01234 boots to black", 0)[0], "Presents")
        self.assertEqual(r.stage_in("PPSA01234 reaches the intro", 0)[0], "Presents")
        self.assertEqual(r.stage_in("PPSA01234 plays the opening cutscene", 0)[0], "Presents")
        self.assertEqual(r.stage_in("PPSA01234 reaches the save select screen", 0)[0], "Menus")
        self.assertEqual(r.stage_in("PPSA01234 gets to the character creator", 0)[0], "Menus")
        self.assertEqual(r.stage_in("PPSA01234 makes it to the hub world", 0)[0], "Ingame")
        self.assertIsNone(r.stage_in("PPSA01234 never boots to black", 0))

    def test_leading_verbs_are_not_part_of_a_name(self):
        line = "Adds LEGO Party! (PPSA29141, Unity 2022.3 IL2CPP, FMOD) to the tested compatibility list"
        self.assertEqual(r.name_before(line, line.find("PPSA")), "LEGO Party!")
        line = "- Seen in PPSA22520 (Animal Well): the title music is a stereo sampler"
        self.assertIsNone(r.name_before(line, line.find("PPSA")))
        self.assertEqual(r.name_after(line, line.find("PPSA") + 9), "Animal Well")
        # a stop phrase before the keyword means the title did not get past it
        self.assertEqual(r.stage_in("PPSA05684 stops in its first level with an error", 0)[0], "Menus")

    def test_a_word_that_only_sits_next_to_the_id_is_not_a_name(self):
        def before(line):
            return r.name_before(line, line.find("PPSA"))

        # sentence openers and verbs
        self.assertIsNone(before("Does PPSA01317 stop earlier than the description says?"))
        self.assertIsNone(before("Not PPSA18605: that one stops at the intro"))
        self.assertIsNone(before("Retried PPSA20612 on another machine."))
        self.assertIsNone(before("It stops. Retried PPSA20612 on another machine."))
        # a one-word title at the start of a line still counts
        self.assertEqual(before("Returnal PPSA01285 crashes in the first room"), "Returnal")
        self.assertEqual(before("Stray (PPSA02100, UE4)"), "Stray")
        # a possessive owns something
        self.assertIsNone(before("Cyberpunk's PPSA03974 build ships its own libc.prx"))
        self.assertEqual(before("Demon's Souls (PPSA01341)"), "Demon's Souls")
        # a list: the words before the connector name other games
        self.assertIsNone(before("These come from Astro Bot, Epic Mickey and PPSA15186 (#1817, #2207)"))
        self.assertEqual(before("Taxi Chaos 2 - PPSA30279"), "Taxi Chaos 2")

    def test_a_report_header_before_a_label_colon_is_not_part_of_the_name(self):
        line = "# Claude Code Report : Commandos: Origins (PPSA14708) on Linux"
        self.assertEqual(r.name_before(line, line.find("PPSA")), "Commandos: Origins")
        line = "Kena: Bridge of Spirits (PPSA01746)"
        self.assertEqual(r.name_before(line, line.find("PPSA")), "Kena: Bridge of Spirits")

    def test_or_joins_the_words_of_a_name_but_on_does_not(self):
        line = "Ready or Not (PPSA18605) stops at startup"
        self.assertEqual(r.name_before(line, line.find("PPSA")), "Ready or Not")
        # "on" stays a label: "Impact on Demon's Souls (PPSA01341)" names Demon's Souls only
        line = "Impact on Demon's Souls (PPSA01341)"
        self.assertEqual(r.name_before(line, line.find("PPSA")), "Demon's Souls")
        line = "Tested on Stray (PPSA02100)"
        self.assertEqual(r.name_before(line, line.find("PPSA")), "Stray")

    def test_an_engine_in_the_parenthesis_is_not_a_name(self):
        line = "PPSA18391 (Clickteam Fusion) queries trophies with a null `details`"
        self.assertIsNone(r.name_after(line, line.find("PPSA") + 9))
        line = "PPSA02929 (Dreaming Sarah, Construct) segfaults"
        self.assertEqual(r.name_after(line, line.find("PPSA") + 9), "Dreaming Sarah")

    def test_closing_references(self):
        refs = r.closing_refs("Fixes #12 and #34. Closes owner/repo#5. Mentions #99.", "example/AnyPS5")
        self.assertEqual(refs, [("example/AnyPS5", 12), ("example/AnyPS5", 34), ("owner/repo", 5)])

    def test_resubmission_references(self):
        text = (
            "This is #1872 again, which was closed. Resubmission of #2174. It resubmits PR #1745. "
            "Reopened as a new PR of #2106. Replaces #2481. Supersedes #1855."
        )
        self.assertEqual(mine.resubmitted_refs(text), [1872, 2174, 1745, 2106, 2481, 1855])
        for other in ("Superseded by #2099", "Follow-up to #419", "tested #1480 again", "Fixes #12"):
            with self.subTest(other=other):
                self.assertEqual(mine.resubmitted_refs(other), [])

    def test_carry_references(self):
        text = (
            "Carries #2738 by @pushkarreddyy, which the intake check closed. Carried from #2909 by @queeeef. "
            "A carry of PR #2684. CARRIES [AlxcBTW/AnyPS5#26](https://github.com/AlxcBTW/AnyPS5/pull/26)."
        )
        self.assertEqual(
            mine.carried_refs(text, "example/AnyPS5"),
            [("example/AnyPS5", 2738), ("example/AnyPS5", 2909), ("example/AnyPS5", 2684), ("AlxcBTW/AnyPS5", 26)],
        )
        for other in (
            "carries the fix for #2701",
            "Carrying @AlxcBTW's fix for #2540 while PR intake is paused",
            "Carry the disclosed fix for #2682 from [AlxcBTW/AnyPS5#18](https://github.com/AlxcBTW/AnyPS5/pull/18)",
            "The test branch also carried #1733",
        ):
            with self.subTest(other=other):
                self.assertEqual(mine.carried_refs(other, "example/AnyPS5"), [])

    def test_pm4_unsupported_reason_parser(self):
        src = """
std::string_view UnsupportedReason(std::uint32_t header) {
    const auto opcode = (header >> 8u) & 0xffu;
    if (opcode == 0x10) {
        switch ((header >> 2u) & 0x3fu) {
            case 0: case 0x06: return {};
            case 0x14: return "guest cache actions are not implemented";
            default: return "custom packet has no implemented contract";
        }
    }
    switch (opcode) {
        case 0x11: case 0x12: return {};
        case 0x24:
            if (IndirectDrawsDisabled()) return "graphics draw is not implemented";
            return {};
        case 0x8e: return "GPU LOD statistics are not implemented";
        default: return "opcode is not known in the reference";
    }
}"""
        out = r.parse_unsupported_reason(src)
        self.assertEqual(out[0x11][0], "handled")
        self.assertEqual(out[0x10][0], "handled")
        self.assertEqual(out[0x24][0], "conditional")
        self.assertIn("IndirectDrawsDisabled()", out[0x24][1])
        self.assertEqual(out[0x8E], ("rejected", "GPU LOD statistics are not implemented"))
        self.assertEqual(out[("custom", 0x14)][0], "rejected")


class Ranking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = json.loads((FIX / "raw.json").read_text(encoding="utf-8"))
        curated = r.load_curated(FIX / "curated.json")
        cls.model = r.Model(raw, curated, "example/AnyPS5", NOW)
        cls.b = cls.model.blockers
        cls.t = cls.model.titles

    def test_titles_are_associated_with_the_issues_they_are_reported_on(self):
        kena = self.t["PPSA01746"]
        self.assertEqual(kena["name"], "Kena: Bridge of Spirits")
        self.assertEqual(kena["engine"], "Unreal Engine 4")
        self.assertEqual(kena["kind"], "retail")
        self.assertEqual([s["blocker"] for s in kena["chain"]], ["10", "11"])
        # a measurement comment naming three titles is a mention, not a blocker link
        self.assertNotIn("10", [s["blocker"] for s in self.t["PPSA02929"]["chain"]])

    def test_a_curated_title_can_exclude_a_mined_blocker(self):
        raw = json.loads((FIX / "raw.json").read_text(encoding="utf-8"))
        curated = r.load_curated(FIX / "curated.json")
        curated["titles"].append(
            {"id": "PPSA01746", "excluded": [{"id": "11", "why": "its stop is the same with and without the fix"}]}
        )
        model = r.Model(raw, curated, "example/AnyPS5", NOW)
        self.assertEqual([s["blocker"] for s in model.titles["PPSA01746"]["chain"]], ["10"])
        self.assertNotIn("PPSA01746", model.blockers["11"]["titles"])

    def test_tags_follow_the_title_id_in_list_order(self):
        stray = self.t["PPSA02100"]
        self.assertEqual(stray["tags"], ["Puzzle", "Adventure"])
        self.assertEqual(stray["tag_sources"], ["https://www.wikidata.org/wiki/Q96247255"])
        self.assertEqual(self.t["PPSA01746"]["tags"], [])
        # an entry for a title the snapshot does not list adds no title
        self.assertNotIn("PPSA99000", self.t)

    def test_tags_survive_a_new_snapshot(self):
        """Tags live in the curated file and follow the title ID, so a re-mine keeps them even when the
        mined name changes or the title is gone for a while."""
        raw = json.loads((FIX / "raw.json").read_text(encoding="utf-8"))
        for item in raw["issues"] + raw["prs"]:
            for key in ("title", "body"):
                item[key] = (item.get(key) or "").replace("Stray (PPSA02100", "STRAY (PPSA02100")
        curated = r.load_curated(FIX / "curated.json")
        model = r.Model(raw, curated, "example/AnyPS5", NOW)
        self.assertEqual(model.titles["PPSA02100"]["name"], "STRAY")
        self.assertEqual(model.titles["PPSA02100"]["tags"], ["Puzzle", "Adventure"])
        raw["issues"] = [i for i in raw["issues"] if "PPSA02100" not in (i.get("body") or "") + i["title"]]
        raw["prs"] = [p for p in raw["prs"] if "PPSA02100" not in (p.get("body") or "")]
        self.assertNotIn("PPSA02100", r.Model(raw, curated, "example/AnyPS5", NOW).titles)
        self.assertEqual(len(curated["title_tags"]), 3)  # the entry waits for the title to come back

    def test_a_build_publishes_tags_and_their_list(self):
        import contextlib
        import io
        import tempfile

        from anyps5_roadmap.config import TAGS

        with tempfile.TemporaryDirectory() as d:
            args = [
                "--offline",
                "--no-network",
                "--cache",
                str(FIX / "raw.json"),
                "--curated",
                str(FIX / "curated.json"),
            ]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(r.main([*args, "--out", d]), 0)
            doc = json.loads((Path(d) / "roadmap.json").read_text(encoding="utf-8"))
        self.assertEqual([t["name"] for t in doc["tags"]], TAGS)
        self.assertEqual({t["group"] for t in doc["tags"]}, {"Dimension", "Genre", "Kind"})
        sarah = next(t for t in doc["titles"] if t["id"] == "PPSA02929")
        self.assertEqual(sarah["tags"], ["2D", "Platformer", "Adventure"])
        self.assertEqual(len(sarah["tag_sources"]), 2)
        self.assertEqual(doc["stats"]["titles_with_tags"], 2)

    def test_closed_issues_drop_out_of_the_open_chain(self):
        stray = self.t["PPSA02100"]
        self.assertEqual([s["blocker"] for s in stray["open_chain"]], ["10"])
        self.assertEqual(self.b["12"]["status"], "resolved")

    def test_scoring(self):
        b10, pr30, b11 = self.b["10"], self.b["pr-30"], self.b["11"]
        self.assertEqual((b10["frontier"], b10["one_fix_away"], b10["total"], b10["score"]), (2, 1, 3, 10))
        self.assertEqual((pr30["frontier"], pr30["one_fix_away"], pr30["total"], pr30["score"]), (1, 1, 1, 6))
        self.assertEqual((b11["frontier"], b11["one_fix_away"], b11["total"], b11["score"]), (0, 0, 1, 1))

    def test_tracker_rows_become_their_own_blockers(self):
        v = self.b["13~pthread_sigmask"]
        self.assertEqual(sorted(v["titles"]), ["PPSA99001", "PPSA99002", "PPSA99003", "PPSA99004", "PPSA99007"])
        self.assertEqual(v["score"], 3 * 5 + 2 * 5 + 5)
        self.assertEqual([p["ref"] for p in v["prs"]], ["#21"])
        self.assertEqual(self.b["13"]["total"], 0)

    def test_ranking_order(self):
        order = [b["id"] for b in self.model.ranking()][:5]
        self.assertEqual(order, ["13~pthread_sigmask", "13~uEtgPWgPxOk", "10", "pr-30", "11"])

    def test_pr_links_and_curated_fix_prs(self):
        refs = {p["ref"]: p["link"] for p in self.b["10"]["prs"]}
        self.assertEqual(refs["#20"], "fixes")
        self.assertEqual(self.b["10"]["origin"], "curated")
        self.assertEqual(self.b["11"]["origin"], "mined")
        self.assertEqual(self.b["10"]["area"], "shader")

    def test_a_resubmission_carries_on_a_closed_fix_pr(self):
        prs = {p["ref"]: p for p in self.b["pr-33"]["prs"]}
        self.assertEqual((prs["#33"]["state"], prs["#33"]["origin"]), ("closed", "curated"))
        self.assertEqual(
            (prs["#34"]["link"], prs["#34"]["state"], prs["#34"]["origin"], prs["#34"]["resubmits"]),
            ("fixes", "open", "mined", "#33"),
        )
        self.assertEqual(self.b["pr-33"]["status"], "open")
        # once the resubmission is merged, the PR-only blocker is resolved like any merged fix
        raw = json.loads((FIX / "raw.json").read_text(encoding="utf-8"))
        pr34 = next(p for p in raw["prs"] if p["number"] == 34)
        pr34.update({"state": "MERGED", "merged": True, "mergedAt": "2026-10-09T09:00:00Z"})
        model = r.Model(raw, r.load_curated(FIX / "curated.json"), "example/AnyPS5", NOW)
        self.assertEqual(model.blockers["pr-33"]["status"], "resolved")
        # an open PR that names the closed one without resubmitting it is not a fix
        pr34.update({"state": "OPEN", "merged": False, "mergedAt": None, "body": "Follow-up to #33."})
        model = r.Model(raw, r.load_curated(FIX / "curated.json"), "example/AnyPS5", NOW)
        self.assertEqual([p["ref"] for p in model.blockers["pr-33"]["prs"]], ["#33"])

    def carry(self, *bodies: str, fork_state: str = "OPEN") -> dict:
        """The fixture model plus upstream PRs #35, #36, ... with these bodies, and a PR-only blocker
        fork-7 whose fix PR is fork/AnyPS5#7."""
        raw = json.loads((FIX / "raw.json").read_text(encoding="utf-8"))
        base = next(p for p in raw["prs"] if p["number"] == 34)
        for n, body in enumerate(bodies, start=35):
            raw["prs"].append(dict(base, number=n, url=f"https://github.com/example/AnyPS5/pull/{n}", body=body))
        raw["external_prs"]["fork/AnyPS5#7"] = {
            "repo": "fork/AnyPS5",
            "number": 7,
            "title": "fix(libkernel): export sceKernelUsleep",
            "url": "https://github.com/fork/AnyPS5/pull/7",
            "state": fork_state,
            "merged": fork_state == "MERGED",
            "draft": False,
            "updatedAt": "2026-10-08T09:00:00Z",
        }
        curated = r.load_curated(FIX / "curated.json")
        curated["blockers"].append(
            {
                "id": "fork-7",
                "issue": None,
                "area": "libkernel",
                "fix_prs": [{"repo": "fork/AnyPS5", "number": 7}],
                "related_prs": [{"number": 30}],
            }
        )
        return r.Model(raw, curated, "example/AnyPS5", NOW).blockers

    def test_a_carry_of_a_closed_fix_pr_or_a_fork_fix_pr_is_a_fix(self):
        b = self.carry(
            "Carries #33 by @kim, which the intake check closed; the commit keeps its author.",
            "Carries [fork/AnyPS5#7](https://github.com/fork/AnyPS5/pull/7) by @kim.",
        )
        prs = {p["ref"]: p for p in b["pr-33"]["prs"]}
        self.assertEqual(
            (prs["#35"]["link"], prs["#35"]["state"], prs["#35"]["via"], prs["#35"]["resubmits"]),
            ("fixes", "open", ["resubmission"], "#33"),
        )
        prs = {p["ref"]: p for p in b["fork-7"]["prs"]}
        self.assertEqual((prs["#36"]["link"], prs["#36"]["resubmits"]), ("fixes", "fork#7"))
        # a fork PR is followed in any state, and its stand-in is listed right after it
        b = self.carry("Carried from fork/AnyPS5#7.", fork_state="MERGED")
        self.assertEqual([p["ref"] for p in b["fork-7"]["prs"]], ["fork#7", "#35", "#30"])

    def test_a_carry_needs_a_closed_pr_or_a_fork_pr_on_a_blocker(self):
        b = self.carry(
            "This branch carries #20 so the fix is reviewable with its demo; merge it first.",  # #20 is open
            "Carries #10, the packed pixel ancillary word.",  # #10 is an issue, not a PR
            "This carries the fix for #10 from the reporter.",
            "Carries #31 by @kim.",  # #31 is merged and on no blocker
        )
        refs = {p["ref"]: p["link"] for p in b["10"]["prs"]}
        self.assertEqual(refs["#20"], "fixes")
        self.assertEqual({refs[k] for k in ("#36", "#37")}, {"mentions"})
        self.assertNotIn("#35", refs)
        # only the fixture's own "This is #33 again" stands in for anything
        self.assertEqual([p["ref"] for bl in b.values() for p in bl["prs"] if p.get("resubmits")], ["#34"])

    def test_curated_stage_wins(self):
        best = self.model.best_stage(self.t["PPSA30279"])
        self.assertEqual((best["stage"], best["origin"], best["verified"]), ("Presents", "curated", True))

    def test_unreviewed_mined_menus_or_higher_is_only_a_claim(self):
        kena = self.t["PPSA01746"]
        self.assertIsNone(self.model.best_stage(kena))  # "reaches gameplay on my integration branch" is not a stage
        # nor a claim about main: it is where Kena gets off main, with the PR and the patches it needs
        self.assertIsNone(self.model.unverified_claim(kena))
        branch = self.model.branch_stage(kena)
        self.assertEqual((branch["stage"], branch["needs"], branch["patches"]), ("Ingame", [32], True))
        self.assertEqual(branch["url"], "https://github.com/example/AnyPS5/pull/32")
        self.assertIn("integration branch", branch["quote"])
        self.assertEqual(branch["confidence"]["label"], "1 report off main")
        # a mined stage below Menus counts, marked as not verified, when it ran on main: "the loading screen
        # renders" in open PR #20 is the PR's branch, so Stray stays at the stop its issue records on main
        stray = self.model.best_stage(self.t["PPSA02100"])
        self.assertEqual((stray["stage"], stray["origin"], stray["verified"]), ("Starts", "mined", False))
        self.assertIsNone(self.model.unverified_claim(self.t["PPSA02100"]))

    def test_stage_review_replaces_the_mined_claim(self):
        sarah = self.t["PPSA02929"]
        best = self.model.best_stage(sarah)
        self.assertEqual(
            (best["stage"], best["origin"], best["verified"], best["review"]), ("Menus", "curated", True, "confirmed")
        )
        self.assertTrue(best["quote"].startswith("Dreaming Sarah"))
        self.assertIsNone(self.model.unverified_claim(sarah))
        self.assertFalse(any(e["origin"] == "mined" and e["url"].endswith("/pull/31") for e in sarah["evidence"]))

    def test_unverified_claim_never_drives_sorting_or_ranking(self):
        upstream = r.Upstream(None, "HEAD", "example/AnyPS5", fetch=False, log=lambda m: None)
        doc = r.assemble(
            self.model,
            {"isa": None, "hle": None, "pm4": None, "registers": []},
            json.loads((FIX / "raw.json").read_text(encoding="utf-8")),
            upstream,
            NOW,
        )
        kena = next(t for t in doc["titles"] if t["id"] == "PPSA01746")
        self.assertIsNone(kena["best_stage"])
        self.assertIsNone(kena["unverified_claim"])
        self.assertEqual(kena["stage_on_branches"]["stage"], "Ingame")
        game = next(g for g in doc["games"] if "PPSA01746" in g["title_ids"])
        self.assertEqual(game["stage_on_branches"]["needs"], [32])
        self.assertIn("unverified claim", r.render_markdown(doc))
        self.assertIn("unverified_claim", r.render_llms(doc))

    def test_curated_stage_needs_a_public_url(self):
        import tempfile

        bad = {"blockers": [], "titles": [{"id": "PPSA16064", "evidence": [{"stage": "Playable", "url": None}]}]}
        review = {
            "blockers": [],
            "titles": [],
            "stage_reviews": [
                {
                    "title": "PPSA01746",
                    "claim": "Ingame",
                    "claim_url": "https://x/pull/1",
                    "verdict": "confirmed",
                    "stage": "Ingame",
                    "url": "https://x/pull/1",
                }
            ],
        }
        for data in (bad, review):
            with tempfile.TemporaryDirectory() as d:
                path = Path(d) / "blockers.json"
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(SystemExit):
                    r.load_curated(path)

    def test_validation_lists_every_problem_at_once(self):
        data = {
            "blockers": [{"id": "1", "area": "gpu", "fix_prs": [{"repo": "x/y"}]}, {"id": "1"}],
            "titles": [
                {
                    "id": "PPSA123",
                    "blockers": [{"id": "9"}],
                    "excluded": [{"id": "8"}],
                    "evidence": [{"stage": "Boots", "url": ""}],
                }
            ],
            "stage_reviews": [{"title": "PPSA01746", "verdict": "maybe"}],
        }
        errors = r.validate_curated(data)
        joined = "\n".join(errors)
        for needle in (
            "blocker id '1' is used more than once",
            "area 'gpu' is not one of",
            "fix_prs[0] needs a PR number",
            "PPSA plus five digits",
            "names blocker '9', which is not in blockers[]",
            "excluded[0] names blocker '8', which is not in blockers[]",
            "excluded[0] needs a why",
            "stage 'Boots'",
            "has no url",
            "verdict must be confirmed, downgraded or suppressed",
        ):
            self.assertIn(needle, joined)
        self.assertEqual(r.validate_curated(r.load_curated(FIX / "curated.json")), [])

    def test_tag_validation(self):
        good = {
            "title": "PPSA02100",
            "name": "Stray",
            "tags": ["Adventure"],
            "sources": ["https://www.wikidata.org/wiki/Q96247255"],
        }
        self.assertEqual(r.validate_curated({"title_tags": [good]}), [])
        bad = [
            {**good, "title": "PPSA123"},
            {**good, "title": "PPSA02929", "name": ""},
            {**good, "title": "PPSA01746", "tags": ["Metroidvania", "Adventure", "Adventure"]},
            {**good, "title": "PPSA21564", "tags": ["2D", "3D"]},
            {**good, "title": "PPSA99000", "tags": ["App", "Puzzle"]},
            {**good, "title": "PPSA99001", "tags": []},
            {**good, "title": "PPSA99002", "sources": []},
            {**good, "title": "PPSA99003", "sources": ["http://example.com/readme"]},
            good,
        ]
        joined = "\n".join(r.validate_curated({"title_tags": [good, *bad]}))
        for needle in (
            "PPSA02100 has more than one entry",
            "title must be a PS5 title ID",
            "needs the name the sources were matched on",
            "tag 'Metroidvania' is not one of",
            "tag 'Adventure' is listed twice",
            "2D and 3D exclude each other",
            "App means not a game",
            "needs a list of tags",
            "needs sources",
            "must be an https link",
        ):
            self.assertIn(needle, joined)

    def test_name_sources_validation(self):
        good = {
            "id": "PPSA01317",
            "name": "Gran Turismo 7",
            "name_sources": ["https://prosperopatches.com/PPSA01317"],
        }
        self.assertEqual(r.validate_curated({"titles": [good]}), [])
        bad = [
            {**good, "id": "PPSA01284", "name": ""},
            {**good, "id": "PPSA03974", "name_sources": []},
            {**good, "id": "PPSA20612", "name_sources": ["http://prosperopatches.com/PPSA20612"]},
        ]
        joined = "\n".join(r.validate_curated({"titles": bad}))
        for needle in ("name_sources without a name", "name_sources needs the public links", "must be an https link"):
            self.assertIn(needle, joined)

    def test_invalid_json_names_line_and_column(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "blockers.json"
            path.write_text('{\n  "blockers": [,]\n}', encoding="utf-8")
            with self.assertRaises(SystemExit) as cm:
                r.load_curated(path)
            self.assertIn(":2:16: not valid JSON", str(cm.exception))

    def test_render_outputs(self):
        upstream = r.Upstream(None, "HEAD", "example/AnyPS5", fetch=False, log=lambda m: None)
        doc = r.assemble(
            self.model,
            {"isa": None, "hle": None, "pm4": None, "registers": []},
            json.loads((FIX / "raw.json").read_text(encoding="utf-8")),
            upstream,
            NOW,
        )
        self.assertEqual(doc["schema_version"], r.SCHEMA_VERSION)
        html = r.render_html.Page(doc).render()
        for anchor in ('id="fix-next"', 'id="games"', 'id="data"', 'id="panel"', "not an official AnyPS5 page"):
            self.assertIn(anchor, html)
        for b in doc["blockers"]:
            if b.get("total"):
                self.assertIn(f'id="b-{b["id"]}"', html)
        for t in doc["titles"]:
            for step in t.get("open_blockers") or []:
                if any(b["id"] == step["id"] and b.get("total") for b in doc["blockers"]):
                    self.assertIn(f'href="#b-{step["id"]}"', html)
        self.assertIn("13~pthread_sigmask", r.render_markdown(doc) + json.dumps(doc))
        self.assertTrue(r.render_llms(doc).startswith("# AnyPS5 blocker map\n\n> "))


if __name__ == "__main__":
    unittest.main()
