# The front page leads with the games

The first version of the app opened on a dashboard: four headline numbers, the stage ladder in eight
columns, and a board of fifteen blocker cards in three lanes (In review, Next up, Recently fixed),
under six tabs. It answered "what is being fixed" before "does my game run", and a first-time visitor
met issue titles about VGPRs and fork PR numbers before any game name.

The front page now answers the visitor's question first. A short hero says what AnyPS5 and the map
are, shows four numbers (games tracked, games that reach their menus, open blockers, fixes in review)
and offers one action, the search. Below it is the game list: one row per game with its stage and the
one blocker that stops it, filtered by stage chips. Region IDs of one game collapse into its best row.
The ranking moved to Blockers, where the old lanes are status filters; the method, the help links and
the data files moved to About; Coverage is linked from About and the footer. The top bar has four
items: Games, Blockers, Changes, About. `#/games` and every older link keep working.

## Considered options

- **Keep the dashboard and trim it.** Rejected: fewer cards still put blockers ahead of games, and the
  search, the main thing a visitor wants, stayed one click away.
- **A separate landing page with the list one click away.** Rejected: it adds a page that only links
  to the list. The hero is short enough that the list starts above the fold on a laptop.
