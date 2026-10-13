# Context: the AnyPS5 blocker map

The words the map, its data and its code use. AGENTS.md describes every field of the data; this file
says what the words mean.

## Language

**AnyPS5**:
The tool that ports PS5 executables to Linux and Windows.
_Avoid_: emulator

**Title ID**:
One PlayStation title ID: `PPSA` + five digits for PS5, `CUSA` + five digits for PS4. Each region release
of a game has its own.
_Avoid_: game, when the region matters

**Game**:
One entity with a canonical name, all of its title IDs and its aliases. The map counts games, not title
IDs, wherever it counts, and a game's stage rests on the reports of all of its title IDs.
_Avoid_: title, when counting

**Region variant**:
Another title ID of the same game, sold in another region (`PPSA04263` in Europe, `PPSA04264` in the US).

**Alias**:
Another way a game's name is written: a short form ("GTA V"), another spelling or another script.

**Store concept**:
The PlayStation Store's product page for a game, which groups its region variants. Title IDs of one
concept are one game.

**Merge**:
Title IDs joined into one game, with the reasons it rests on: a person's word, one store concept, or
names that agree once spelling, symbols, editions and abbreviations are set aside.

**Review list**:
Matches that may be one game but are not certain enough to merge: a mined name that equals a listed
game's, a name that is another one minus its subtitle or that starts it, a near spelling, or a homebrew
app on a retail title ID. A person settles each one.
_Avoid_: duplicate, which presumes the answer

**Tag**:
What kind of game a title is, from a fixed list: 2D or 3D, a genre such as Shooter or Platformer, or App
for anything that is not a game. Every tag has a public source; a game without tags is unknown, not
untyped.
_Avoid_: category, genre (2D, 3D and App are not genres)

**Stage**:
How far a title gets on AnyPS5 `main`, lowest to highest: Converts, Loads, Starts, First draw,
Presents, Menus, Ingame, Playable.

**Qualifying report**:
A report that can set a stage: curated, or mined below Menus from a run on `main` or on `main` plus PRs
that are merged now. Runs on branches with open PRs, local patches, forks or hacks never qualify.

**Best stage**:
The highest stage of the qualifying reports of a title or a game. The only stage that is shown, counted
or sorted on.

**Unverified claim**:
A mined stage of Menus or higher, reported on `main`, that nobody has reviewed yet. Shown as a claim,
never as the stage.
_Avoid_: stage

**Stage off main**:
The furthest stage a game reaches with open PRs or local patches, with the PRs it needs. It becomes the
stage once those PRs are merged.
_Avoid_: stage, unverified claim

**Working group**:
A thread outside upstream that follows one title on a patched stack, such as AlxcBTW/AnyPS5#44 for
Sword of the Sea. Everything reported there is off main.

**Stage review**:
A person's verdict on a claim (confirmed, downgraded or suppressed), with the sentence it rests on.

**Confidence**:
How sure the map is of a best stage: verified (a person checked the source), corroborated (two or more
GitHub accounts report it), reported (one account), or none.

**Stage history**:
The dates on which a game's best stage rose, each with its source.
_Avoid_: timeline, in the page's words

**Cover**:
A game's picture, linked from the PlayStation Store or Steam where they publish it, never stored here.

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
