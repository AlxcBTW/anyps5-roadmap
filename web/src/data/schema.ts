// The shape of site/roadmap.json (schema_version 2, written by anyps5_roadmap/assemble.py) and of
// site/feed.json (JSON Feed 1.1, written by anyps5_roadmap/feed.py). Only the fields the app reads are
// typed; AGENTS.md and llms.txt describe every field.

export type Area = "shader" | "agc" | "libkernel" | "libc" | "relinker" | "prx";
export type Origin = "curated" | "mined" | "upstream" | "github";

export interface PullRequest {
  key: string;
  ref: string; // "#2589" upstream, "AlxcBTW#25" on a fork
  url: string;
  title: string | null;
  state: "open" | "draft" | "merged" | "closed";
  link: "fixes" | "related" | "mentions";
  updated?: string | null;
  note?: string | null;
  origin?: Origin;
}

export interface Blocker {
  id: string; // "2548", "pr-2106", "1578~atoll" or a slug
  issue: number | null;
  url: string;
  title: string;
  signature: string | null;
  area: Area | null;
  status: "open" | "resolved";
  prs: PullRequest[];
  next: string | null;
  help_wanted: string | null;
  origin: Origin;
  created: string | null;
  last_activity: string | null;
  labels: string[];
  frontier: number;
  one_fix_away: number;
  total: number;
  titles: string[];
  frontier_titles: string[];
  one_fix_titles: string[];
  games: string[]; // game ids: frontier, one_fix_away and total count these
  frontier_games: string[];
  one_fix_games: string[];
  score: number;
  parent?: number;
}

export interface Evidence {
  stage: string;
  os?: string | null;
  gpu?: string | null;
  build?: string | null;
  build_kind?: "main" | "prs" | "patched" | null;
  url: string;
  date?: string | null;
  note?: string | null;
  quote?: string | null;
  origin?: Origin;
  verified?: boolean;
  author?: string | null;
  part?: string | null;
  title?: string; // the title ID it is about, in a game's evidence
  also?: string[]; // the same report quoted elsewhere
}

export interface Claim {
  stage: string;
  url: string;
  quote?: string | null;
}

export interface StageReview {
  claim: string;
  claim_url: string;
  verdict: "confirmed" | "downgraded" | "suppressed";
  stage?: string | null;
  url?: string | null;
  quote: string;
  reason?: string | null;
}

export interface ChainStep {
  id: string;
  origin: Origin;
  why: string | null;
  scope: string[] | null; // OS/GPU paths, e.g. ["Windows/NVIDIA"]; null applies to every path
}

export type ConfidenceLevel = "verified" | "corroborated" | "reported" | "none";

export interface Confidence {
  stage: string | null;
  level?: ConfidenceLevel;
  reports_on_main: number | null;
  authors: string[];
  last_seen?: string | null;
  claim?: { stage: string; reports_on_main: number; reports_on_branches: number };
  label: string | null; // "Checked by hand", "2 reports on main"
}

export interface Title {
  id: string; // PPSA + 5 digits
  name: string | null;
  engine: string | null;
  kind: "retail" | "homebrew" | null;
  tags?: string[]; // what kind of game it is, from RoadmapDoc.tags; empty when no source names one
  tag_sources?: string[]; // the public pages the tags come from
  curated: boolean;
  best_stage: Evidence | null;
  unverified_claim: Claim | null;
  stage_reviews: StageReview[];
  evidence: Evidence[];
  open_blockers: ChainStep[];
  resolved_blockers: string[];
  issues: number[];
  prs: number[];
  last_evidence: { kind: string; number: number; url: string; date: string | null } | null;
  confidence: Confidence;
}

/** A cover on a public CDN, hotlinked. `sizing: "w"` means the CDN resizes with ?w=<pixels>. */
export interface ImageRef {
  square: string | null;
  wide: string | null;
  portrait: string | null;
  source: string; // "PlayStation Store", "Steam" or "data/games.json"
  page: string | null;
  sizing: "w" | null;
}

export interface TitleRef {
  id: string;
  name: string | null;
  region: string | null; // US, EU, JP, Asia, KR
  platform: "PS5" | "PS4";
  content_id: string | null;
  stage: string | null;
}

export interface TimelineStep {
  date: string | null;
  stage: string;
  url: string;
  origin?: Origin;
  build?: string | null;
  title?: string;
}

/** One game: all of its title IDs, evaluated together. */
export interface Game {
  id: string; // a slug of its name, e.g. grand-theft-auto-v
  name: string | null;
  name_origin: "curated" | "store" | "mined" | null;
  name_sources: string[];
  aliases: string[];
  title_ids: string[];
  titles: TitleRef[];
  primary: string | null; // the title ID that leads: its chain decides where the game stops first
  store_url: string | null;
  kind: "retail" | "homebrew" | null;
  engine: string | null;
  tags: string[];
  tag_sources: string[];
  curated: boolean;
  image: ImageRef | null;
  stage: Evidence | null;
  confidence: Confidence;
  unverified_claim: Claim | null;
  stage_on_branches?: BranchStage | null;
  timeline: TimelineStep[];
  stage_reviews: (StageReview & { title?: string })[];
  evidence: Evidence[];
  evidence_count: number;
  open_blockers: (ChainStep & { title?: string })[];
  resolved_blockers: string[];
  issues: number[];
  prs: number[];
  discussions: number[];
  last_evidence: { url: string; date: string | null } | null;
}

/** The furthest stage reached off main: on a PR's branch, with open PRs, or with local patches. Never the stage. */
export interface BranchStage {
  stage: string;
  url: string;
  quote?: string | null;
  date?: string | null;
  build?: string | null;
  title?: string | null;
  needs: number[]; // the open upstream PRs it ran with
  patches: boolean; // it also had changes no PR carries
  confidence: { level: ConfidenceLevel; reports: number; authors: string[]; label: string | null };
}

export interface ReviewItem {
  kind: "mined-name" | "subtitle" | "prefix" | "similar" | "reused-id";
  title_ids: string[];
  names: (string | null)[];
  note: string;
  games: string[];
}

export interface Identity {
  merges: { game: string; name: string | null; title_ids: string[]; names: Record<string, string | null>; reasons: string[] }[];
  review: ReviewItem[];
  placeholders?: string[];
  rules?: string;
}

export interface Stage {
  name: string;
  rank: number;
  meaning: string;
}

/** One entry of the fixed tag list, in display order. */
export interface Tag {
  name: string; // "2D", "Shooter", "App"
  group: "Dimension" | "Genre" | "Kind";
  meaning: string;
}

export interface CoverageGroup {
  library?: string;
  encoding?: string;
  label?: string;
  done: number;
  todo: number;
  percent?: number;
  todo_names?: string[];
  requested?: Record<string, number[]>; // missing function -> open issues that ask for it
}

export interface Coverage {
  isa?: { done: number; total: number; groups: CoverageGroup[] } | null;
  hle?: { done: number; total: number; groups: CoverageGroup[] } | null;
  pm4?: {
    total: number;
    counts: { handled?: number; conditional?: number; rejected?: number };
    rows: { name: string; hex: string; kind: string; status: string }[];
  } | null;
}

export interface RoadmapDoc {
  schema_version: number;
  generated_at: string;
  upstream: { repo: string; ref: string | null; commit: string | null };
  project?: { repo: string; corrections?: string };
  window?: { days: number; since: string | null };
  stages: Stage[];
  tags?: Tag[];
  stats: Record<string, unknown> & {
    issues_scanned?: number;
    prs_scanned?: number;
    titles?: number;
    stage_reviews?: number;
  };
  ranking: string[];
  blockers: Blocker[];
  games: Game[];
  identity?: Identity;
  titles: Title[];
  coverage: Coverage | null;
  not_blockers?: { issue: number; reason: string }[];
  gaps?: string[];
  sources?: Record<string, string>;
}

export type ChangeType = "resolved" | "entered" | "left" | "moved" | "stage" | "stop" | "merged";

export interface ChangeRecord {
  type: ChangeType;
  blocker?: string | null;
  title?: string;
  game?: string;
  titles?: string[];
  rank?: number;
  was?: number | string | null;
  score?: number;
  was_score?: number;
  stage?: string | null;
  url?: string;
}

export interface FeedItem {
  id: string;
  title?: string;
  content_text?: string;
  date_published?: string;
  _anyps5?: { since?: string | null; changes?: ChangeRecord[]; not_listed?: number };
}

export interface Feed {
  version: string;
  items: FeedItem[];
}
