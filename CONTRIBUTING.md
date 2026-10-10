# Contributing

Thanks for helping. The map is only as good as its data, and its data comes from people who read the
AnyPS5 issues closely. There are three ways to help, smallest first:

1. **Data corrections** in `data/blockers.json`: a wrong stage, a missing blocker, a fix that landed.
2. **Mining rules** in `anyps5_roadmap/`: teach the miner to read a kind of sentence it gets wrong.
3. **Rendering** in `render_html.py`: the page itself.

Not sure where something belongs? Open an issue with one of the forms, or ask in
[Discussions](https://github.com/AlxcBTW/anyps5-roadmap/discussions). Look for issues labelled
[good first issue](https://github.com/AlxcBTW/anyps5-roadmap/labels/good%20first%20issue).

## Your first data fix in 5 minutes

A real example: the page listed LEGO Horizon Adventures (PPSA14632) with "Claimed Ingame, unverified ·
PR #2791". This is how such a claim gets settled.

1. **Open the source.** Click the claim's link. PR #2791 says: "PPSA14632 (LEGO Horizon Adventures),
   on my test branch (`main` db343a93 plus #1157, #425, #2699, #423/#1077 and local stand-ins needed to
   reach gameplay)". `gh pr view 1157 -R boykopovar/AnyPS5` and so on show those PRs are still open.
   Gameplay on a branch of open PRs and local stand-ins does not count, so the verdict is `suppressed`.
2. **Add a stage review** to `stage_reviews` in `data/blockers.json`:

   ```json
   {
     "title": "PPSA14632",
     "claim": "Ingame",
     "claim_url": "https://github.com/boykopovar/AnyPS5/pull/2791",
     "verdict": "suppressed",
     "quote": "PPSA14632 (LEGO Horizon Adventures), on my test branch (`main` db343a93 plus #1157, #425, #2699, #423/#1077 and local stand-ins needed to reach gameplay), steady state per 10 s:",
     "reason": "Gameplay was reached only on a test branch with five open PRs and local stand-ins."
   }
   ```

   `confirmed` and `downgraded` verdicts also need the `stage` that holds on `main`, with its own `url`.
3. **Check it:** `python3 roadmap.py --validate` names every rule a change breaks, with its place in
   the file. Then `python3 -m unittest discover -s tests`.
4. **Open a pull request.** CI runs the checks and posts a **Blocker map preview** in the job summary:
   the base branch and your branch, built from the same API snapshot, side by side. For this fix it
   shows one unverified claim fewer, and PPSA14632's claim going from Ingame to none. The built site is
   attached to the run as the `site-preview` artifact if you want to click through it.
5. **Merge.** Every push to `main` that touches `data/` rebuilds and deploys the page, so the fix is
   live a few minutes later.

The same steps work for blockers (`blockers[]`), the order in which they stop a game (`titles[]` →
`blockers`) and issues that are not blockers (`not_blockers[]`). [AGENTS.md](AGENTS.md) describes every
field.

## Evidence rules

These hold for every data change, and reviewers check them:

- **A public link for everything.** An issue, a comment or a PR. A stage without a public source is not
  added, however sure you are.
- **Never invent an ID.** No title ID, game name, issue number or stage from memory. Check numbers with
  `gh issue view N -R boykopovar/AnyPS5` (works for PRs too) and copy the exact state.
- **Only `main` counts.** A stage counts when it was reached on `main`, or on `main` plus PRs that are
  merged now. Hopes and plans, other emulators, negations ("crashes before the main menu"), loading
  steps ("loads story mode until …"), quotes about another title, and anything reached only on a branch
  with open PRs, local stand-ins, integration stacks or hacks do not count.
- **Quote, don't paraphrase.** A stage review carries the exact sentence it rests on.
- **Short and factual.** `why`, `note` and `reason` are one line, without adjectives or guesses about
  causes. No console dumps, keys or personal data.

## Mining rules

The miner reads text one line at a time (`anyps5_roadmap/mine.py`) and the model turns what it reads
into titles, blockers and chains (`anyps5_roadmap/model.py`). A rule change can move many games at
once, so:

- **Every rule comes with a fixture test.** Test the function directly (for example
  `stage_in("… boots to the title screen …", 0)` in `tests/test_roadmap.py`), and when the rule changes
  what the model builds, add the case to `tests/fixtures/raw.json` and assert on the model.
- **Prefer missing a stage to inventing one.** A rule that reads a stage it should not is worse than
  one that reads nothing; mined stages of Menus and up stay claims anyway.
- **Look at the preview.** The CI summary runs your rule over the real snapshot and lists every title
  whose stage, claim or chain changed. Read the list before asking for review.

Locally, after one live build: `python3 roadmap.py --offline --out build/before` on `main`, the same
with `--out build/after` on your branch, then
`python3 -m anyps5_roadmap.preview build/before build/after`.

## Rendering

`render_html.py` renders `site/index.html` from `site/roadmap.json` and nothing else. To rebuild only
the page: `python3 render_html.py build/site/roadmap.json build/site/index.html`.

The page has a settled design: monochrome, Geist and Geist Mono, one type scale (12, 13, 15, 17 and
22 px), color only in the coverage map, links as small muted text. A change should look like it was
always there. Before asking for review, check it in light and dark mode, at a desktop width and at
390 px, with the keyboard, and with JavaScript off (the page must still show everything).

## Setup and checks

```sh
python3 -m pip install -r requirements-dev.txt   # ruff, for lint and format only
ruff check . && ruff format --check .
python3 -m unittest discover -s tests
python3 roadmap.py --validate
```

The generator itself uses the Python standard library only; please keep it that way.

CI (`.github/workflows/ci.yml`) runs all of this on Python 3.11 for every pull request, forks included,
without secrets. A labeler adds `data-correction`, `mining` or `rendering` from the files you touch.

## Module map

| File | What it does |
|---|---|
| `roadmap.py` | Entry point; re-exports the package's names for tests and scripts |
| `anyps5_roadmap/cli.py` | Command line, `--validate`, the checks on `data/blockers.json` (`validate_curated`) |
| `anyps5_roadmap/config.py` | Paths, the upstream repository, stage names |
| `anyps5_roadmap/github.py` | `gh api` calls with retries |
| `anyps5_roadmap/collect.py` | GraphQL queries for issues, PRs and their threads; the raw cache |
| `anyps5_roadmap/mine.py` | Text rules: names (`name_before`, `name_after`), stages (`stage_in`), error lines (`signature_from`), references (`refs_in`, `closing_refs`) |
| `anyps5_roadmap/model.py` | `Model`: links, titles, blockers, chains, `best_stage`, `unverified_claim`, the ranking |
| `anyps5_roadmap/coverage.py` | HLE and ISA coverage from progress.json; PM4 packets from the driver sources |
| `anyps5_roadmap/assemble.py` | `roadmap.json`: stats, focus areas, help wanted, `KNOWN_GAPS` |
| `anyps5_roadmap/render_md.py` | `ROADMAP.md` and `llms.txt` |
| `anyps5_roadmap/preview.py` | The PR preview summary |
| `render_html.py` | `index.html` |
| `tests/` | Fixture tests; `tests/fixtures/raw.json` is a tiny upstream, `curated.json` a tiny curated file |

## Pull requests

- One topic per pull request, based on current `main`.
- Fill in the checklist in the template. It ends with **AI-assisted: yes / no**, the same line AnyPS5
  uses: say whether the change was written with AI assistance. You are responsible for every line
  either way.
- Merges are squash merges; the branch is deleted afterwards.

Everyone taking part follows the [code of conduct](CODE_OF_CONDUCT.md).
