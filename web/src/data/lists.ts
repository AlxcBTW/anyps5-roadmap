// The lists the views show: the roadmap board's lanes, and the filters and sort columns of the
// Blockers and Games tables. Pure functions over the model, so tests and views share them.

import type { Accessors, Dir } from "../lib/sort";
import type { BlockerRow, GameRow, Model } from "./model";

// -- the roadmap board --------------------------------------------------------

export interface Board {
  review: BlockerRow[]; // open, with a fix PR open or in draft
  next: BlockerRow[]; // ranked, without an open fix PR, best first
  fixed: { row: BlockerRow; date: string | null; fromFeed: boolean }[]; // resolved, newest first
}

export function board(model: Model, resolvedAt: Map<string, string>): Board {
  const open = model.blockers.filter((r) => r.open);
  const byRank = (a: BlockerRow, z: BlockerRow) => (a.rank ?? Infinity) - (z.rank ?? Infinity);
  const fixed = model.blockers
    .filter((r) => !r.open)
    .map((row) => {
      const seen = resolvedAt.get(row.id);
      return { row, date: seen ?? row.lastActivity, fromFeed: !!seen };
    })
    .sort((a, z) => Number(z.fromFeed) - Number(a.fromFeed) || (z.date ?? "").localeCompare(a.date ?? ""));
  return {
    review: open.filter((r) => r.fix.kind === "review").sort(byRank),
    next: open.filter((r) => r.rank != null && r.fix.kind !== "review").sort(byRank),
    fixed,
  };
}

// -- blockers -------------------------------------------------------------------

export const BLOCKER_FILTERS = {
  open: { label: "Open", test: (r: BlockerRow) => r.open },
  review: { label: "Fix in review", test: (r: BlockerRow) => r.fix.kind === "review" },
  nofix: { label: "No open fix", test: (r: BlockerRow) => r.open && r.fix.kind !== "review" },
  help: { label: "Help wanted", test: (r: BlockerRow) => r.open && r.helpWanted },
  unlinked: { label: "No game linked", test: (r: BlockerRow) => r.open && r.rank == null },
  resolved: { label: "Resolved", test: (r: BlockerRow) => !r.open },
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
  q: string;
}

export function filterGames(rows: readonly GameRow[], { stage, q }: GameQuery): GameRow[] {
  const term = q.trim().toLowerCase();
  return rows.filter(
    (g) =>
      (stage === "all" || (stage === "none" ? g.stage == null : g.stage === stage)) &&
      (!term || g.search.includes(term)),
  );
}

/** Title IDs per stage chip ("all", each stage name, "none"). */
export function stageCounts(rows: readonly GameRow[]): Map<string, number> {
  const n = new Map<string, number>([["all", rows.length]]);
  for (const g of rows) n.set(g.stage ?? "none", (n.get(g.stage ?? "none") ?? 0) + 1);
  return n;
}

export function gameCount(rows: readonly GameRow[]): number {
  return new Set(rows.map((g) => g.name)).size;
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
