// Everything the views show, derived once from roadmap.json. The rules match the classic page
// (render_html.py): games are counted by name, since one game can have several title IDs (regions),
// and the ranking counts games, not title IDs.

import type { Area, Blocker, ChainStep, Claim, Evidence, PullRequest, RoadmapDoc, Stage, Title } from "./schema";

export const AREA_NAMES: Record<Area, string> = {
  shader: "Shader recompiler",
  agc: "AGC driver",
  libkernel: "libkernel",
  libc: "libc",
  prx: "HLE libraries",
  relinker: "Relinker",
};

export type FixKind = "review" | "partial" | "closed" | "none" | "resolved";

export interface FixStatus {
  kind: FixKind;
  label: string;
  pr: PullRequest | null; // the PR the label refers to
}

export interface BlockerRow {
  id: string;
  ref: string; // "#2548", "PR #2106" or the id
  title: string;
  area: string; // display name
  blocker: Blocker;
  open: boolean;
  rank: number | null; // place in the ranking; null when no game is linked or it is resolved
  score: number; // 3 × only stop + 2 × first stop + games, counted by game name
  games: number; // games that list it anywhere
  firstStop: number; // games it stops first
  onlyStop: number; // games for which it is the only stop left
  fix: FixStatus;
  helpWanted: boolean;
  lastActivity: string | null;
  search: string;
}

export interface GameRow {
  id: string;
  name: string; // the game's name, or its title ID when the name is unknown
  named: boolean;
  title: Title;
  stage: string | null; // best verified stage; never an unverified claim
  stageRank: number; // -1 without a stage
  reports: string | null; // "2 reports on main"
  claim: Claim | null;
  claimReports: number;
  steps: ChainStep[]; // open stops on the map, first stop first
  firstStop: BlockerRow | null;
  lastReport: string | null;
  search: string;
}

export interface Rung {
  stage: Stage;
  games: number;
  heldBy: { row: BlockerRow; games: number } | null; // the blocker that holds most games at this stage
}

export type AfterFix =
  | { game: GameRow; kind: "next"; then: BlockerRow }
  | { game: GameRow; kind: "earlier"; then: BlockerRow }
  | { game: GameRow; kind: "done" };

export interface Counts {
  games: number; // listed games, by name
  titleIds: number; // listed title IDs
  gamesWithStage: number;
  reachMenus: number; // games whose best stage is Menus or higher
  gamesWaiting: number; // games with at least one open stop
  open: number;
  ranked: number;
  inReview: number;
  resolved: number;
}

export interface Model {
  doc: RoadmapDoc;
  repo: string; // upstream, e.g. boykopovar/AnyPS5
  project: string; // this repository; corrections are filed here
  stages: Stage[];
  stageRank: (stage: string | null | undefined) => number;
  blockers: BlockerRow[]; // ranked, then not linked to a game, then resolved
  blocker: (id: string) => BlockerRow | undefined;
  games: GameRow[]; // one row per listed title ID, highest stage first
  game: (id: string) => GameRow | undefined;
  regions: (id: string) => GameRow[]; // the other listed title IDs of the same game
  ladder: Rung[];
  noStage: number; // games with an open stop but no confirmed stage
  counts: Counts;
  afterFix: (id: string) => AfterFix[];
}

export function ref(b: Pick<Blocker, "id" | "issue">): string {
  if (b.issue) return `#${b.issue}`;
  if (b.id.startsWith("pr-")) return `PR #${b.id.slice(3)}`;
  return b.id;
}

export function areaName(area: string | null | undefined): string {
  return (area && AREA_NAMES[area as Area]) || area || "Other";
}

export function fixStatus(b: Blocker): FixStatus {
  const fixes = b.prs.filter((p) => p.link === "fixes");
  if (b.status !== "open") {
    return { kind: "resolved", label: "Fixed", pr: fixes.find((p) => p.state === "merged") ?? null };
  }
  const rules: [PullRequest["state"][], FixKind, string][] = [
    [["open", "draft"], "review", "Fix in review"],
    [["merged"], "partial", "Partly fixed"],
    [["closed"], "closed", "Fix closed unmerged"],
  ];
  for (const [states, kind, label] of rules) {
    const hit = fixes.find((p) => states.includes(p.state));
    if (hit) return { kind, label, pr: hit };
  }
  return { kind: "none", label: "No fix yet", pr: null };
}

/** The PR a status names, unless the blocker is that PR itself (PR #2106 "Fix closed unmerged #2106"). */
export function statusRef(row: Pick<BlockerRow, "id" | "fix">): string | null {
  const pr = row.fix.pr;
  if (!pr) return null;
  return row.id === `pr-${pr.ref.replace(/^#/, "")}` ? null : pr.ref;
}

function lower(words: (string | null | undefined)[]): string {
  return words.filter(Boolean).join(" ").toLowerCase();
}

export function buildModel(doc: RoadmapDoc): Model {
  const stages = doc.stages;
  const rankOf = new Map(stages.map((s, i) => [s.name, i]));
  const stageRank = (s: string | null | undefined) => (s != null && rankOf.has(s) ? rankOf.get(s)! : -1);
  const byId = new Map(doc.blockers.map((b) => [b.id, b]));
  const titles = new Map(doc.titles.map((t) => [t.id, t]));
  const nameOf = (tid: string) => titles.get(tid)?.name || tid;
  const names = (ids: string[]) => new Set(ids.map(nameOf));

  // ranking: open blockers linked to a game, by score over game names, ties in the data's order
  const open = doc.ranking.map((id) => byId.get(id)).filter((b): b is Blocker => !!b);
  const order = new Map(open.map((b, i) => [b.id, i]));
  const rows = new Map<string, BlockerRow>();
  const toRow = (b: Blocker): BlockerRow => {
    const all = names(b.titles ?? []);
    const first = names(b.frontier_titles ?? []);
    const only = names(b.one_fix_titles ?? []);
    const r: BlockerRow = {
      id: b.id,
      ref: ref(b),
      title: b.title,
      area: areaName(b.area),
      blocker: b,
      open: b.status === "open",
      rank: null,
      score: 3 * only.size + 2 * first.size + all.size,
      games: all.size,
      firstStop: first.size,
      onlyStop: only.size,
      fix: fixStatus(b),
      helpWanted: !!b.help_wanted,
      lastActivity: b.last_activity ?? null,
      search: "",
    };
    r.search = lower([b.id, r.ref, r.ref.replace("PR ", ""), b.title, b.signature, r.area, ...b.prs.map((p) => p.ref)]);
    rows.set(b.id, r);
    return r;
  };
  const linked = open.filter((b) => b.total).map(toRow);
  linked.sort((a, z) => z.score - a.score || order.get(a.id)! - order.get(z.id)!);
  linked.forEach((r, i) => (r.rank = i + 1));
  const unlinked = open.filter((b) => !b.total).map(toRow);
  const resolved = doc.blockers.filter((b) => b.status !== "open" && !order.has(b.id)).map(toRow);
  resolved.sort((a, z) => (z.lastActivity ?? "").localeCompare(a.lastActivity ?? ""));
  // open blockers outside the ranking (none today) still get a row, so every link resolves
  const rest = doc.blockers.filter((b) => !rows.has(b.id)).map(toRow);
  const blockers = [...linked, ...unlinked, ...rest, ...resolved];

  // games: titles with a stage, a stop or a claim; one row per title ID
  const listed = doc.titles.filter((t) => t.best_stage || t.open_blockers?.length || t.unverified_claim);
  const games: GameRow[] = listed.map((t) => {
    const stage = t.best_stage?.stage ?? null;
    const steps = (t.open_blockers ?? []).filter((s) => byId.has(s.id));
    const conf = t.confidence;
    const words: (string | null | undefined)[] = [t.name, t.id, t.engine, t.kind];
    for (const s of steps) {
      const r = rows.get(s.id);
      if (r) words.push(r.title, r.ref, r.ref.replace("PR ", ""), r.blocker.signature);
    }
    return {
      id: t.id,
      name: t.name || t.id,
      named: !!t.name,
      title: t,
      stage,
      stageRank: stageRank(stage),
      reports: stage && conf?.label ? conf.label : null,
      claim: t.unverified_claim?.url ? t.unverified_claim : null,
      claimReports: conf?.claim?.reports_on_main ?? 0,
      steps,
      firstStop: steps.length ? (rows.get(steps[0].id) ?? null) : null,
      lastReport: t.last_evidence?.date ?? null,
      search: lower(words),
    };
  });
  games.sort((a, z) => z.stageRank - a.stageRank || a.name.toLowerCase().localeCompare(z.name.toLowerCase()));
  const gameById = new Map(games.map((g) => [g.id, g]));
  const byName = new Map<string, GameRow[]>();
  for (const g of games) byName.set(g.name, [...(byName.get(g.name) ?? []), g]);

  // the stage ladder: each game at its highest confirmed stage over all of its title IDs
  const best = new Map<string, string | null>();
  for (const g of games) {
    const cur = best.get(g.name);
    if (!best.has(g.name) || (g.stage && (cur == null || g.stageRank > stageRank(cur)))) best.set(g.name, g.stage);
  }
  const held = new Map<string, Map<string, Set<string>>>(stages.map((s) => [s.name, new Map()]));
  for (const g of games) {
    const first = g.steps[0];
    if (g.stage && first) {
      const at = held.get(g.stage)!;
      at.set(first.id, (at.get(first.id) ?? new Set()).add(g.name));
    }
  }
  const ladder: Rung[] = stages.map((stage) => {
    let top: Rung["heldBy"] = null;
    for (const [id, set] of held.get(stage.name) ?? []) {
      const row = rows.get(id)!;
      const better =
        !top || set.size > top.games || (set.size === top.games && (row.rank ?? 999) < (top.row.rank ?? 999));
      if (better) top = { row, games: set.size };
    }
    return { stage, games: [...best.values()].filter((s) => s === stage.name).length, heldBy: top };
  });

  const afterFix = (id: string): AfterFix[] => {
    const b = rows.get(id);
    if (!b) return [];
    const out: AfterFix[] = [];
    const seen = new Set<string>();
    for (const tid of b.blocker.titles ?? []) {
      const game = gameById.get(tid);
      if (!game) continue;
      const ids = game.steps.map((s) => s.id);
      const i = ids.indexOf(id);
      if (i < 0) continue;
      let entry: AfterFix;
      if (i > 0) entry = { game, kind: "earlier", then: rows.get(ids[0])! };
      else if (i + 1 < ids.length) entry = { game, kind: "next", then: rows.get(ids[i + 1])! };
      else entry = { game, kind: "done" };
      const key = `${game.name}|${entry.kind}|${"then" in entry ? entry.then.id : ""}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(entry);
    }
    return out;
  };

  const gameNames = new Set(games.map((g) => g.name));
  return {
    doc,
    repo: doc.upstream.repo,
    project: doc.project?.repo || "AlxcBTW/anyps5-roadmap",
    stages,
    stageRank,
    blockers,
    blocker: (id) => rows.get(id),
    games,
    game: (id) => gameById.get(id),
    regions: (id) => {
      const g = gameById.get(id);
      return g ? (byName.get(g.name) ?? []).filter((o) => o.id !== id) : [];
    },
    ladder,
    noStage: [...best.values()].filter((s) => s == null).length,
    counts: {
      games: gameNames.size,
      titleIds: games.length,
      gamesWithStage: [...best.values()].filter(Boolean).length,
      reachMenus: [...best.values()].filter((s) => s != null && stageRank(s) >= stageRank("Menus")).length,
      gamesWaiting: new Set(games.filter((g) => g.steps.length).map((g) => g.name)).size,
      open: open.length,
      ranked: linked.length,
      inReview: open.filter((b) => rows.get(b.id)!.fix.kind === "review").length,
      resolved: resolved.length,
    },
    afterFix,
  };
}

// -- correction links -------------------------------------------------------

/** A prefilled issue form of this project (issue forms take ?<field id>=value). */
export function reportUrl(project: string, template: string, fields: Record<string, string | null | undefined>): string {
  const q = new URLSearchParams({ template });
  for (const [k, v] of Object.entries(fields)) if (v) q.set(k, v);
  return `https://github.com/${project}/issues/new?${q}`;
}

export function blockerReport(model: Model, row: BlockerRow): string {
  const label = `${row.ref} ${row.title}`;
  return reportUrl(model.project, "blocker.yml", {
    title: [...`Blocker: ${label}`].slice(0, 120).join(""),
    blocker: label,
    page_source: row.blocker.url,
    error: row.blocker.signature,
  });
}

export function gameReport(model: Model, t: Title): string {
  const best: Partial<Evidence> = t.best_stage ?? {};
  const claim: Partial<Claim> = t.unverified_claim ?? {};
  let now = best.stage ? `${best.stage} (${best.origin ?? "mined"})` : "No stage yet";
  if (claim.stage) now += `; claimed ${claim.stage}, unverified`;
  return reportUrl(model.project, "wrong-stage.yml", {
    title: t.name ? `Stage: ${t.name} (${t.id})` : `Stage: ${t.id}`,
    title_id: t.id,
    game: t.name ?? "",
    page_stage: now,
    page_source: best.url || claim.url || "",
  });
}

/** "#2156 comment", "PR #2583", "COMPATIBILITY.md" or the host: how a source link reads. */
export function sourceLabel(url: string, repo: string): string {
  const base = `https://github.com/${repo}/`;
  if (url.startsWith(base)) {
    const [kind, ...tail] = url.slice(base.length).split("/");
    const rest = tail.join("/");
    const num = rest.split("#")[0].split("/")[0];
    if (kind === "pull" && /^\d+$/.test(num)) return `PR #${num}`;
    if (kind === "issues" && /^\d+$/.test(num)) return `#${num}${rest.includes("#issuecomment") ? " comment" : ""}`;
    if (kind === "blob") return rest.split("/").pop() ?? rest;
  }
  if (url.startsWith("https://github.com/")) {
    const parts = url.split("/");
    const n = parts[6]?.split("#")[0];
    if (n && /^\d+$/.test(n)) return `${parts[3]}#${n}`;
  }
  return url.split("//")[1]?.split("/")[0] ?? url;
}
