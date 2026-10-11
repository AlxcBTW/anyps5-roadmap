// The shape of site/roadmap.json (schema_version 1, written by anyps5_roadmap/assemble.py) and of
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
  score: number;
  parent?: number;
}

export interface Evidence {
  stage: string;
  os?: string | null;
  gpu?: string | null;
  build?: string | null;
  url: string;
  date?: string | null;
  note?: string | null;
  quote?: string | null;
  origin?: Origin;
  verified?: boolean;
  author?: string | null;
  part?: string | null;
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

export interface Confidence {
  stage: string | null;
  reports_on_main: number | null;
  authors: string[];
  claim?: { stage: string; reports_on_main: number; reports_on_branches: number };
  label: string | null; // "2 reports on main"
}

export interface Title {
  id: string; // PPSA + 5 digits
  name: string | null;
  engine: string | null;
  kind: "retail" | "homebrew" | null;
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

export interface Stage {
  name: string;
  rank: number;
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
  stats: Record<string, unknown> & {
    issues_scanned?: number;
    prs_scanned?: number;
    titles?: number;
    stage_reviews?: number;
  };
  ranking: string[];
  blockers: Blocker[];
  titles: Title[];
  coverage: Coverage | null;
  not_blockers?: { issue: number; reason: string }[];
  gaps?: string[];
  sources?: Record<string, string>;
}

export type ChangeType = "resolved" | "entered" | "left" | "moved" | "stage" | "stop";

export interface ChangeRecord {
  type: ChangeType;
  blocker?: string | null;
  title?: string;
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
