"""Whole-word mentions of names in issue texts (coverage.py): the word index must agree with the regex it replaced."""

import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from anyps5_roadmap import coverage as cv  # noqa: E402

TEXTS = {
    1: "sceKernelUsleep fails; also call sceKernelUsleepX and xsceKernelUsleep",
    2: "IT_DRAW_INDEX_AUTO is not handled, PKT3_DISPATCH_DIRECT neither",
    3: "`sceKernelUsleep`, (sceKernelUsleep) and sceKernelUsleep_ are different",
    4: "DRAW_INDEX_AUTO\nDISPATCH_DIRECT",
    5: "",
}


def old_regex(name, prefixes=False):
    lead = r"(?:IT_|PKT3_)?" if prefixes else ""
    rx = re.compile(r"(?<![A-Za-z0-9_])" + lead + re.escape(name) + r"(?![A-Za-z0-9_])")
    return sorted(n for n, t in TEXTS.items() if rx.search(t))


class Mentions(unittest.TestCase):
    def test_a_name_counts_only_as_a_whole_word(self):
        index = cv.word_index(TEXTS)
        self.assertEqual(cv.mentions_of("sceKernelUsleep", TEXTS, index), [1, 3])

    def test_the_index_agrees_with_the_regex_for_library_names(self):
        index = cv.word_index(TEXTS)
        for name in ("sceKernelUsleep", "sceKernelUsleepX", "missing", "Usleep"):
            self.assertEqual(cv.mentions_of(name, TEXTS, index), old_regex(name), name)

    def test_pm4_names_match_with_or_without_their_prefix(self):
        names = ["DRAW_INDEX_AUTO", "DISPATCH_DIRECT", "NOP"]
        got = cv.mention_count(names, TEXTS)
        for name in names:
            self.assertEqual(got[name], old_regex(name, prefixes=True), name)
        self.assertEqual(got["DRAW_INDEX_AUTO"], [2, 4])

    def test_a_name_with_other_characters_falls_back_to_the_regex(self):
        texts = {1: "calls sce::Foo now", 2: "sce::FooBar"}
        self.assertEqual(cv.mentions_of("sce::Foo", texts, cv.word_index(texts)), [1])


if __name__ == "__main__":
    unittest.main()
