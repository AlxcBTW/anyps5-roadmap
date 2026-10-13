// feed.json (anyps5_roadmap/feed.py) as rows the Changes view and the roadmap board read.

import type { ChangeRecord, ChangeType, Feed } from "./schema";

export interface ChangeRow {
  key: string;
  type: ChangeType;
  text: string; // the feed's own sentence for this change
  item: { kind: "blocker" | "game"; id: string } | null; // what the row opens
}

export interface Snapshot {
  id: string;
  date: string; // when the build that saw these changes ran
  since: string | null; // the snapshot it compares with
  summary: string; // "2 ranking changes, 1 title changed"
  rows: ChangeRow[];
  notListed: number;
}

export const CHANGE_LABELS: Record<ChangeType, string> = {
  resolved: "Fixed",
  entered: "Entered",
  left: "Left",
  moved: "Moved",
  stage: "Stage",
  stop: "Stop",
  merged: "Merged",
};

/** The groups of the Changes filter: what a reader asks for, not the seven record types. */
export const CHANGE_GROUPS = {
  resolved: ["resolved"],
  ranking: ["entered", "left", "moved"],
  games: ["stage", "stop", "merged"],
} as const satisfies Record<string, readonly ChangeType[]>;

export type ChangeGroup = keyof typeof CHANGE_GROUPS;

function itemOf(r: ChangeRecord): ChangeRow["item"] {
  if ((r.type === "stage" || r.type === "stop" || r.type === "merged") && (r.game || r.title))
    return { kind: "game", id: (r.game ?? r.title)! };
  if (r.blocker) return { kind: "blocker", id: r.blocker };
  return null;
}

function fallbackText(r: ChangeRecord): string {
  const subject = r.title ?? r.blocker ?? "";
  switch (r.type) {
    case "resolved":
      return `${subject} is resolved.`;
    case "entered":
      return `${subject} entered the ranking at No. ${r.rank}.`;
    case "left":
      return `${subject} left the ranking (was No. ${r.was}).`;
    case "moved":
      return `${subject} moved from No. ${r.was} to No. ${r.rank}.`;
    case "stage":
      return `${subject} is at ${r.stage ?? "no stage"} now.`;
    case "stop":
      return `${subject} now stops at ${r.blocker ?? "nothing known"}.`;
    case "merged":
      return `${subject} now holds ${(r.titles ?? []).join(", ")} as one game.`;
  }
}

/** Snapshots newest first. Unknown record types and malformed items are skipped, never thrown on. */
export function snapshots(feed: Feed | null | undefined): Snapshot[] {
  const out: Snapshot[] = [];
  for (const it of feed?.items ?? []) {
    if (!it || typeof it.id !== "string") continue;
    const records = (it._anyps5?.changes ?? []).filter((r) => r && r.type in CHANGE_LABELS);
    const lines = (it.content_text ?? "").split("\n");
    out.push({
      id: it.id,
      date: it.date_published ?? it.id,
      since: it._anyps5?.since ?? null,
      summary: it.title ?? "",
      rows: records.map((r, i) => ({
        key: `${it.id}/${i}`,
        type: r.type,
        // feed.py writes one line per listed record, in the same order
        text: lines.length > i && lines[i] ? lines[i] : fallbackText(r),
        item: itemOf(r),
      })),
      notListed: it._anyps5?.not_listed ?? 0,
    });
  }
  return out.sort((a, z) => z.date.localeCompare(a.date));
}

/** The date of the oldest snapshot that lists each blocker as resolved. */
export function resolvedAt(feed: Feed | null | undefined): Map<string, string> {
  const at = new Map<string, string>();
  for (const s of snapshots(feed).reverse()) {
    for (const r of s.rows) {
      if (r.type === "resolved" && r.item?.kind === "blocker" && !at.has(r.item.id)) at.set(r.item.id, s.date);
    }
  }
  return at;
}
