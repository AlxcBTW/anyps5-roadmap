"""Chain order: which blocker a title's newest stop on main points at. No network."""

import datetime as dt
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from anyps5_roadmap.model import Model  # noqa: E402

NOW = dt.datetime(2026, 10, 16, 12, 0, tzinfo=dt.UTC)
REPO = "example/AnyPS5"
LOST = "terminate called after throwing an instance of 'std::runtime_error'\n  what():  vkWaitForFences present: Vulkan result -4"
DEPTH_STORAGE = "AGC graphics: storage image access to depth/stencil surface 0x3 is not implemented"


def issue(number, title, body, created, state="OPEN", reason=None):
    return {
        "number": number,
        "title": title,
        "body": body,
        "url": f"https://github.com/{REPO}/issues/{number}",
        "state": state,
        "stateReason": reason,
        "createdAt": created,
        "updatedAt": created,
        "closedAt": None if state == "OPEN" else created,
        "author": "reporter",
        "labels": [],
        "assignees": [],
        "comments": [],
        "xrefs": [],
        "closed_by": [],
    }


class ClosedIssueStops(unittest.TestCase):
    """A stop logged in an issue that was fixed since says the title got past it; it must not make
    another open issue with the same error line the title's first stop (#87)."""

    @classmethod
    def setUpClass(cls):
        raw = {
            "repo": REPO,
            "issues": [
                # Ghostrunner's own open issue, which carries the error line as its signature
                issue(
                    10, "Ghostrunner (PPSA03685): device lost after 147 s", f"```\n{LOST}\n```", "2026-10-14T00:00:00Z"
                ),
                # Wobbly Life hit the same error line once, in an issue that is fixed and closed now
                issue(
                    11,
                    "Wobbly Life (PPSA29413): device loss under streaming",
                    f"On main:\n```\n{LOST}\n```",
                    "2026-10-11T00:00:00Z",
                    state="CLOSED",
                    reason="COMPLETED",
                ),
                # Wobbly Life's remaining stop, an open report without an error line
                issue(
                    12,
                    "Wobbly Life (PPSA29413): 3D view corrupts after map use",
                    "Wobbly Life (PPSA29413) on main: the 3D view corrupts after the map is opened three times.",
                    "2026-10-13T00:00:00Z",
                ),
                # a duplicate is closed without a fix: its error line still belongs to the open issue
                issue(
                    13,
                    "Ninja Game (PPSA11111): device lost",
                    f"On main:\n```\n{LOST}\n```",
                    "2026-10-15T00:00:00Z",
                    state="CLOSED",
                    reason="DUPLICATE",
                ),
                # an open issue for a depth-surface error, and a fixed issue whose thread reports that error as
                # the next stop: the next stop is not the fixed one, so it still points at the open issue
                issue(
                    20,
                    "AGC: storage image access to a depth/stencil surface",
                    f"```\nwhat():  {DEPTH_STORAGE}\n```",
                    "2026-10-01T00:00:00Z",
                ),
                {
                    **issue(
                        21,
                        "Epic Game (PPSA15657): a D16 depth surface sampled as a 32-bit texture",
                        "On main:\n```\nwhat():  AGC graphics: sampling the depth plane of depth surface 0x2 "
                        "(240x135, vk format 124) as a 120x135 texture is not implemented\n```",
                        "2026-10-05T00:00:00Z",
                        state="CLOSED",
                        reason="COMPLETED",
                    ),
                    "comments": [
                        {
                            "body": f"Epic Game (PPSA15657) after the fix, on main:\n```\nwhat():  {DEPTH_STORAGE}\n```",
                            "url": f"https://github.com/{REPO}/issues/21#issuecomment-1",
                            "createdAt": "2026-10-13T00:00:00Z",
                            "author": "tester",
                        }
                    ],
                },
            ],
            "prs": [],
            "discussions": [],
            "dependencies": {},
            "external_prs": {},
        }
        cls.model = Model(raw, {"blockers": [], "titles": [], "not_blockers": []}, REPO, NOW)

    def chain(self, tid):
        return [(s["blocker"], s["why"]) for s in self.model.titles[tid]["chain"]]

    def test_a_fixed_issues_error_line_does_not_point_at_another_open_issue(self):
        self.assertNotIn("10", [b for b, _ in self.chain("PPSA29413")])
        self.assertEqual(self.chain("PPSA29413")[0], ("11", "reported on this issue"))
        self.assertIn(("12", "reported on this issue"), self.chain("PPSA29413"))

    def test_the_open_issue_still_leads_for_its_own_title(self):
        self.assertEqual(self.chain("PPSA03685")[0], ("10", "latest recorded stop matches its signature"))

    def test_an_issue_closed_as_a_duplicate_still_points_at_the_open_one(self):
        self.assertEqual(self.chain("PPSA11111")[0], ("10", "latest recorded stop matches its signature"))

    def test_a_next_stop_reported_in_a_fixed_issue_still_counts(self):
        self.assertEqual(self.chain("PPSA15657")[0], ("20", "latest recorded stop matches its signature"))


if __name__ == "__main__":
    unittest.main()
