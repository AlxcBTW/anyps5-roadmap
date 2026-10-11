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

    def test_curated_stage_wins(self):
        best = self.model.best_stage(self.t["PPSA30279"])
        self.assertEqual((best["stage"], best["origin"], best["verified"]), ("Presents", "curated", True))

    def test_unreviewed_mined_menus_or_higher_is_only_a_claim(self):
        kena = self.t["PPSA01746"]
        self.assertIsNone(self.model.best_stage(kena))  # "reaches gameplay on my integration branch" is not a stage
        claim = self.model.unverified_claim(kena)
        self.assertEqual(claim["stage"], "Ingame")
        self.assertEqual(claim["url"], "https://github.com/example/AnyPS5/pull/32")
        self.assertIn("integration branch", claim["quote"])
        # a mined stage below Menus still counts, marked as not verified
        stray = self.model.best_stage(self.t["PPSA02100"])
        self.assertEqual((stray["stage"], stray["origin"], stray["verified"]), ("Presents", "mined", False))
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
        self.assertEqual(set(kena["unverified_claim"]), {"stage", "url", "quote"})
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
            "titles": [{"id": "PPSA123", "blockers": [{"id": "9"}], "evidence": [{"stage": "Boots", "url": ""}]}],
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
            "stage 'Boots'",
            "has no url",
            "verdict must be confirmed, downgraded or suppressed",
        ):
            self.assertIn(needle, joined)
        self.assertEqual(r.validate_curated(r.load_curated(FIX / "curated.json")), [])

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
