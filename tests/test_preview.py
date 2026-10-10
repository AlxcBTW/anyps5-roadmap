"""Tests for the PR preview summary (anyps5_roadmap/preview.py). No network."""

import copy
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import roadmap as r  # noqa: E402
from anyps5_roadmap import preview  # noqa: E402

FIX = HERE / "fixtures"
NOW = dt.datetime(2026, 10, 10, 12, 0, tzinfo=dt.UTC)


def build_doc(curated: dict) -> dict:
    raw = json.loads((FIX / "raw.json").read_text(encoding="utf-8"))
    model = r.Model(raw, curated, "example/AnyPS5", NOW)
    upstream = r.Upstream(None, "HEAD", "example/AnyPS5", fetch=False, log=lambda m: None, network=False)
    return r.assemble(model, {"isa": None, "hle": None, "pm4": None, "registers": []}, raw, upstream, NOW)


def write_site(root: Path, doc: dict) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "roadmap.json").write_text(json.dumps(doc), encoding="utf-8")
    (root / "ROADMAP.md").write_text(r.render_markdown(doc), encoding="utf-8")
    return root


class Preview(unittest.TestCase):
    def setUp(self):
        self.curated = r.load_curated(FIX / "curated.json")
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_identical_builds_say_nothing_changed(self):
        doc = build_doc(self.curated)
        text = preview.render(write_site(self.root / "a", doc), write_site(self.root / "b", doc), "fixtures")
        self.assertIn("No change to the ranking", text)
        self.assertIn("built from fixtures", text)
        self.assertNotIn("Titles that change", text)

    def test_a_curated_stage_review_shows_up_as_a_title_change(self):
        base = build_doc(self.curated)
        changed = copy.deepcopy(self.curated)
        changed["stage_reviews"].append(
            {
                "title": "PPSA01746",
                "claim": "Ingame",
                "claim_url": "https://github.com/example/AnyPS5/pull/32",
                "verdict": "suppressed",
                "quote": "Kena: Bridge of Spirits (PPSA01746) reaches gameplay on my integration branch.",
                "reason": "integration branch",
            }
        )
        head = build_doc(changed)
        text = preview.render(write_site(self.root / "a", base), write_site(self.root / "b", head))
        self.assertIn("Titles that change (1)", text)
        self.assertIn("`PPSA01746` Kena: Bridge of Spirits", text)
        self.assertIn("Ingame → **—**", text)
        self.assertIn("ROADMAP.md diff", text)

    def test_missing_base_still_reports_the_head(self):
        doc = build_doc(self.curated)
        text = preview.render(self.root / "missing", write_site(self.root / "b", doc))
        self.assertIn("could not be built", text)
        self.assertIn("| Title IDs | 14 |", text)


if __name__ == "__main__":
    unittest.main()
