// The lists the views show: the filters and sort orders of the game list and the blocker list.
// Pure functions over the model, so tests and views share them.

import type { Accessors, Dir } from "../lib/sort";
import { matchesTerms, searchTerms } from "../lib/text";
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
  const terms = searchTerms(q);
  const test = BLOCKER_FILTERS[status].test;
  return rows.filter((r) => test(r) && (!area || r.area === area) && matchesTerms(r.search, terms));
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
  const terms = searchTerms(q);
  return rows.filter(
    (g) =>
      (stage === "all" || (stage === "none" ? g.stage == null : g.stage === stage)) &&
      (!tag || g.tags.includes(tag)) &&
      matchesTerms(g.search, terms),
  );
}

/** Games per stage chip ("all", each stage name, "none"). */
export function stageCounts(rows: readonly GameRow[]): Map<string, number> {
  const n = new Map<string, number>([["all", rows.length]]);
  for (const g of rows) n.set(g.stage ?? "none", (n.get(g.stage ?? "none") ?? 0) + 1);
  return n;
}

/** Games per tag: a game counts once for each of its tags. */
export function tagCounts(rows: readonly GameRow[]): Map<string, number> {
  const n = new Map<string, number>();
  for (const g of rows) for (const t of g.tags) n.set(t, (n.get(t) ?? 0) + 1);
  return n;
}

/**
 * The game list: one row per game. The search reads every title ID, alias and name of a game, so a region's
 * title ID or a short form such as "GTA V" finds it.
 */
export function gameList(rows: readonly GameRow[], query: GameQuery): GameRow[] {
  return filterGames(rows, query);
}

export const GAME_SORTS = ["name", "stage", "stop", "chain", "report"] as const;
export type GameSort = (typeof GAME_SORTS)[number];

export const gameAccessors: Accessors<GameRow, GameSort> = {
  name: (g) => g.name,
  // no stage ranks below the first stage, so it leads "Earliest first" and trails "Furthest first"
  stage: (g) => g.stageRank,
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
