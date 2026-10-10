"""Constants shared by every stage of the pipeline: paths, upstream locations, stages."""

from __future__ import annotations

from pathlib import Path

SCHEMA_VERSION = 1
ROOT = Path(__file__).resolve().parent.parent  # the repository root
DATA = ROOT / "data"
CURATED = DATA / "blockers.json"
CACHE = DATA / "cache" / "raw.json"

UPSTREAM = "boykopovar/AnyPS5"
PROJECT_REPO = "AlxcBTW/anyps5-roadmap"  # this repository: corrections are filed here
WINDOW_DAYS = 60
PROGRESS_URL = "https://boykopovar.github.io/AnyPS5/progress.json"
PM4_HEADER = "core/libs/prx/libSceAgcDriver/Execution/include/Pm4Opcodes.hpp"
PM4_SOURCE = "core/libs/prx/libSceAgcDriver/Execution/src/Pm4.cpp"
DRIVER_DIR = "core/libs/prx/libSceAgcDriver"
RAW_URL = "https://raw.githubusercontent.com/{repo}/main/{path}"

STAGES = ["Converts", "Loads", "Starts", "First draw", "Presents", "Menus", "Ingame", "Playable"]
# mined stages from here up need a hand review before they count as best_stage
VERIFY_FROM = STAGES.index("Menus")
STAGE_HELP = {
    "Converts": "The package unpacks and the relinker converts the executable.",
    "Loads": "All imports resolve and the ELF loads.",
    "Starts": "Guest code runs past startup.",
    "First draw": "The first GPU draw or dispatch executes.",
    "Presents": "Frames reach the screen (loading screens and black frames count).",
    "Menus": "A menu or title screen renders and responds.",
    "Ingame": "Gameplay is reached.",
    "Playable": "Playable from start to finish with minor issues.",
}
