// Everything the views show, derived once from roadmap.json. A game is one entity of the data (roadmap.json
// `games`): all of its title IDs, region variants and other spellings of its name, evaluated together. The
// ranking counts games, as the data does.

import { compareText } from "../lib/sort";
import { fold } from "../lib/text";
import type { Area, Blocker, BranchStage, ChainStep, Claim, Confidence, Evidence, Game, PullRequest, RoadmapDoc, Stage, Tag } from "./schema";

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
  score: number; // 3 × only stop + 2 × first stop + games
  games: number; // games that list it anywhere
  firstStop: number; // games it stops first
  onlyStop: number; // games for which it is the only stop left
  fix: FixStatus;
  helpWanted: boolean;
  lastActivity: string | null;
  search: string;
}

export interface GameRow {
  id: string; // the game's id, a slug of its name
  name: string; // the game's name, or its title ID when the name is unknown
  named: boolean;
  game: Game;
  ids: string[]; // its title IDs, the leading one first
  stage: string | null; // best qualifying stage; never an unverified claim
  stageRank: number; // -1 without a stage
  confidence: Confidence;
  reports: string | null; // "Checked by hand", "2 reports on main"
  sure: string | null; // the same for a row: "Checked by hand", "2 reports"
  claim: Claim | null;
  claimReports: number;
  offMain: BranchStage | null; // further with open PRs or patches; never the stage
  steps: (ChainStep & { title?: string })[]; // open stops on the map, first stop first
  tags: string[]; // in the order of the tag list
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
  games: number; // listed games
  titleIds: number; // the title IDs behind them
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
  tags: Tag[]; // the fixed tag list, in display order
  stageRank: (stage: string | null | undefined) => number;
  blockers: BlockerRow[]; // ranked, then not linked to a game, then resolved
  blocker: (id: string) => BlockerRow | undefined;
  games: GameRow[]; // one row per listed game, highest stage first
  game: (id: string) => GameRow | undefined; // by game id or by any of its title IDs
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

function folded(words: (string | null | undefined)[]): string {
  return fold(words.filter(Boolean).join(" "));
}

export function buildModel(doc: RoadmapDoc): Model {
  const stages = doc.stages;
  const rankOf = new Map(stages.map((s, i) => [s.name, i]));
  const stageRank = (s: string | null | undefined) => (s != null && rankOf.has(s) ? rankOf.get(s)! : -1);
  const byId = new Map(doc.blockers.map((b) => [b.id, b]));

  // ranking: open blockers linked to a game, in the data's order (by score over games)
  const open = doc.ranking.map((id) => byId.get(id)).filter((b): b is Blocker => !!b);
  const rows = new Map<string, BlockerRow>();
  const toRow = (b: Blocker): BlockerRow => {
    const r: BlockerRow = {
      id: b.id,
      ref: ref(b),
      title: b.title,
      area: areaName(b.area),
      blocker: b,
      open: b.status === "open",
      rank: null,
      score: b.score ?? 0,
      games: b.total ?? 0,
      firstStop: b.frontier ?? 0,
      onlyStop: b.one_fix_away ?? 0,
      fix: fixStatus(b),
      helpWanted: !!b.help_wanted,
      lastActivity: b.last_activity ?? null,
      search: "",
    };
    r.search = folded([b.id, r.ref, r.ref.replace("PR ", ""), b.title, b.signature, r.area, ...b.prs.map((p) => p.ref)]);
    rows.set(b.id, r);
    return r;
  };
  const linked = open.filter((b) => b.total).map(toRow);
  linked.forEach((r, i) => (r.rank = i + 1));
  const unlinked = open.filter((b) => !b.total).map(toRow);
  const ranked = new Set(open.map((b) => b.id));
  const resolved = doc.blockers.filter((b) => b.status !== "open" && !ranked.has(b.id)).map(toRow);
  resolved.sort((a, z) => (z.lastActivity ?? "").localeCompare(a.lastActivity ?? ""));
  // open blockers outside the ranking (none today) still get a row, so every link resolves
  const rest = doc.blockers.filter((b) => !rows.has(b.id)).map(toRow);
  const blockers = [...linked, ...unlinked, ...rest, ...resolved];

  // games: those with a stage, a stop or a claim
  const tagList = doc.tags ?? [];
  const listed = (doc.games ?? []).filter(
    (g) => g.stage || g.open_blockers?.length || g.unverified_claim || g.stage_on_branches,
  );
  const games: GameRow[] = listed.map((g) => {
    const stage = g.stage?.stage ?? null;
    const steps = (g.open_blockers ?? []).filter((s) => byId.has(s.id));
    const conf = g.confidence ?? { stage, reports_on_main: 0, authors: [], label: null };
    const tags = tagList.map((x) => x.name).filter((x) => (g.tags ?? []).includes(x));
    const ids = g.primary ? [g.primary, ...g.title_ids.filter((t) => t !== g.primary)] : g.title_ids;
    const words: (string | null | undefined)[] = [g.name, g.id, ...g.title_ids, ...g.aliases, g.engine, g.kind, ...tags];
    for (const t of g.titles ?? []) words.push(t.name);
    for (const s of steps) {
      const r = rows.get(s.id);
      if (r) words.push(r.title, r.ref, r.ref.replace("PR ", ""), r.blocker.signature);
    }
    return {
      id: g.id,
      name: g.name || ids[0] || g.id,
      named: !!g.name,
      game: g,
      ids,
      stage,
      stageRank: stageRank(stage),
      confidence: conf,
      reports: stage && conf.label ? conf.label : null,
      sure: !stage
        ? null
        : conf.level === "verified"
          ? "Checked by hand"
          : conf.reports_on_main
            ? `${conf.reports_on_main} report${conf.reports_on_main === 1 ? "" : "s"}`
            : null,
      claim: g.unverified_claim?.url ? g.unverified_claim : null,
      claimReports: conf.claim?.reports_on_main ?? 0,
      offMain: g.stage_on_branches ?? null,
      steps,
      tags,
      firstStop: steps.length ? (rows.get(steps[0].id) ?? null) : null,
      lastReport: g.last_evidence?.date ?? null,
      search: folded(words),
    };
  });
  games.sort((a, z) => z.stageRank - a.stageRank || compareText(a.name, z.name));
  const gameById = new Map<string, GameRow>();
  for (const g of games) {
    gameById.set(g.id, g);
    for (const tid of g.game.title_ids) if (!gameById.has(tid)) gameById.set(tid, g);
  }

  // the stage ladder: each game at its stage, and the blocker that holds most of them there
  const held = new Map<string, Map<string, number>>(stages.map((s) => [s.name, new Map()]));
  for (const g of games) {
    const first = g.steps[0];
    if (g.stage && first) {
      const at = held.get(g.stage)!;
      at.set(first.id, (at.get(first.id) ?? 0) + 1);
    }
  }
  const ladder: Rung[] = stages.map((stage) => {
    let top: Rung["heldBy"] = null;
    for (const [id, n] of held.get(stage.name) ?? []) {
      const row = rows.get(id)!;
      const better = !top || n > top.games || (n === top.games && (row.rank ?? 999) < (top.row.rank ?? 999));
      if (better) top = { row, games: n };
    }
    return { stage, games: games.filter((g) => g.stage === stage.name).length, heldBy: top };
  });

  const afterFix = (id: string): AfterFix[] => {
    const b = rows.get(id);
    if (!b) return [];
    const out: AfterFix[] = [];
    for (const gid of b.blocker.games ?? []) {
      const game = gameById.get(gid);
      if (!game) continue;
      const ids = game.steps.map((s) => s.id);
      const i = ids.indexOf(id);
      if (i < 0) continue;
      if (i > 0) out.push({ game, kind: "earlier", then: rows.get(ids[0])! });
      else if (i + 1 < ids.length) out.push({ game, kind: "next", then: rows.get(ids[i + 1])! });
      else out.push({ game, kind: "done" });
    }
    return out;
  };

  return {
    doc,
    repo: doc.upstream.repo,
    project: doc.project?.repo || "AlxcBTW/anyps5-roadmap",
    stages,
    tags: tagList,
    stageRank,
    blockers,
    blocker: (id) => rows.get(id),
    games,
    game: (id) => gameById.get(id),
    ladder,
    noStage: games.filter((g) => g.stage == null).length,
    counts: {
      games: games.length,
      titleIds: games.reduce((n, g) => n + g.game.title_ids.length, 0),
      gamesWithStage: games.filter((g) => g.stage).length,
      reachMenus: games.filter((g) => g.stageRank >= stageRank("Menus")).length,
      gamesWaiting: games.filter((g) => g.steps.length).length,
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

export function gameReport(model: Model, g: GameRow): string {
  const best: Partial<Evidence> = g.game.stage ?? {};
  const claim: Partial<Claim> = g.game.unverified_claim ?? {};
  const tid = best.title ?? g.ids[0];
  let now = best.stage ? `${best.stage} (${best.origin ?? "mined"})` : "No stage yet";
  if (claim.stage) now += `; claimed ${claim.stage}, unverified`;
  if (g.offMain) now += `; ${g.offMain.stage} off main`;
  return reportUrl(model.project, "wrong-stage.yml", {
    title: g.named ? `Stage: ${g.name} (${tid})` : `Stage: ${tid}`,
    title_id: tid,
    game: g.named ? g.name : "",
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

/** How a tag source reads: the site it is on, or the homebrew's own README. */
export function tagSourceLabel(url: string): string {
  const host = url.split("//")[1]?.split("/")[0] ?? "";
  if (host.endsWith("wikidata.org")) return "Wikidata";
  if (host === "store.playstation.com") return "PlayStation Store";
  if (host.endsWith("steamspy.com")) return "SteamSpy";
  if (host === "github.com") return "the homebrew’s README";
  return host || url;
}
