# AGENTS.md: curating the AnyPS5 blocker map

This repo builds a generated roadmap for AnyPS5, the tool that ports PS5 executables to Linux and Windows. `roadmap.py` mines
GitHub issues and PRs of `boykopovar/AnyPS5`; `data/blockers.json` holds the facts that
mining gets wrong or cannot see. Curated facts always win over mined ones.

## Run it

```sh
python3 roadmap.py --upstream-checkout /path/to/AnyPS5            # live: gh api + git fetch
python3 roadmap.py --offline --upstream-checkout /path/to/AnyPS5  # rebuild from data/cache/
python3 roadmap.py --validate                                     # check data/blockers.json only
python3 -m unittest discover -s tests                             # fixture tests, no network
```

`gh` must be logged in (or `GH_TOKEN` set). A run lists every issue and PR in the window
(about 30 queries, 70 points), then reads comments, reviews, review threads and
cross-references only for threads whose `updatedAt` changed since `data/cache/threads.json`
was written. With an empty cache that is about 3,000 threads in 115 batched queries, and the
whole run costs about 190 points (4% of the hourly 5,000); with a warm cache it costs about
75. The Roadmap workflow keeps `data/cache` between runs. Check the budget with
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
| `name`, `engine`, `kind` | `kind` is `retail` or `homebrew`. |
| `paths` | Optional OS/GPU paths, e.g. `["Windows/NVIDIA", "Windows/AMD"]`, when a title stops at different places. |
| `blockers` | Ordered chain, first stop first: `{"id": "2783", "scope": ["Windows/NVIDIA"], "why": "…"}`. A step without `scope` applies to every path. Every `id` must exist in `blockers[]`. |
| `evidence` | Best stages seen: `{"stage", "os", "gpu", "build", "date", "url", "note"}`. `url` is required: a stage without a public source is not added, however sure you are. `build` says what was running: `main`, `main + #2054`, `main + local patches`. |

Stages, lowest to highest: Converts, Loads, Starts, First draw, Presents, Menus, Ingame,
Playable. Black frames and loading screens count as Presents. A menu that runs but stays
black is still Presents.

### Verification policy for stages

A stage of **Menus or higher** is what people screenshot and repeat, so a mined one never
counts on its own:

- `best_stage` holds only verified stages: curated entries, the maintainers'
  `COMPATIBILITY.md` (`upstream`), and mined stages below Menus. `best_stage.verified` is
  `false` only for that last kind.
- A mined stage of Menus or higher that nobody has reviewed becomes `unverified_claim`
  (`{stage, url, quote}`) when it is above the best verified stage. It is never sorted or
  ranked on, and it must never be reported as the title's stage.
- `confidence` counts distinct GitHub accounts whose own text puts a title at its stage on
  `main` ("2 reports on main" on the page), and separately those that reached the claimed
  stage only on PR branches or patched builds. It never turns a claim into a stage; only a
  `stage_reviews` entry does.
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
