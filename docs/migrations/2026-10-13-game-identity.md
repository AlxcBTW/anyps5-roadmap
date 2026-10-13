# Game identity migration

Before: roadmap.json of 2026-10-13T12:07:17Z (schema 1). After: roadmap.json of 2026-10-13T12:23:18Z (schema 2), built from the API snapshot of 2026-10-13T12:15:38Z.

Until now each title ID was its own entry and the page put two IDs together only when their names were spelled exactly alike, so “GTA V” and “Grand Theft Auto V” were two games. Now a game is one entity with all of its title IDs and aliases; how title IDs are matched is in [CONTEXT.md](../../CONTEXT.md) and `anyps5_roadmap/identity.py`. This report lists every merge, every renamed title, every game whose stage changed, and what is left for a person to decide.

## Counts

| | Before | After |
|---|---:|---:|
| Games on the page | 182 | 185 |
| Title IDs behind them | 189 | 195 |
| Games with more than one title ID | 6 | 10 |
| Title IDs folded into another game | 7 | 10 |
| Matches waiting for review | | 2 |

## Merges

10 games hold more than one title ID.

| Game | Title IDs | Names before | Why |
|---|---|---|---|
| Astro Bot | `PPSA21564` (US), `PPSA21567` (EU) | `PPSA21564`: Astro Bot; `PPSA21567`: Astro Bot | same PlayStation Store concept (10002684) |
| Blasphemous 2 | `PPSA13579` (EU), `PPSA13580` (US) | `PPSA13579`: Blasphemous 2; `PPSA13580`: Blasphemous II | same PlayStation Store concept (10007264) |
| Cult of the Lamb | `PPSA06464` (US), `PPSA06465` (EU) | `PPSA06464`: Cult of the Lamb; `PPSA06465`: Cult of the Lamb | same PlayStation Store concept (10004484) |
| Cyberpunk 2077 | `PPSA03974` (US), `PPSA04029` (EU) | `PPSA03974`: Cyberpunk 2077; `PPSA04029`: Cyberpunk 2077 | same PlayStation Store concept (234567) |
| Demon's Souls | `PPSA01341` (EU), `PPSA01342` (US) | `PPSA01341`: Demon's Souls; `PPSA01342`: Demon's Souls | same PlayStation Store concept (10000368) |
| Grand Theft Auto V | `PPSA04263` (EU), `PPSA04264` (US) | `PPSA04263`: Grand Theft Auto V; `PPSA04264`: GTA V | same PlayStation Store concept (201930) |
| Kena: Bridge of Spirits | `PPSA01746` (US), `PPSA01802` (EU) | `PPSA01746`: Kena: Bridge of Spirits; `PPSA01802`: Kena: Bridge of Spirits | same PlayStation Store concept (10001235) |
| Minecraft | `PPSA17221` (US), `PPSA19639` | `PPSA17221`: Minecraft; `PPSA19639`: Minecraft Preview | same PlayStation Store concept (212779) |
| Returnal | `PPSA01284` (US), `PPSA01285` (EU) | `PPSA01284`: Returnal; `PPSA01285`: Returnal | same PlayStation Store concept (10000176) |
| Stray | `PPSA02100` (US), `PPSA02101` (EU) | `PPSA02100`: Stray; `PPSA02101`: Stray | same PlayStation Store concept (10001114) |

## Renamed titles

12 listed title IDs show another name now: the store's own name for the ID, the name of the game it joined, or a correction of a mis-read name.

| Title ID | Before | After | Name from |
|---|---|---|---|
| `PPSA03647` | 3D MiniGolf | 3DMiniGolf | PlayStation title list |
| `PPSA03490` | Demon Slayer | Demon Slayer -Kimetsu no Yaiba- The Hinokami Chronicles | PlayStation title list |
| `PPSA14383` | Disney-Pixar WALL-E | Disney•Pixar WALL-E | PlayStation title list |
| `PPSA02070` | Don’t Starve Together | Don't Starve Together: Console Edition | PlayStation title list |
| `PPSA02262` | Dying Light 2 | Dying Light 2: Stay Human | PlayStation title list |
| `PPSA23566` | UFC 6 | EA SPORTS UFC 6 | PlayStation title list |
| `PPSA07645` | Fallen Legion | Fallen Legion: Rise to Glory | PlayStation title list |
| `PPSA04264` | GTA V | Grand Theft Auto V | PlayStation title list |
| `PPSA06699` | Hot Shots Golf 2 via PS1HD | Hot Shots Golf 2 | PlayStation title list |
| `PPSA33016` | Rayman: 30th Anniversary Edition | Rayman 30th Anniversary Edition | PlayStation title list |
| `PPSA05347` | Record of Lodoss War | Record of Lodoss War -Deedlit in Wonder Labyrinth- | PlayStation title list |
| `PPSA03061` | Void Terrarium | void tRrLM();++ //Void Terrarium++ | PlayStation title list |

## Stage changes

30 games show another stage. Stages count only on main, or on main plus PRs that are merged now, as the README and AGENTS.md always said; the old build counted any mined stage below Menus. A stage seen only on a PR branch, a stack of open PRs or local patches now shows apart, as the stage off main, with the PRs it needs, and moves up by itself once they are merged.

| Game | Before | After | Why |
|---|---|---|---|
| 2 Ship 2 Harkinian | Converts | no stage | the higher stage was reported only off main (open PRs or patches); stage off main now: Converts with #4553 |
| 7 Days to Die - Console Edition | Presents | no stage | the higher stage was reported only off main (open PRs or patches); stage off main now: Ingame with #4847 |
| Ape Escape | Starts | no stage | the higher stage was reported only off main (open PRs or patches); stage off main now: Starts with #572 + patches |
| Big Helmet Heroes | no stage | Starts | a newer report, or a report from a discussion |
| Commandos: Origins | Presents | no stage | the higher stage was reported only off main (open PRs or patches); a claim of Menus on main waits for review |
| Cult of the Lamb | Presents | Converts | the higher stage was reported only off main (open PRs or patches); stage off main now: Presents with #4652 |
| EmuStore | Converts | no stage | the higher stage was reported only off main (open PRs or patches); stage off main now: Converts with #3658 |
| Ghost of Yōtei | Starts | Presents | a newer report, or a report from a discussion |
| Goat Simulator 3 | Presents | Starts | the higher stage was reported only off main (open PRs or patches); stage off main now: Menus with #5016 |
| Gran Turismo 7 | Presents | Starts | the higher stage was reported only off main (open PRs or patches); stage off main now: Menus with #2589 + patches |
| Horizon Zero Dawn Remastered | Converts | no stage | the higher stage was reported only off main (open PRs or patches); stage off main now: Converts + patches |
| Killzone: Liberation | Starts | no stage | the higher stage was reported only off main (open PRs or patches); stage off main now: Menus + patches |
| Last of Us Part II Remastered | Starts | Converts | the higher stage was reported only off main (open PRs or patches); stage off main now: Starts with #3897, #3925, #3965 + patches |
| LEGO Party! | Presents | Converts | the higher stage was reported only off main (open PRs or patches); a claim of Menus on main waits for review |
| Marsupilami 2 - Salsa Palombia | Starts | no stage | the higher stage was reported only off main (open PRs or patches); stage off main now: Starts with #2558 |
| Metal Gear Solid Δ: Snake Eater | Presents | no stage | the higher stage was reported only off main (open PRs or patches); stage off main now: Presents with #4573 |
| NHL 27 | Starts | Presents | a newer report, or a report from a discussion |
| OpenRCT2 Native Port | Presents | Converts | the higher stage was reported only off main (open PRs or patches); stage off main now: Presents with #3664 |
| PS5CEMU-HAR | Converts | Presents | a newer report, or a report from a discussion |
| PS5SX2 | Presents | Starts | the higher stage was reported only off main (open PRs or patches); stage off main now: Presents with #4776 |
| Puyo Puyo Tetris 2 | Starts | no stage | the higher stage was reported only off main (open PRs or patches); stage off main now: Starts + patches |
| Rayman 30th Anniversary Edition | Loads | no stage | the higher stage was reported only off main (open PRs or patches); a claim of Menus on main waits for review |
| Silt | Converts | Starts | a newer report, or a report from a discussion |
| Skyrim | Starts | Converts | the higher stage was reported only off main (open PRs or patches); stage off main now: Starts with #1299 |
| Slay the Princess | Presents | First draw | the higher stage was reported only off main (open PRs or patches); stage off main now: Presents with #1359 |
| Spirit of the Island | Starts | no stage | the higher stage was reported only off main (open PRs or patches); stage off main now: Starts + patches |
| Sword of the Sea | Presents | Converts | the higher stage was reported only off main (open PRs or patches); stage off main now: Ingame with #1077, #2054 + patches |
| The Pathless | First draw | Starts | the higher stage was reported only off main (open PRs or patches); stage off main now: First draw with #4491, #4678 |
| Uncharted: Legacy of Thieves Collection | Starts | Presents | a newer report, or a report from a discussion |
| Vampire Survivors | Presents | Converts | the higher stage was reported only off main (open PRs or patches); a claim of Ingame on main waits for review |

## Waiting for review

Never merged by themselves. Settle one by listing the title IDs together in `data/games.json` (with a source), or keep them apart with a `distinct` entry.

| Kind | Names | Title IDs | Note |
|---|---|---|---|
| mined-name | Astro Bot / ASTRO BOT | `PPSA02158`, `PPSA21564` | PPSA02158 is not in the PlayStation title list; its mined name matches ASTRO BOT (PPSA21564). Merge it in data/games.json only with a source that ties the ID to the game. |
| mined-name | Cult of the Lamb / Cult Of The Lamb | `PPSA12338`, `PPSA06464` | PPSA12338 is not in the PlayStation title list; its mined name matches Cult Of The Lamb (PPSA06464). Merge it in data/games.json only with a source that ties the ID to the game. |

Placeholder IDs skipped: `PPSA00000`.
