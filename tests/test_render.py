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


if __name__ == "__main__":
    unittest.main()
