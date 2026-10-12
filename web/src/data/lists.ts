// The lists the views show: the filters and sort orders of the game list and the blocker list.
// Pure functions over the model, so tests and views share them.

import type { Accessors, Dir } from "../lib/sort";
import type { BlockerRow, GameRow } from "./model";

// -- blockers -------------------------------------------------------------------

export const BLOCKER_FILTERS = {
  open: { label: "Open", test: (r: BlockerRow) => r.open },
  review: { label: "Fix in review", test: (r: BlockerRow) => r.fix.kind === "review" },
  nofix: { label: "No open fix", test: (r: BlockerRow) => r.open && r.fix.kind !== "review" },
  help: { label: "Help wanted", test: (r: BlockerRow) => r.open && r.helpWanted },
  unlinked: { label: "No game linked", test: (r: BlockerRow) => r.open && r.rank == null },
  resolved: { label: "Fixed", test: (r: BlockerRow) => !r.open },
} as const;

export type BlockerFilter = keyof typeof BLOCKER_FILTERS;

export interface BlockerQuery {
  status: BlockerFilter;
  area: string; // "" for every area
  q: string;
}

export function filterBlockers(rows: readonly BlockerRow[], { status, area, q }: BlockerQuery): BlockerRow[] {
  const term = q.trim().toLowerCase();
  const test = BLOCKER_FILTERS[status].test;
  return rows.filter((r) => test(r) && (!area || r.area === area) && (!term || r.search.includes(term)));
}

const FIX_ORDER = { review: 0, partial: 1, closed: 2, none: 3, resolved: 4 } as const;

export const BLOCKER_SORTS = ["rank", "title", "area", "status", "games", "score", "activity"] as const;
export type BlockerSort = (typeof BLOCKER_SORTS)[number];

export const blockerAccessors: Accessors<BlockerRow, BlockerSort> = {
  rank: (r) => r.rank,
  title: (r) => r.title,
  area: (r) => r.area,
  status: (r) => FIX_ORDER[r.fix.kind],
  games: (r) => (r.open ? r.games : null),
  score: (r) => (r.open ? r.score : null),
  activity: (r) => r.lastActivity,
};

/** The direction a column sorts in when it is first clicked. */
export const blockerNatural: Record<BlockerSort, Dir> = {
  rank: "asc",
  title: "asc",
  area: "asc",
  status: "asc",
  games: "desc",
  score: "desc",
  activity: "desc",
};

// -- games ----------------------------------------------------------------------

export interface GameQuery {
  stage: string; // "all", a stage name, or "none"
  tag?: string; // a tag name; empty or missing for every game
  q: string;
}

export function filterGames(rows: readonly GameRow[], { stage, tag = "", q }: GameQuery): GameRow[] {
  const term = q.trim().toLowerCase();
  return rows.filter(
    (g) =>
      (stage === "all" || (stage === "none" ? g.stage == null : g.stage === stage)) &&
      (!tag || g.tags.includes(tag)) &&
      (!term || g.search.includes(term)),
  );
}

/** Games per stage chip ("all", each stage name, "none"): the names with a title ID at that stage. */
export function stageCounts(rows: readonly GameRow[]): Map<string, number> {
  const names = new Map<string, Set<string>>([["all", new Set()]]);
  for (const g of rows) {
    names.get("all")!.add(g.name);
    const k = g.stage ?? "none";
    names.set(k, (names.get(k) ?? new Set()).add(g.name));
  }
  return new Map([...names].map(([k, s]) => [k, s.size]));
}

/** Games per tag, by name: a game counts once for each of its tags. */
export function tagCounts(rows: readonly GameRow[]): Map<string, number> {
  const names = new Map<string, Set<string>>();
  for (const g of rows) for (const t of g.tags) names.set(t, (names.get(t) ?? new Set()).add(g.name));
  return new Map([...names].map(([k, s]) => [k, s.size]));
}

/** One row per game: the first title ID of each name in the given order, so a sorted list keeps its best. */
export function onePerGame(rows: readonly GameRow[]): GameRow[] {
  const seen = new Set<string>();
  return rows.filter((g) => !seen.has(g.name) && !!seen.add(g.name));
}

/**
 * The game list: one row per game, its best title ID (rows come highest stage first, as model.games
 * does). The stage filter reads that row, like the stage chips and the ladder; the tag filter reads the
 * game's tags, which every title ID of it shares; the search reads every title ID of the game, so a
 * region's PPSA ID still finds it.
 */
export function gameList(rows: readonly GameRow[], { stage, tag = "", q }: GameQuery): GameRow[] {
  const hit = new Set(filterGames(rows, { stage: "all", q }).map((g) => g.name));
  return filterGames(onePerGame(rows), { stage, tag, q: "" }).filter((g) => hit.has(g.name));
}

export const GAME_SORTS = ["name", "stage", "stop", "chain", "report"] as const;
export type GameSort = (typeof GAME_SORTS)[number];

export const gameAccessors: Accessors<GameRow, GameSort> = {
  name: (g) => g.name,
  stage: (g) => (g.stageRank < 0 ? null : g.stageRank),
  stop: (g) => g.firstStop?.rank ?? (g.firstStop ? 1e6 : null),
  chain: (g) => g.steps.length || null,
  report: (g) => g.lastReport,
};

export const gameNatural: Record<GameSort, Dir> = {
  name: "asc",
  stage: "desc",
  stop: "asc",
  chain: "desc",
  report: "desc",
};
