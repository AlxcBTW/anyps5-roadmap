"""Game identity: the name normaliser, merging title IDs into games, the review list and overrides."""

import sys
import unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from anyps5_roadmap.cli import validate_games  # noqa: E402
from anyps5_roadmap.identity import TitleNames, name_key, parse_catalog, related, resolve, slug  # noqa: E402

TSV = "titleId\tconceptId\tname\tcontentId\tregion\tpublisherId\n" + "\n".join(
    "\t".join(row)
    for row in [
        ("PPSA04263_00", "201930", "Grand Theft Auto V", "EP1004-PPSA04263_00-GTAVFULLGAMEDISC", "EP", "EP1004"),
        ("PPSA04264_00", "201930", "Grand Theft Auto V", "UP1004-PPSA04264_00-GTAVFULLGAMEDISC", "UP", "UP1004"),
        ("PPSA21564_00", "10002684", "ASTRO BOT", "UP9000-PPSA21564_00-0000000000000000", "UP", "UP9000"),
        ("PPSA21567_00", "10002684", "ASTRO BOT", "EP9000-PPSA21567_00-0000000000000000", "EP", "EP9000"),
        ("PPSA05510_00", "10000771", "Minecraft Legends", "EP4433-PPSA05510_00-1296939562310362", "EP", "EP4433"),
        ("PPSA17221_00", "212779", "Minecraft", "UP4433-PPSA17221_00-MINECRAFTPS50000", "UP", "UP4433"),
        ("PPSA19111_00", "10009999", "Mars Base", "EP0001-PPSA19111_00-MARSBASE00000000", "EP", "EP0001"),
        ("PPSA03396_00", "10000001", "The Last of Us™ Part I", "UP9000-PPSA03396_00-TLOU000000000000", "UP", "UP9000"),
    ]
)


def names(*mined, curated=None):
    return TitleNames(curated, Counter(dict(mined)))


class NameKeys(unittest.TestCase):
    def key(self, name):
        return name_key(name).key

    def test_abbreviations_and_roman_numerals(self):
        for name in ("GTA V", "GTA5", "gta 5", "Grand Theft Auto V", "Grand Theft Auto 5", "GRAND THEFT AUTO V™"):
            self.assertEqual(self.key(name), "grand theft auto 5", name)
        self.assertEqual(self.key("RE4"), self.key("Resident Evil 4"))
        self.assertEqual(self.key("FFVII Rebirth"), self.key("Final Fantasy VII Rebirth"))
        self.assertEqual(self.key("CoD Black Ops 2"), self.key("Call of Duty: Black Ops II"))
        self.assertEqual(self.key("TLOU Part 1"), self.key("The Last of Us Part I"))
        self.assertEqual(self.key("Blasphemous II"), self.key("Blasphemous 2"))

    def test_ambiguous_short_forms_need_a_number(self):
        self.assertEqual(self.key("Re:Zero - Starting Life in Another World"), "re zero starting life in another world")
        self.assertEqual(self.key("GT7"), "gran turismo 7")
        self.assertEqual(self.key("GT Racing"), "gt racing")

    def test_single_letter_numerals_only_at_the_end(self):
        self.assertEqual(self.key("Raiden III x MIKADO MANIAX"), "raiden 3 x mikado maniax")
        self.assertEqual(self.key("V Rising"), "v rising")
        self.assertEqual(self.key("Mega Man X"), "mega man x")

    def test_symbols_punctuation_accents_and_articles(self):
        self.assertEqual(self.key("Astro Bot™"), self.key("ASTRO BOT"))
        self.assertEqual(self.key("Don’t Starve Together"), self.key("Dont Starve Together"))
        self.assertEqual(self.key("Ghost of Yōtei"), "ghost of yotei")
        self.assertEqual(self.key("Ratchet & Clank: Rift Apart"), self.key("Ratchet and Clank - Rift Apart"))
        self.assertEqual(self.key("The Last of Us Part I"), self.key("Last of Us Part I"))
        self.assertEqual(self.key("永久與神樹的祈願者"), "永久與神樹的祈願者")

    def test_region_platform_and_edition_suffixes(self):
        for name in (
            "Cyberpunk 2077 (PS5)",
            "Cyberpunk 2077: Ultimate Edition",
            "Cyberpunk 2077 PS5",
            "Cyberpunk 2077 (EU)",
        ):
            self.assertEqual(self.key(name), "cyberpunk 2077", name)
        self.assertEqual(self.key("DOOM Shareware (homebrew)"), "doom shareware")
        # a product name is not an edition suffix
        self.assertNotEqual(
            self.key("Grand Theft Auto: San Andreas - The Definitive Edition"), "grand theft auto san andreas"
        )
        self.assertNotEqual(self.key("Horizon Zero Dawn Remastered"), self.key("Horizon Zero Dawn"))

    def test_subtitle_base(self):
        k = name_key("Demon Slayer -Kimetsu no Yaiba- The Hinokami Chronicles")
        self.assertEqual(k.base, "demon slayer")
        self.assertIsNone(name_key("Cyberpunk 2077: Ultimate Edition").base)

    def test_slug(self):
        self.assertEqual(slug("Grand Theft Auto V"), "grand-theft-auto-v")
        self.assertEqual(slug("Ghost of Yōtei"), "ghost-of-yotei")
        self.assertEqual(slug("永久與神樹的祈願者"), "")

    def test_related(self):
        self.assertTrue(related("UFC 6", "EA SPORTS UFC 6"))
        self.assertTrue(
            related("Yaiba- The Hinokami Chronicles", "Demon Slayer -Kimetsu no Yaiba- The Hinokami Chronicles")
        )
        self.assertFalse(related("XashPS5", "Mars Base"))
        self.assertTrue(related("LEGO Horizon Adventures", "LEGO® ホライゾン アドベンチャー"))  # another script


class Catalog(unittest.TestCase):
    def test_parse(self):
        cat = parse_catalog(TSV)
        self.assertEqual(cat["PPSA04264"].concept, "201930")
        self.assertEqual(cat["PPSA04264"].region_name, "US")
        self.assertEqual(cat["PPSA04263"].content_id, "EP1004-PPSA04263_00-GTAVFULLGAMEDISC")
        self.assertEqual(parse_catalog("not a table"), {})


class Resolve(unittest.TestCase):
    def setUp(self):
        self.cat = parse_catalog(TSV)

    def test_gta_v_long_and_short_form_are_one_game(self):
        ident = resolve(
            {"PPSA04263": names(("Grand Theft Auto V", 3)), "PPSA04264": names(("GTA V", 40))}, {}, self.cat
        )
        g = ident.game_of("PPSA04264")
        self.assertIs(g, ident.game_of("PPSA04263"))
        self.assertEqual((g.id, g.name, g.name_origin), ("grand-theft-auto-v", "Grand Theft Auto V", "store"))
        self.assertIn("GTA V", g.aliases)
        self.assertEqual(len(ident.merges), 1)
        self.assertIn("same PlayStation Store concept (201930)", ident.merges[0]["reasons"])

    def test_without_the_store_list_mined_spellings_still_merge_with_reasons(self):
        ident = resolve({"PPSA04263": names(("Grand Theft Auto V", 3)), "PPSA04264": names(("GTA V", 40))})
        g = ident.game_of("PPSA04264")
        self.assertEqual(g.title_ids, ["PPSA04263", "PPSA04264"])
        self.assertEqual(g.name, "Grand Theft Auto V")  # the full form, not the abbreviation
        reason = ident.merges[0]["reasons"][0]
        self.assertIn("GTA = Grand Theft Auto", reason)
        self.assertIn("V = 5", reason)

    def test_region_variants_of_one_concept_and_the_nicer_spelling(self):
        ident = resolve({"PPSA21564": names(("Astro Bot", 12)), "PPSA21567": names(("ASTRO BOT", 1))}, {}, self.cat)
        g = ident.game_of("PPSA21567")
        self.assertEqual((g.name, g.title_ids), ("Astro Bot", ["PPSA21564", "PPSA21567"]))
        self.assertEqual(ident.titles["PPSA21564"]["region"], "UP")

    def test_store_names_drop_trademark_signs(self):
        ident = resolve({"PPSA03396": names(("Last of Us Part I", 2))}, {}, self.cat)
        self.assertEqual(ident.game_of("PPSA03396").name, "The Last of Us Part I")
        self.assertEqual(ident.game_of("PPSA03396").aliases, ["Last of Us Part I"])

    def test_a_mined_name_matching_a_listed_game_goes_to_review(self):
        # PPSA02158 is not in the store list: its ID may be wrong even though its name is right
        ident = resolve({"PPSA21564": names(("Astro Bot", 5)), "PPSA02158": names(("Astro Bot", 1))}, {}, self.cat)
        self.assertIsNot(ident.game_of("PPSA02158"), ident.game_of("PPSA21564"))
        kinds = [r["kind"] for r in ident.review]
        self.assertEqual(kinds, ["mined-name"])
        self.assertEqual(ident.review[0]["title_ids"], ["PPSA02158", "PPSA21564"])

    def test_different_store_concepts_are_different_games(self):
        ident = resolve(
            {"PPSA17221": names(("Minecraft", 4)), "PPSA05510": names(("Minecraft Legends", 2))}, {}, self.cat
        )
        self.assertIsNot(ident.game_of("PPSA17221"), ident.game_of("PPSA05510"))
        self.assertEqual(ident.review, [])  # the store tells them apart; nothing to review

    def test_subtitle_prefix_and_spelling_matches_are_reviewed_not_merged(self):
        ident = resolve(
            {
                "PPSA99001": names(("Prospero Radio", 3)),
                "PPSA99002": names(("Prospero Radio: Night Edition", 2)),
                "PPSA99003": names(("Nuvio PS5", 2)),
                "PPSA99004": names(("Nuvio Max", 2)),
                "PPSA99005": names(("Hollow Knight Silksong", 2)),
                "PPSA99006": names(("Hollow Knight Sliksong", 1)),
                "PPSA99007": names(("Hades", 2)),
                "PPSA99008": names(("Hades II", 2)),
            }
        )
        self.assertEqual(len(ident.games), 8)
        self.assertEqual(ident.merges, [])
        self.assertEqual(
            sorted(r["kind"] for r in ident.review), ["prefix", "similar", "subtitle"]
        )  # Hades II is a sequel

    def test_curated_games_merge_and_distinct_keeps_apart(self):
        overrides = {
            "games": [
                {
                    "name": "Prospero Radio",
                    "title_ids": ["PPSA99001", "PPSA99002"],
                    "aliases": ["PRadio"],
                    "sources": ["https://example.org"],
                }
            ],
            "distinct": [{"title_ids": ["PPSA99010", "PPSA99011"], "reason": "two different apps"}],
        }
        ident = resolve(
            {
                "PPSA99001": names(("Prospero Radio", 3)),
                "PPSA99002": names(("Radio for PS5", 2)),
                "PPSA99010": names(("Same Name", 2)),
                "PPSA99011": names(("Same Name", 2)),
            },
            overrides,
        )
        g = ident.game_of("PPSA99002")
        self.assertEqual(
            (g.name, g.name_origin, g.title_ids), ("Prospero Radio", "curated", ["PPSA99001", "PPSA99002"])
        )
        self.assertEqual(g.aliases[0], "PRadio")
        self.assertIn("listed together in data/games.json", ident.merges[0]["reasons"])
        self.assertIsNot(ident.game_of("PPSA99010"), ident.game_of("PPSA99011"))

    def test_a_homebrew_on_a_retail_id_keeps_its_own_name(self):
        ident = resolve({"PPSA19111": names(("XashPS5", 9))}, {}, self.cat)
        self.assertEqual(ident.game_of("PPSA19111").name, "XashPS5")
        self.assertEqual(ident.game_of("PPSA19111").concepts, [])  # no store art of Mars Base either
        self.assertEqual(ident.review[0]["kind"], "reused-id")
        curated = resolve({"PPSA19111": names(("XashPS5", 9), curated="XashPS5")}, {}, self.cat)
        self.assertEqual(curated.review, [])
        self.assertEqual(curated.game_of("PPSA19111").aliases, [])

    def test_placeholder_ids_are_dropped(self):
        ident = resolve({"PPSA00000": names(("Label", 1)), "PPSA01000": names(("Real", 1))})
        self.assertEqual(ident.dropped, ["PPSA00000"])
        self.assertNotIn("PPSA00000", ident.of)


class GamesFile(unittest.TestCase):
    def test_validation(self):
        ok = {
            "games": [{"name": "X", "title_ids": ["PPSA00001", "CUSA00002"], "sources": ["https://example.org"]}],
            "distinct": [{"title_ids": ["PPSA00003", "PPSA00004"], "reason": "two games"}],
        }
        self.assertEqual(validate_games(ok), [])
        bad = {
            "games": [
                {"title_ids": ["PPSA1"], "sources": ["http://x"]},
                {"title_ids": ["PPSA00001", "PPSA00001"], "sources": []},
            ],
            "distinct": [{"title_ids": ["PPSA00003"]}],
        }
        errors = validate_games(bad)
        self.assertTrue(any("is not a title ID" in e for e in errors))
        self.assertTrue(any("https link" in e for e in errors))
        self.assertTrue(any("already listed" in e for e in errors))
        self.assertTrue(any("needs sources" in e for e in errors))
        self.assertTrue(any("needs a reason" in e for e in errors))
        self.assertTrue(any("two or more" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
