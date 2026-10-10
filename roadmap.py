#!/usr/bin/env python3
"""Technical roadmap / blocker map generator for AnyPS5 (community prototype).

Collects upstream issues and PRs through `gh api`, merges them with the curated
facts in data/blockers.json, measures HLE / RDNA ISA / PM4 coverage and writes
site/roadmap.json, site/ROADMAP.md, site/index.html, site/llms.txt and
site/AGENTS.md.

Standard library only. Needs the GitHub CLI (`gh`) on PATH; in Actions it reads
GH_TOKEN / GITHUB_TOKEN from the environment.

This file is the entry point; the code lives in the anyps5_roadmap package
(see CONTRIBUTING.md for the module map). The names below are re-exported so
`import roadmap` keeps working for tests and scripts.
"""

from __future__ import annotations

import sys

import render_html
from anyps5_roadmap.assemble import KNOWN_GAPS, assemble, focus_areas
from anyps5_roadmap.cli import load_curated, main
from anyps5_roadmap.collect import collect
from anyps5_roadmap.config import SCHEMA_VERSION, STAGES, VERIFY_FROM
from anyps5_roadmap.coverage import build_coverage, parse_pm4_opcodes, parse_unsupported_reason
from anyps5_roadmap.mine import (
    clean_name,
    closing_refs,
    compute_nid,
    name_after,
    name_before,
    refs_in,
    signature_from,
    signature_key,
    signatures_in,
    stage_in,
)
from anyps5_roadmap.model import Model
from anyps5_roadmap.render_md import render_llms, render_markdown
from anyps5_roadmap.upstream import Upstream

__all__ = [
    "KNOWN_GAPS",
    "SCHEMA_VERSION",
    "STAGES",
    "VERIFY_FROM",
    "Model",
    "Upstream",
    "assemble",
    "build_coverage",
    "clean_name",
    "closing_refs",
    "collect",
    "compute_nid",
    "focus_areas",
    "load_curated",
    "main",
    "name_after",
    "name_before",
    "parse_pm4_opcodes",
    "parse_unsupported_reason",
    "refs_in",
    "render_html",
    "render_llms",
    "render_markdown",
    "signature_from",
    "signature_key",
    "signatures_in",
    "stage_in",
]

if __name__ == "__main__":
    sys.exit(main())
