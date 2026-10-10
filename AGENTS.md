# AGENTS.md: curating the AnyPS5 blocker map

This repo builds a generated roadmap for the AnyPS5 PS5 emulator. `roadmap.py` mines
GitHub issues and PRs of `boykopovar/AnyPS5`; `data/blockers.json` holds the facts that
mining gets wrong or cannot see. Curated facts always win over mined ones.

## Run it

```sh
python3 roadmap.py --upstream-checkout /path/to/AnyPS5            # live: gh api + git fetch
python3 roadmap.py --offline --upstream-checkout /path/to/AnyPS5  # reuse data/cache/raw.json
python3 -m unittest discover -s tests                             # fixture tests, no network
```

`gh` must be logged in (or `GH_TOKEN` set). A full run costs about 35 GraphQL points and
a few REST calls; check `gh api rate_limit` first. Do not use the search API in loops.

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
| `fix_prs` | PRs that fix it: `{"number": 454}` upstream, `{"repo": "Owner/AnyPS5", "number": 25, "note": "partial: …"}` for forks. A `note` keeps a merged PR from marking the blocker resolved. |
| `related_prs` | PRs worth knowing about that do not fix it. |
| `status` | Optional override: `open` or `resolved`. Without it, the issue state decides; a PR-only blocker is resolved when a fix PR without a note is merged. |
| `next` | The next concrete step, one sentence. |
| `help_wanted` | What an outside contributor could do. Shows up under Help wanted. |
| `sources` | Links that back the entry. |

### Titles (`titles[]`)

| Field | Meaning |
|---|---|
| `id` | PS5 title ID, `PPSA` + 5 digits. One entry per region ID. |
| `name`, `engine`, `kind` | `kind` is `retail` or `homebrew`. |
| `paths` | Optional OS/GPU paths, e.g. `["Windows/NVIDIA", "Windows/AMD"]`, when a title stops at different places. |
| `blockers` | Ordered chain, first stop first: `{"id": "2783", "scope": ["Windows/NVIDIA"], "why": "…"}`. A step without `scope` applies to every path. Every `id` must exist in `blockers[]`. |
| `evidence` | Best stages seen: `{"stage", "os", "gpu", "build", "date", "url", "note"}`. `build` says what was running: `main`, `main + #2054`, `main + local patches`. |

Stages, lowest to highest: Converts, Loads, Starts, First draw, Presents, Menus, Ingame,
Playable. Black frames and loading screens count as Presents. A menu that runs but stays
black is still Presents.

### Not blockers (`not_blockers[]`)

`{"issue": 2749, "reason": "…"}` keeps a mined issue out of the ranking, e.g. a title
report whose real stop is another issue.

## Ranking

For every title the chain is split into its OS/GPU paths. Per blocker:

- `frontier`: titles where it is the first open step on at least one path
- `one_fix_away`: titles where it is the only open step on at least one path
- `total`: titles that list it anywhere
- `score = 3 * one_fix_away + 2 * frontier + total`

Titles whose best stage is Playable only count toward `total`.

## Rules for agents

- Mark nothing as curated that you only inferred. Leave it to mining, or ask.
- Keep `why` and `note` short and factual. No adjectives, no guesses about causes.
- Do not copy console dumps, keys or personal data into this repo.
- After editing, run the tests and an offline build, then read the diff of `site/ROADMAP.md`.
