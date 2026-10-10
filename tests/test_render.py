"""Tests for the coverage treemap layout in render_html.py. No network."""

import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import render_html as h  # noqa: E402


def cells(html: str) -> tuple[int, int]:
    """Count (cells, missing cells) in one rendered tile from its bands' grids and missing runs."""
    total = missing = 0
    for band in re.finditer(r'<div class="tm-band[^"]*" style="[^"]*--c:(\d+);--r:(\d+)">(.*?)</div>', html):
        cols, rows = int(band[1]), int(band[2])
        total += cols * rows
        for run in re.finditer(r"width:([\d.]+)%;height:([\d.]+)%", band[3]):
            missing += round(float(run[1]) * cols / 100) * round(float(run[2]) * rows / 100)
    return total, missing


class Treemap(unittest.TestCase):
    def test_squarify_fills_the_area(self):
        rects = h.squarify([(v, i) for i, v in enumerate([618, 511, 229, 195, 7, 3, 1])], 0, 0, 640, 290)
        self.assertEqual(len(rects), 7)
        self.assertAlmostEqual(sum(w * hh for _, _, _, w, hh in rects), 640 * 290, places=3)

    def test_every_cell_is_a_function_and_missing_cells_match(self):
        page = h.Page.__new__(h.Page)
        for done, todo in [(599, 19), (195, 34), (0, 4), (7, 0), (1, 1), (113, 22), (40, 11), (3, 23), (5, 25)]:
            group = {"label": "lib", "done": done, "todo": todo, "todo_names": [], "requested": {}}
            for w, hh in [(640, 290), (80, 40), (12, 30), (300, 9)]:
                html = page.treemap([group], "label", w, hh, "functions")
                self.assertEqual(cells(html), (done + todo, todo), (done, todo, w, hh))
                self.assertNotIn("void", html)


class CorrectionLinks(unittest.TestCase):
    def setUp(self):
        import datetime as dt
        import json

        import roadmap as r

        fix = HERE / "fixtures"
        raw = json.loads((fix / "raw.json").read_text(encoding="utf-8"))
        now = dt.datetime(2026, 10, 10, 12, 0, tzinfo=dt.UTC)
        model = r.Model(raw, r.load_curated(fix / "curated.json"), "example/AnyPS5", now)
        upstream = r.Upstream(None, "HEAD", "example/AnyPS5", fetch=False, log=lambda m: None, network=False)
        self.doc = r.assemble(model, {"isa": None, "hle": None, "pm4": None, "registers": []}, raw, upstream, now)
        self.html = h.Page(self.doc).render()

    def links(self) -> list[dict[str, str]]:
        import html as htmlmod
        import urllib.parse

        out = []
        for href in re.findall(r'<a class="report" href="([^"]+)"', self.html):
            url = urllib.parse.urlsplit(htmlmod.unescape(href))
            self.assertEqual(url.netloc + url.path, "github.com/AlxcBTW/anyps5-roadmap/issues/new")
            out.append({k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()})
        return out

    def test_every_game_row_and_blocker_has_a_prefilled_link(self):
        links = self.links()
        rows = self.html.count('<tr class="game"')
        bodies = self.html.count('<div class="body">')
        self.assertEqual(len(links), rows + bodies)
        sarah = next(q for q in links if q.get("title_id") == "PPSA02929")
        self.assertEqual(sarah["template"], "wrong-stage.yml")
        self.assertEqual(sarah["page_stage"], "Menus (curated)")
        self.assertEqual(sarah["page_source"], "https://github.com/example/AnyPS5/pull/31")
        self.assertEqual(sarah["title"], "Stage: Dreaming Sarah (PPSA02929)")
        kena = next(q for q in links if q.get("title_id") == "PPSA01746")
        self.assertEqual(kena["page_stage"], "No stage yet; claimed Ingame, unverified")
        blocker = next(q for q in links if q.get("blocker", "").startswith("#10 "))
        self.assertEqual(blocker["template"], "blocker.yml")
        self.assertEqual(blocker["page_source"], "https://github.com/example/AnyPS5/issues/10")
        self.assertIn("packed pixel ancillary input", blocker["error"])

    def test_each_link_names_what_it_corrects_for_screen_readers(self):
        self.assertIn('Report a correction<span class="sr-only"> for Dreaming Sarah (PPSA02929)</span>', self.html)
        self.assertIn('Report a correction<span class="sr-only"> for #10</span>', self.html)


if __name__ == "__main__":
    unittest.main()
