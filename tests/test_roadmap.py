"""Fixture tests for the extraction and ranking logic. No network, no gh."""

import datetime as dt
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import roadmap as r  # noqa: E402

FIX = HERE / "fixtures"
NOW = dt.datetime(2026, 10, 10, 12, 0, tzinfo=dt.timezone.utc)


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
        a = r.signature_from("presentation failed: compute shader 0x2006410000: AGC graphics: storage image access to "
                             "depth/stencil surface 0x20183b0000 is not implemented")
        b = r.signature_from("  what():  AGC graphics: storage image access to depth/stencil surface 0x53a500000 is not implemented")
        self.assertEqual(a["key"], b["key"])
        self.assertEqual(a["display"], "AGC graphics: storage image access to depth/stencil surface 0x… is not implemented")

    def test_signature_keeps_balanced_parentheses_and_cuts_markdown(self):
        s = r.signature_from("`ShaderRecompiler::Recompile: shader info collection failed: packed pixel ancillary input has an "
                             "unsupported live use (used by SelectU32 ? ?)`. #1904 made all four compile")
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
        # a stop phrase before the keyword means the title did not get past it
        self.assertEqual(r.stage_in("PPSA05684 stops in its first level with an error", 0)[0], "Menus")

    def test_closing_references(self):
        refs = r.closing_refs("Fixes #12 and #34. Closes owner/repo#5. Mentions #99.", "example/AnyPS5")
        self.assertEqual(refs, [("example/AnyPS5", 12), ("example/AnyPS5", 34), ("owner/repo", 5)])

    def test_pm4_unsupported_reason_parser(self):
        src = '''
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
}'''
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

    def test_curated_stage_wins(self):
        best = self.model.best_stage(self.t["PPSA30279"])
        self.assertEqual((best["stage"], best["origin"]), ("Presents", "curated"))

    def test_render_outputs(self):
        upstream = r.Upstream(None, "HEAD", "example/AnyPS5", fetch=False, log=lambda m: None)
        doc = r.assemble(self.model, {"isa": None, "hle": None, "pm4": None, "registers": []},
                         json.loads((FIX / "raw.json").read_text(encoding="utf-8")), upstream, NOW)
        self.assertEqual(doc["schema_version"], r.SCHEMA_VERSION)
        html = r.render_html(doc)
        for anchor in ('id="ranking"', 'id="titles"', 'id="coverage"', 'id="focus"', 'id="about"', "not official"):
            self.assertIn(anchor, html)
        self.assertNotIn("<script", html)
        self.assertIn("13~pthread_sigmask", r.render_markdown(doc) + json.dumps(doc))
        self.assertTrue(r.render_llms(doc).startswith("# AnyPS5 blocker map\n\n> "))


if __name__ == "__main__":
    unittest.main()
