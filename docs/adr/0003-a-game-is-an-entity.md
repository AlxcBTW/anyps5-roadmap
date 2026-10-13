# A game is an entity, not a group of title IDs with one name

Until schema 1 the data had one entry per title ID, and the pages put title IDs together only when their
mined names were spelled exactly alike. "GTA V" (PPSA04264) and "Grand Theft Auto V" (PPSA04263) were two
games, "Blasphemous 2" and "Blasphemous II" too, and the ranking counted a blocker twice when it stopped both
regions of one game. A search for "theft" did not find the row named GTA V.

Now the generator resolves games once (`anyps5_roadmap/identity.py`) and `roadmap.json` (schema 2) carries
them: each game has an id, a canonical name, its title IDs, aliases, a cover, and a stage, confidence,
timeline and chain evaluated over the evidence of all of its title IDs. Blocker scores count games. The
pages, `ROADMAP.md`, the feed and the PR preview all read the same games, so they agree.

Title IDs are one game on a person's word (`data/games.json`), on the PlayStation Store's (one store concept,
from the PlayStation title list), or when their names agree after normalising, and both names are trusted or
both mined. Weaker matches (a mined name that equals a listed game's, a subtitle, a prefix, a near spelling)
are listed for review and never merged automatically, because a wrong merge hides a game and moves its
evidence, while a missed merge only shows a duplicate. Every merge carries its reasons in `identity.merges`;
the PR preview lists merges a change adds or removes, and the feed announces new ones.

## Considered options

- **Group in the web app only**, as before but with a smarter key. Rejected: the classic page, `ROADMAP.md`,
  the feed and the ranking would each need the same rules, and they had already drifted (the data ranked by
  title ID while the page ranked by name).
- **Merge on fuzzy names automatically.** Rejected: "Minecraft" and "Minecraft Legends", "Hades" and "Hades
  II" are different games, and a homebrew app often reuses a retail title ID. The store concept and a
  person's word are the strong signals; the name key only joins spellings of the same name.
- **Key games by their first title ID.** Rejected: the id would change when a lower region ID appears. Game
  ids are slugs of the name, and every title ID of a game still opens it (`#/games/PPSA04264`).
