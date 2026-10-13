"""The game identity migration report (anyps5_roadmap/migrate.py): every merge, rename, stage change and
review item is listed. Built from the fixtures; no network."""

import copy
import datetime as dt
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import roadmap as r  # noqa: E402
from anyps5_roadmap import migrate  # noqa: E402
from anyps5_roadmap.identity import parse_catalog  # noqa: E402

FIX = HERE / "fixtures"
NOW = dt.datetime(2026, 10, 13, 12, 0, tzinfo=dt.UTC)


def build() -> dict:
    raw = json.loads((FIX / "raw.json").read_text(encoding="utf-8"))
    catalog = parse_catalog((FIX / "PS5_Titles.tsv").read_text(encoding="utf-8"))
    model = r.Model(raw, r.load_curated(FIX / "curated.json"), "example/AnyPS5", NOW, catalog=catalog)
    upstream = r.Upstream(None, "HEAD", "example/AnyPS5", fetch=False, log=lambda m: None, network=False)
    return r.assemble(model, {"isa": None, "hle": None, "pm4": None, "registers": []}, raw, upstream, NOW)


def schema_1(doc: dict) -> dict:
    """The same snapshot as the page saw it before games: titles only, the EU Kena under another name, and
    Stray at the stage an open PR's branch reached."""
    old = copy.deepcopy(doc)
    old["schema_version"] = 1
    del old["games"], old["identity"]
    for t in old["titles"]:
        t.pop("game", None)
        if t["id"] == "PPSA01802":
            t["name"] = "Kena"
            t["best_stage"] = {
                "stage": "Starts",
                "origin": "mined",
                "url": "https://github.com/example/AnyPS5/issues/11",
            }
        if t["id"] == "PPSA02100":
            t["best_stage"] = {**(t["best_stage"] or {}), "stage": "Presents"}
    return old


class Report(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.after = build()
        cls.text = migrate.report(schema_1(cls.after), cls.after)

    def test_lists_every_merge_with_its_names_before_and_reasons(self):
        self.assertIn(
            "| Kena: Bridge of Spirits | `PPSA01746` (US), `PPSA01802` (EU) | `PPSA01746`: Kena: Bridge of Spirits; "
            "`PPSA01802`: Kena | same PlayStation Store concept (10001235) |",
            self.text,
        )
        self.assertIn("1 game holds more than one title ID.", self.text)

    def test_counts_before_and_after(self):
        self.assertIn("| Games on the page | 13 | 12 |", self.text)
        self.assertIn("| Title IDs folded into another game | 0 | 1 |", self.text)

    def test_lists_renamed_titles_and_stage_changes_with_why(self):
        self.assertIn("| `PPSA01802` | Kena | Kena: Bridge of Spirits | PlayStation title list |", self.text)
        self.assertIn(
            "| Stray | Presents | Starts | the higher stage was reported only off main (open PRs or patches); "
            "stage off main now: Presents with #20 |",
            self.text,
        )
        self.assertIn("| Kena: Bridge of Spirits | Starts | no stage | the higher stage", self.text)

    def test_cli_writes_the_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            before, after, out = Path(tmp, "a.json"), Path(tmp, "b.json"), Path(tmp, "r.md")
            before.write_text(json.dumps(schema_1(self.after)), encoding="utf-8")
            after.write_text(json.dumps(self.after), encoding="utf-8")
            self.assertEqual(migrate.main(["--before", str(before), "--after", str(after), "--out", str(out)]), 0)
            self.assertTrue(out.read_text(encoding="utf-8").startswith("# Game identity migration"))


if __name__ == "__main__":
    unittest.main()
