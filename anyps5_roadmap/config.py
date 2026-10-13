"""Constants shared by every stage of the pipeline: paths, upstream locations, stages."""

from __future__ import annotations

from pathlib import Path

SCHEMA_VERSION = 2  # 2: games[], identity{}, blocker counts by game
ROOT = Path(__file__).resolve().parent.parent  # the repository root
DATA = ROOT / "data"
CURATED = DATA / "blockers.json"
GAMES = DATA / "games.json"  # which title IDs are one game, by hand
CACHE = DATA / "cache" / "raw.json"

UPSTREAM = "boykopovar/AnyPS5"
PROJECT_REPO = "AlxcBTW/anyps5-roadmap"  # this repository: corrections are filed here
SITE_URL = "https://alxcbtw.github.io/anyps5-roadmap/"  # where the Roadmap workflow publishes site/
WINDOW_DAYS = 60
# Working-group threads outside the upstream repository that follow one title on a patched stack. Every report
# in them is read as off main (a stage with open PRs or patches), never as the stage; see AGENTS.md.
WORKING_GROUPS = ("AlxcBTW/AnyPS5#44",)  # Sword of the Sea (PPSA25344)
PROGRESS_URL = "https://boykopovar.github.io/AnyPS5/progress.json"
# The PlayStation title list (MIT): title ID, store concept, name, content ID and region of every PS5 and PS4 title
CATALOG_URL = "https://raw.githubusercontent.com/andshrew/PlayStation-Titles/main/PS5_Titles.tsv"
CATALOG_PS4_URL = "https://raw.githubusercontent.com/andshrew/PlayStation-Titles/main/PS4_Titles.tsv"
ARCHIVE_URL = "https://github.com/boykopovar/AnyPS5/discussions/2475#discussioncomment-18886410"
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

# What kind of game a title is (data/blockers.json title_tags): a fixed list, in display order
TAG_HELP = {
    "2D": "Played in two dimensions.",
    "3D": "Played in three dimensions.",
    "Shooter": "Shooting is the core of play, first or third person.",
    "Platformer": "Running and jumping between platforms.",
    "Racing": "Driving or racing.",
    "Sports": "A real sport, such as hockey, football or pool.",
    "Fighting": "Head-to-head fights.",
    "Puzzle": "Puzzles and logic.",
    "Horror": "Horror and survival horror.",
    "RPG": "Role-playing: a character grows through levels, skills or gear.",
    "Simulation": "Simulates a real activity or system.",
    "Strategy": "Planning and tactics, in real time or turn by turn.",
    # the broad genres last, so a row leads with the tags that tell games apart
    "Action": "Real-time combat and reflexes.",
    "Adventure": "Exploration and story.",
    "App": "Not a game: a media player, emulator, streaming client, store or tool.",
}
TAGS = list(TAG_HELP)
TAG_GROUPS = {"2D": "Dimension", "3D": "Dimension", "App": "Kind"}  # every other tag is a genre
