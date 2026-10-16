# Game covers: where they come from and on what terms

Every game on the map shows a cover when one exists on a public CDN, and its initials when not. The
repository stores no artwork: `roadmap.json` carries image URLs, and the reader's browser loads the
pictures from the CDN that serves them. `anyps5_roadmap/images.py` finds the URLs at build time.

## Sources, in order

1. **`data/games.json`**: a person can set a game's `image` (an https URL and the page it comes from), or
   `"image": null` to show no cover, for example when the store's art is wrong for a homebrew app that
   reuses a retail title ID.
2. **The PlayStation Store.** The PlayStation title list (below) gives each PS5 title ID its store concept.
   The concept's page on `store.playstation.com` embeds the game's artwork, hosted on
   `image.api.playstation.com`. The map uses the concept's own media: `MASTER` (square key art) for the rows,
   `GAMEHUB_COVER_ART` (16:9) and `PORTRAIT_BANNER` (2:3) as alternatives. The CDN resizes on request, so
   the page asks for 48 or 88 px tiles (`?w=48`, `?w=96` for 2x screens) instead of the full image.
3. **Steam.** For a concept the store has no artwork for, Wikidata ties the concept (property P12332,
   PlayStation Store concept ID) to a Steam app (P1733), and Steam's CDN serves the app's library art
   (`shared.akamai.steamstatic.com/store_item_assets/steam/apps/<id>/library_600x900.jpg`).
4. **None.** Homebrew titles (PPSA99xxx and other IDs the store does not list) show their initials.

A homebrew app that uses a retail title ID gets no store cover: when a curated name, or a name that reports
use three or more times, has nothing to do with the store's name for the ID, the store entry is set aside
for that title (it shows up under "Possible duplicates to check" as `reused-id`).

## Caching and cost

Lookups are cached in `data/cache/images.json`, which the Roadmap workflow keeps between runs with the rest
of the API cache: a found cover for 30 days, a miss for 7. One build reads at most three store pages at a
time and spends at most three minutes on them (`BUDGET_S`), so a cold cache fills over one or two runs
and a warm one costs nothing. Wikidata gets one SPARQL query per build, for all misses together. An
offline build (`--offline`) reads the cache and never the network.

## The PlayStation title list

[andshrew/PlayStation-Titles](https://github.com/andshrew/PlayStation-Titles) (MIT license) lists every PS5
title ID with its store concept, official name, content ID and region, built from the PlayStation Store. A
live build downloads `PS5_Titles.tsv` (and `PS4_Titles.tsv` when a report names a CUSA ID) into
`data/cache/`, revalidating with its ETag, so an unchanged list costs one `304 Not Modified`. The map uses it
to put region variants of a game together, to name title IDs, and to find each game's store page.

## Terms

- **Cover art belongs to its publishers.** The map does not copy it; it links the picture where the
  PlayStation Store and Steam publish it, names the source under every cover ("Cover from the PlayStation
  Store") and links the store page. The PlayStation Store and its image CDN are not a public API, and no
  license is granted for this use: Sony's [Terms of Service](https://www.playstation.com/content/dam/global_pdc/en/corporate/legal/tosua/march-2026/TOS-2026-EN.pdf) (sections 10.9 and 10.10)
  reserve all rights in PlayStation content. Steam's art is likewise its publishers'. A rights holder who
  wants a cover removed can open an issue; the fix is an `"image": null` entry in `data/games.json`.
- **Not affiliated** with Sony Interactive Entertainment or Valve. PlayStation and PS5 are trademarks of Sony
  Interactive Entertainment.
- **andshrew/PlayStation-Titles** is used under its MIT license.
- **Wikidata** data is CC0.

## Considered and not used

- **Committing the images** to the repository: it would redistribute copyrighted art and grow the repository
  with every new game.
- **prosperopatches.com** and **serialstation.com**: third-party hosts of console icons; one has no stated
  terms, the other blocks automated requests.
- **IGDB, RAWG and SteamGridDB**: all need an API key, and none looks games up by PS5 title ID, which the
  store concept does. RAWG also requires a visible attribution link on every page. They stay an option if
  the store path stops working; nothing in the build depends on a key.
- **The PS4 `tmdb` metadata service**: it needs a key extracted from console firmware.
