# AGENTS.md: curating the AnyPS5 blocker map

This repo builds a generated roadmap for AnyPS5, the tool that ports PS5 executables to Linux and Windows. `roadmap.py` mines
GitHub issues, PRs and discussions of `boykopovar/AnyPS5`; `data/blockers.json` holds the facts
that mining gets wrong or cannot see, and `data/games.json` says which title IDs are one game where
the automatic matching cannot. Curated facts always win over mined ones.

## Run it

```sh
python3 roadmap.py --upstream-checkout /path/to/AnyPS5            # live: gh api + git fetch
python3 roadmap.py --offline --upstream-checkout /path/to/AnyPS5  # rebuild from data/cache/
python3 roadmap.py --validate                                     # check data/blockers.json and data/games.json
python3 -m unittest discover -s tests                             # fixture tests, no network
cd web && npm ci && npm run dev                                   # the page, over site/roadmap.json
```

`gh` must be logged in (or `GH_TOKEN` set). A run lists only the issues, PRs and discussions
updated since the last run (`data/cache/listing.json`; a full listing once a week, about 110
points), then reads comments, reviews, review threads, discussion replies and cross-references only
for threads whose `updatedAt` changed (`data/cache/threads.json`). With an empty cache that is about
4,800 threads and 220 points; an hourly run with a warm cache costs about 20. Below a reserve of 500
points the thread pass stops and the rest waits for the next run (`api.partial` in raw.json). REST
calls and downloads are revalidated with their ETag (`etags.json`, `*.meta.json`). The Roadmap
workflow keeps `data/cache` between runs. Check the budget with
`gh api graphql -f query='{ rateLimit { remaining resetAt } }'` (the REST `rate_limit`
view of the graphql bucket lags behind). No search API calls; do not add any in loops.

## What to curate

Add an entry only when you can link a public source for it (an issue, a comment, a PR).
Before adding a number, check it: `gh issue view N -R boykopovar/AnyPS5` (works for PRs
too) and copy the exact state. Never invent a PPSA ID, a title name or a stage.

### Blockers (`blockers[]`)

| Field | Meaning |
|---|---|
| `id` | Upstream issue number as a string (`"2548"`). For a blocker that only exists as a PR, `pr-N`. Otherwise a short slug (`siglongjmp`). Unique. |
| `issue` | Upstream issue number, or `null`. |
| `title` | One short line, sentence case. |
| `signature` | The error line as logged, e.g. `AGC graphics: color views of several array slices are unsupported` or `FAIL: unresolved ELF import JZKw5+Wrnaw (pthread_sigmask) from libkernel`. Used to match title stops to this blocker; hex addresses and long numbers are masked automatically. |
| `area` | `shader`, `agc`, `libkernel`, `libc`, `relinker` or `prx`. |
| `fix_prs` | PRs that fix it: `{"number": 454}` upstream, `{"repo": "Owner/AnyPS5", "number": 25, "note": "partial: …"}` for forks. A `note` keeps a merged PR from marking the blocker resolved. A fix PR closed without merge is followed by the PR that resubmits or carries it ("This is #1872 again", "Resubmission of #2174", "Replaces #2481", "Supersedes #1855", "Carries #2738", "Carried from #2909"), and a fork fix PR by the PR that carries it ("Carries AlxcBTW/AnyPS5#26"); that PR joins as a mined fix PR, so it needs no entry here. |
| `related_prs` | PRs worth knowing about that do not fix it. |
| `status` | Optional override: `open` or `resolved`. Without it, the issue state decides; a PR-only blocker is resolved when a fix PR without a note is merged. |
| `next` | The next concrete step, one sentence. |
| `help_wanted` | What an outside contributor could do. Shows up under Help wanted. |
| `sources` | Links that back the entry. |

### Titles (`titles[]`)

| Field | Meaning |
|---|---|
| `id` | PS5 title ID, `PPSA` + 5 digits. One entry per region ID. |
| `name`, `engine`, `kind` | `kind` is `retail` or `homebrew`. `name` wins over the PlayStation title list and every mined name. |
| `name_sources` | Public links that tie this title ID to `name`: its PlayStation Store product, `https://prosperopatches.com/PPSA…`, serialstation, or the upstream issue text that says so. Required in practice whenever `name` replaces another name (the validator checks the links are https and that a name exists). A title ID in the PlayStation title list already has the store's name, so a curated name is needed only for IDs the list lacks (homebrew), for a homebrew app on a retail ID, or to correct the list; never write a name you only know from memory. |
| `paths` | Optional OS/GPU paths, e.g. `["Windows/NVIDIA", "Windows/AMD"]`, when a title stops at different places. |
| `blockers` | Ordered chain, first stop first: `{"id": "2783", "scope": ["Windows/NVIDIA"], "why": "…"}`. A step without `scope` applies to every path. Every `id` must exist in `blockers[]`. |
| `evidence` | Best stages seen: `{"stage", "os", "gpu", "build", "date", "url", "note"}`. `url` is required: a stage without a public source is not added, however sure you are. `build` says what was running: `main`, `main + #2054`, `main + local patches`. |
| `excluded` | Blockers the miner attaches to this title that do not hold: `{"id": "3369", "why": "…"}`. The step is dropped from the chain and from the blocker's title counts. Use it only after reading the source; a wrong match caused by a mining rule is fixed in the rule. |

Stages, lowest to highest: Converts, Loads, Starts, First draw, Presents, Menus, Ingame,
Playable. Black frames and loading screens count as Presents. A menu that runs but stays
black is still Presents.

### Verification policy for stages

A stage of **Menus or higher** is what people screenshot and repeat, so a mined one never
counts on its own:

- `best_stage` holds only qualifying stages: curated entries, the two archived reports of the removed
  `COMPATIBILITY.md` (curated, see `ARCHIVE_URL`), and mined stages below Menus from a run on `main` or on
  `main` plus PRs that are merged now. `best_stage.verified` is `false` only for that last kind. Each mined
  report has a `build_kind`: `main`, `prs` (main plus the PRs in `prs`: a PR's own branch or "with #3497";
  it counts once all of them are merged) or `patched` (local patches, a fork, a hack or someone's branch;
  it never counts). A mined report older than the newest curated fact about the same game is superseded.
- A mined stage of Menus or higher, reported on `main` (or `main` plus merged PRs), that nobody
  has reviewed becomes `unverified_claim` (`{stage, url, quote, build}`) when it is above the best
  verified stage. It is never sorted or ranked on, and it must never be reported as the title's stage.
- The furthest stage reported off main (a PR's branch, `main` plus open PRs, local patches, a
  working group's stack) becomes `stage_on_branches` (`{stage, url, quote, needs, patches,
  confidence}`) when it is above both. `needs` lists the open upstream PRs it ran with, `patches`
  says it also had changes no PR carries. It is the "what is needed to get there" view: shown
  apart, never sorted or ranked on, never the stage. Once its PRs are merged, the same report
  qualifies and the stage (or the claim) moves up by itself.
- Working-group threads outside upstream (`WORKING_GROUPS` in `anyps5_roadmap/config.py`, now the
  Sword of the Sea group, AlxcBTW/AnyPS5#44) are read as off main only. In such a thread, a line
  that names the title (or its initials, "SotS") counts for it even without the title ID; its
  upstream PRs are the ones the opening post's recipe names, or the ones the line names.
- `confidence` counts distinct GitHub accounts whose own text puts a title at its stage on
  `main` ("2 reports on main" on the page), and separately those that reached the claimed
  stage only on PR branches or patched builds. Its `level` is `verified` (curated), `corroborated`
  (two or more accounts), `reported` (one) or `none`. It never turns a claim into a stage; only a
  `stage_reviews` entry does. A blockquote (`> …`) repeats someone else's words and is not the
  quoter's report, and the same sentence posted in several threads counts once.
- To settle a claim, open the source (body, comments, linked screenshots and logs) and add
  a `stage_reviews` entry.

What counts: the stage was reached on `main`, or on `main` plus PRs that are merged now.
What does not count: hopes and plans, other emulators, negations ("crashes before the main
menu", "nothing was tested in-game"), loading steps ("loads story mode until …"), quotes about
another title, and anything reached only on a branch with open PRs, local stand-ins,
integration stacks or hacks.

### Stage reviews (`stage_reviews[]`)

| Field | Meaning |
|---|---|
| `title` | PPSA ID. |
| `claim`, `claim_url` | The mined stage and the source it was mined from (PR, issue or comment URL). Mined stages from that source are dropped for this title. |
| `verdict` | `confirmed`, `downgraded` or `suppressed`. |
| `stage`, `os`, `gpu`, `build`, `date`, `url` | For `confirmed` and `downgraded`: the stage that holds on main and its own source, which may differ from `claim_url`. |
| `quote` | The exact sentence the verdict rests on. Required. |
| `reason` | One line on why, e.g. "reached only on an integration branch of open PRs". |

### Games (`data/games.json`)

A game is one entity with all of its title IDs. The build joins title IDs by itself when the PlayStation
title list ([andshrew/PlayStation-Titles](https://github.com/andshrew/PlayStation-Titles)) puts them under
one store concept, or when their names agree after normalising case, ™ ® ©, punctuation, accents, a leading
"The", region, platform and edition suffixes, roman numerals (V = 5) and known short forms (GTA, RE, CoD,
TLOU, GT, GoW, FF, MGS, RDR, …; `ABBREVIATIONS` in `anyps5_roadmap/identity.py`), as long as both names are
trusted (curated or from the store list) or both are mined. Every merge is listed with its reasons in
`roadmap.json` → `identity.merges`. Weaker matches land in `identity.review` and are never merged by
themselves. Settle them here:

| Field | Meaning |
|---|---|
| `games[]` | `{"name", "title_ids", "aliases", "image", "sources"}`: these title IDs are one game. `name` (optional) is the canonical name; `aliases` are other ways it is written, for the search; `image` is `{"url", "page", "source"}` for a cover, or `null` for none; `sources` (required) are public links that tie the IDs and the name together. A title ID belongs to one game only. |
| `distinct[]` | `{"title_ids": [...], "reason"}`: these title IDs are different games. They are never merged with each other, and the review list stops listing them. |

Add an entry only with a source: a store page for each ID, a release note, or the homebrew's README. A
review item is settled by one of the two; leaving it open is fine.

### Not blockers (`not_blockers[]`)

`{"issue": 2749, "reason": "…"}` keeps a mined issue out of the ranking, e.g. a title
report whose real stop is another issue.

### Tags (`title_tags[]`)

What kind of game a title is, for the tag filter on the page. One entry per title ID:

| Field | Meaning |
|---|---|
| `title` | PPSA ID. Tags follow the ID: a re-mine that renames the title keeps them, and an entry for a title outside the window waits until it is back. |
| `name` | The name the sources were matched on. |
| `tags` | From the fixed list (`TAG_HELP` in `anyps5_roadmap/config.py`): `2D`, `3D`; `Shooter`, `Platformer`, `Racing`, `Sports`, `Fighting`, `Puzzle`, `Horror`, `RPG`, `Simulation`, `Strategy`, `Action`, `Adventure`; `App` for anything that is not a game (player, emulator, client, store, tool, demo). `App` takes no other tag; `2D` and `3D` exclude each other, so when sources disagree, use neither. |
| `sources` | The public pages the tags come from. |

A tag needs a source that names it. No source, no entry; never tag a game from what you know about it.

- **Match conservatively.** The source's name must equal the title's name, ignoring case, punctuation,
  ™ and ®, a leading "The" and a "PS4 & PS5" suffix, and its platform must include PS5. Where the title
  ID's own name is known (its PlayStation Store product, or `https://prosperopatches.com/PPSA…`), it must
  name the same game, an edition suffix aside. A mined name that belongs to another game ("Retried" on
  the ID of Dragon Quest III HD-2D Remake) gets nothing until the name is fixed.
- **Wikidata**, genre (P136): platformer → Platformer; 2D platform game → 2D, Platformer; Metroidvania →
  2D, Platformer, Action, Adventure; first- or third-person shooter → Shooter; action-adventure → Action,
  Adventure; action RPG and soulslike → Action, RPG; tactical RPG → RPG, Strategy; survival,
  psychological, body or cosmic horror → Horror; management or flight simulation → Simulation; pool →
  Sports. Themes (science fiction, fantasy), roguelike, survival, sandbox, stealth, casual and party
  give nothing.
- **PlayStation Store**, the genres of the product with this title ID, else of the item's store concept:
  Driving/Racing → Racing, Role Playing Games → RPG, Sport → Sports, Simulator → Simulation, the others by
  name. Unique, Family, Arcade, Casual and Party give nothing.
- **SteamSpy**, user tags of the item's Steam app (Wikidata P1733) with at least a third of the votes of
  its top tag, for 2D, 3D, Shooter and Platformer only (2D Platformer, FPS and Third-Person Shooter
  count). Its broader tags are votes on mood (Horror on a puzzle game) and are not used.
- **Homebrew**: the README, or the repository description, of the homebrew itself. "VLC media player" is
  App and "a native puzzle collection" is Puzzle; a port whose README names no genre gets nothing.

## Ranking

A game's chain is the chain of its leading title ID (the furthest one), followed by the steps only its other
title IDs know; it is split into its OS/GPU paths. Per blocker, counted by game:

- `frontier`: games where it is the first open step on at least one path
- `one_fix_away`: games where it is the only open step on at least one path
- `total`: games that list it anywhere
- `score = 3 * one_fix_away + 2 * frontier + total`

Games whose stage is Playable only count toward `total`. `games`, `frontier_games` and `one_fix_games`
list the games; `titles`, `frontier_titles` and `one_fix_titles` the title IDs behind them.

## Rules for agents

- Mark nothing as curated that you only inferred. Leave it to mining, or ask.
- Keep `why` and `note` short and factual. No adjectives, no guesses about causes.
- Do not copy console dumps, keys or personal data into this repo.
- After editing, run the tests and an offline build, then read the diff of `site/ROADMAP.md`.
- The page (`web/`) reads `roadmap.json` in the browser. A data fix needs no change there, and nothing
  built (`site/index.html`, `site/assets/`, `web/dist/`) is edited by hand.
