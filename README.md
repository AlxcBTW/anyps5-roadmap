# AnyPS5 blocker map

[![CI](https://github.com/AlxcBTW/anyps5-roadmap/actions/workflows/ci.yml/badge.svg)](https://github.com/AlxcBTW/anyps5-roadmap/actions/workflows/ci.yml)
[![Pages](https://github.com/AlxcBTW/anyps5-roadmap/actions/workflows/roadmap.yml/badge.svg)](https://github.com/AlxcBTW/anyps5-roadmap/actions/workflows/roadmap.yml)

Which open issues stop which PS5 games in [AnyPS5](https://github.com/boykopovar/AnyPS5), the tool that ports PS5 executables to Linux and Windows,
ranked by how many games a fix would move, plus how much of the PS5's system libraries and GPU AnyPS5
implements.

**Live: <https://alxcbtw.github.io/anyps5-roadmap/>**. A merge to `main` goes live within minutes. Otherwise
GitHub's schedule rebuilds the page: an hourly build, and a check several times an hour that builds once an upstream
issue or PR changed and costs no API quota when nothing did (`.github/workflows/update-check.yml`). GitHub runs
schedules best effort and started both far less often than their cron asks, so the rebuilds come irregularly: in
mid-October 2026 about 1.7 hours apart at the median and at most about 5 hours apart
([#70](https://github.com/AlxcBTW/anyps5-roadmap/issues/70) has the details).

A community project, not an official AnyPS5 page. Every stage and link on it comes from public GitHub
data and links its source.

![The blocker map in dark mode: a short intro with four numbers and a game search, then the list of games, each with its cover, its stage, how sure that stage is, and the issue that stops it](docs/screenshot.png)

## How it works

```text
  boykopovar/AnyPS5 on GitHub                          data/blockers.json, data/games.json
  issues, PRs, discussions, comments, reviews          curated by people; always wins
          |                                                     |
          | gh api graphql, only what changed                   |
          v                                                     |
  data/cache/raw.json --> mine.py ----------> model.py <--------+
                          keyword rules        titles, blockers, chains
                          per line                  |
  PlayStation title list ---------------> identity.py: title IDs -> games (merges, review list)
                                                    |
                                          evaluate.py: stage, confidence, stage history per game
                                                    |
  store pages, Wikidata ----------------> images.py: a cover URL per game (never the image)
                                                    |
  progress.json, COMPATIBILITY.md, PM4 sources --> coverage.py, assemble.py
                                                    |
                                                    v
            site/roadmap.json, feed.json --> the web app (web/), classic.html, ROADMAP.md, llms.txt
                                          |
                                          v
  the live roadmap.json, feed.json --> feed.py --> site/feed.json (last 50 items)
```

1. **Mine.** `collect.py` reads the upstream issues, PRs and discussions of the last 60 days (all open
   ones) with their comments, replies, reviews, review threads and cross-references. Each run lists only
   what changed since the last one and reads only the threads that changed, within a GraphQL budget.
   `mine.py` reads title IDs, game names, stages, OS, GPU, the build (main, main plus named PRs, or
   patches), the author and error lines from that text, one line at a time, plus the last error line of
   a fenced log and the "Furthest point" of a Game bring-up discussion form. A quoted line is not the
   quoter's report, and a report posted twice counts once.
2. **Group.** `identity.py` puts the title IDs of one game together: by a person's word
   (`data/games.json`), by the PlayStation Store's (one store concept), or when their names agree once
   spelling, symbols, editions and short forms such as GTA are set aside. Anything less certain goes to a
   review list instead. `images.py` finds each game's cover on the PlayStation Store or Steam CDN;
   [docs/images.md](docs/images.md) has the sources and terms.
3. **Curate.** `data/blockers.json` holds what mining gets wrong or cannot see: blockers, the order in
   which they stop each game, and hand reviews of mined stages. A curated fact always wins.
4. **Render.** `assemble.py` writes `site/roadmap.json`. The page, `ROADMAP.md` and `llms.txt` are
   rendered from that file alone, so people and tools see the same data. `feed.py` compares it with
   the `roadmap.json` that is live before the deploy and adds what changed to `feed.json`.

The code is in [`anyps5_roadmap/`](anyps5_roadmap/); [CONTRIBUTING.md](CONTRIBUTING.md#module-map)
has a module map.

## Run it locally

Python 3.11 or newer; nothing to install. On Windows, use `py -3` for `python3`.

```sh
git clone https://github.com/AlxcBTW/anyps5-roadmap && cd anyps5-roadmap
python3 -m unittest discover -s tests                     # fixture tests, no network
python3 roadmap.py --offline --no-network --cache tests/fixtures/raw.json --curated tests/fixtures/curated.json --games tests/fixtures/games.json --out build/site
gh auth login                                             # only for live data
python3 roadmap.py --out build/site                       # live build; open build/site/classic.html
cd web && npm ci && npm run dev                           # the app (Node 24) at http://localhost:5173
```

The live build needs the [GitHub CLI](https://cli.github.com/) and saves what it fetched in
`data/cache/`. After that, `python3 roadmap.py --offline --out build/site` rebuilds from the cache in
seconds, which is the quick way to try a change to `data/blockers.json`. Add
`--upstream-checkout <path to an AnyPS5 clone>` for the PM4 coverage line.

## The data, in short

- **Stages**, lowest to highest: Converts, Loads, Starts, First draw, Presents, Menus, Ingame,
  Playable. A stage counts only when it was reached on AnyPS5 `main`, or on `main` plus PRs that are
  merged now.
- **Games** hold all of their title IDs (PPSA for PS5, CUSA for PS4; region variants share a game) and
  aliases ("GTA V" for Grand Theft Auto V). Each has a `stage` (qualifying reports only), a `confidence`
  (checked by hand, or how many different people report that stage on `main`: a count, not a
  verification), an `unverified_claim` (a mined Menus or higher on main that nobody has reviewed yet;
  never ranked on), a `stage_on_branches` (how far it gets with open PRs or local patches, and the PRs
  it needs; never ranked on), its `open_blockers` in the order they stop it, a `timeline` of the dates its stage rose,
  and a cover `image` linked from the PlayStation Store or Steam. `identity` lists every merge with its
  reasons, and the matches waiting for review.
- **Titles** (one per title ID) keep the same fields for that ID alone and name their `game`.
- **Blockers** are upstream issues, PRs (`pr-N`) or crash sites listed in a tracker issue (`N~symbol`).
  Each has its fix PRs and a score: `3 × one_fix_away + 2 × frontier + total` (games for which it is
  the only open stop, the first open stop, or any stop; a game counts once, whatever its title IDs).
- **`origin`** says where a fact comes from: `curated` (data/blockers.json), `upstream`
  (COMPATIBILITY.md), `github` (native "blocked by" links) or `mined` (text rules).
- **Changes** are in [feed.json](https://alxcbtw.github.io/anyps5-roadmap/feed.json), a
  [JSON Feed 1.1](https://www.jsonfeed.org/version/1.1/) that feed readers can follow. Each snapshot
  that changed something adds one item: blockers resolved, blockers that enter, leave or move in the
  ranking, games whose stage or first open blocker changed, and games that took in another title ID, each
  linked on the page. The feed keeps
  the last 50 items, so a reader that checks every few hours misses nothing.

Every field is described in [AGENTS.md](AGENTS.md) and in the published
[llms.txt](https://alxcbtw.github.io/anyps5-roadmap/llms.txt).

## Correct an entry

- **On the page:** each game and each blocker opens a panel with a "Report a correction" link. It opens an issue
  form with the title ID, the stage on the page and its source already filled in.
- **As a pull request:** edit `data/blockers.json`, or `data/games.json` to join or separate the title
  IDs of a game. [CONTRIBUTING.md](CONTRIBUTING.md) walks through a first data fix in five minutes. CI shows what the change does to the ranking and the stages, and the
  page is rebuilt a few minutes after the merge.

Bugs in AnyPS5 itself belong in [AnyPS5's issues](https://github.com/boykopovar/AnyPS5/issues).

## Known limits

- Mining reads text with keyword rules, one line at a time. Negations and context are handled only
  roughly, so a stage of Menus or higher stays an unverified claim until someone reviews it.
- The order of mined blockers is a heuristic: the latest recorded stop first, then issues by date.
- Reports that only exist on Discord are invisible until someone copies them to GitHub.
- Titles without a PPSA or CUSA ID (some homebrew) appear only when curated.
- A homebrew app without a title ID of its own shows its initials instead of a cover.

The full list, as of the last build, is under "Known gaps in the data" in the page's Data view and in
`roadmap.json` → `gaps`.

## License

The code is under the [MIT license](LICENSE). Text quoted on the page and in the data (issue titles,
sentences, error lines) belongs to its authors in the upstream repository; it is quoted with a link to
its source and is not relicensed. Game covers are not stored here: the page links them where the
PlayStation Store and Steam publish them, and they belong to their publishers ([docs/images.md](docs/images.md)).
The PlayStation title list is [andshrew/PlayStation-Titles](https://github.com/andshrew/PlayStation-Titles)
(MIT). The Geist fonts are under the SIL Open Font License
([site/fonts/OFL.txt](site/fonts/OFL.txt)).

Not affiliated with the AnyPS5 project or with Sony Interactive Entertainment. PlayStation and PS5 are
trademarks of Sony Interactive Entertainment.

Contributions follow the [code of conduct](CODE_OF_CONDUCT.md).
