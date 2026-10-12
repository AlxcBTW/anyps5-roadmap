# Context: the AnyPS5 blocker map

The words the map, its data and its code use. AGENTS.md describes every field of the data; this file
says what the words mean.

## Language

**AnyPS5**:
The tool that ports PS5 executables to Linux and Windows.
_Avoid_: emulator

**Title ID**:
One PS5 title ID (`PPSA` + five digits). The data has one entry per title ID.
_Avoid_: game, when the region matters

**Game**:
All title IDs that share a name, counted once. The map counts games, not title IDs, wherever it
counts.
_Avoid_: title, when counting

**Stage**:
How far a title gets on AnyPS5 `main`, lowest to highest: Converts, Loads, Starts, First draw,
Presents, Menus, Ingame, Playable.

**Best stage**:
The highest stage verified for a title: curated, from the maintainers' compatibility list, or mined
below Menus. The only stage that is shown, counted or sorted on.

**Unverified claim**:
A mined stage of Menus or higher that nobody has reviewed yet. Shown as a claim, never as the stage.
_Avoid_: stage

**Stage review**:
A person's verdict on a claim (confirmed, downgraded or suppressed), with the sentence it rests on.

**Blocker**:
An open problem upstream (an issue, a PR, or a row of a tracker issue) that stops at least one title,
or could.
_Avoid_: bug, ticket

**Stop**:
A place where a title stops. A title's stops form an ordered **chain**; the first one is where it stops
now.

**Path**:
An OS and GPU combination (`Windows/NVIDIA`) on which a stop applies. A stop without a path applies to
every path.

**First stop**:
A blocker is the first stop of a game when it is the first open stop on at least one path. Fixing it
moves that game forward.
_Avoid_: unblocks, which promises more than the data knows

**Only stop**:
A blocker is the only stop of a game when no other open stop is known on that path.

**Score**:
3 × games for which a blocker is the only stop + 2 × games it stops first + every game that lists it.
The **rank** orders blockers by score.

**Fix status**:
What the fix PRs of a blocker say: fix in review (one is open), partly fixed (one is merged with a
note), fix closed unmerged, no fix yet, or fixed.

**Fix in review**, **No open fix**, **Fixed**:
The status filters of the blocker list. Fix in review: open blockers with an open fix PR. No open fix:
open blockers without one, best ranked first. Fixed: blockers resolved in the window.

**Snapshot**:
One build of the map from GitHub data, named by when it ran. The **window** is how far back a snapshot
reads closed issues and PRs (60 days).

**Change**:
What one snapshot changed against the one before: a blocker resolved, a blocker entering, leaving or
moving in the ranking, or a title whose best stage or first stop changed.

**Coverage**:
How much of the PS5's system library functions, GPU shader instructions and GPU command packets
AnyPS5 implements.

**Curated**:
Written by a person in `data/blockers.json`, with a public source. Curated facts win over **mined**
ones, which keyword rules read from issue and PR text.
