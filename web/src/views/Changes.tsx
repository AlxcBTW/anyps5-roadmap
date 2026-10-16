// What each snapshot changed, from feed.json, newest first. Every row opens its blocker or game.

import { useMemo, useState } from "react";
import { CHANGE_GROUPS, CHANGE_LABELS, type ChangeGroup, type ChangeRow } from "../data/feed";
import { useData } from "../data/load";
import { fmtTime, plural } from "../lib/format";
import { setParams, type Location } from "../lib/router";
import { Chips, Empty, ItemLink, ViewHead } from "../components/ui";

const ROWS_SHOWN = 6; // per snapshot, until someone asks for the rest
const SNAPSHOTS_SHOWN = 10;

const GROUP_LABELS: Record<ChangeGroup, string> = { resolved: "Fixed", ranking: "Ranking", games: "Games" };

function inGroup(r: ChangeRow, g: string): boolean {
  return g === "all" || (CHANGE_GROUPS[g as ChangeGroup] as readonly string[] | undefined)?.includes(r.type) === true;
}

export function Changes({ loc }: { loc: Location }) {
  const { snapshots, feed } = useData();
  const group = loc.under.params.get("type") ?? "all";
  const counts = useMemo(() => {
    const n: Record<string, number> = { all: 0 };
    for (const s of snapshots)
      for (const r of s.rows) {
        n.all++;
        for (const g of Object.keys(CHANGE_GROUPS)) if (inGroup(r, g)) n[g] = (n[g] ?? 0) + 1;
      }
    return n;
  }, [snapshots]);
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(new Set());
  const [older, setOlder] = useState(false);
  const matching = snapshots
    .map((s) => ({ ...s, rows: s.rows.filter((r) => inGroup(r, group)) }))
    .filter((s) => s.rows.length || (group === "all" && s.notListed));
  const shown = older ? matching : matching.slice(0, SNAPSHOTS_SHOWN);

  return (
    <div className="list-view">
      <ViewHead title="Changes">
        What each snapshot changed: blockers resolved, moves in the ranking, and games whose stage or first stop
        changed. Also as a <a href="feed.json">JSON feed</a>.
      </ViewHead>
      {feed === "loading" && <p className="result" role="status">Loading the change feed…</p>}
      {(feed === "missing" || feed === "error") && (
        <Empty
          title={feed === "missing" ? "No change feed in this build" : "Unable to load feed.json"}
          hint={
            feed === "missing"
              ? "Offline builds skip feed.json; the live site adds an entry whenever a build changes something."
              : "Check your connection and reload the page."
          }
        />
      )}
      {feed === "ready" && !snapshots.length && (
        <Empty title="No changes recorded yet" hint="An entry appears here when a build changes the ranking, a stage or a stop." />
      )}
      {snapshots.length > 0 && (
        <>
          <Chips
            legend="Show"
            value={group}
            onChange={(v) => setParams(loc, { type: v === "all" ? null : v })}
            chips={[
              { value: "all", label: "All", count: counts.all },
              ...(Object.keys(CHANGE_GROUPS) as ChangeGroup[]).map((g) => ({ value: g, label: GROUP_LABELS[g], count: counts[g] ?? 0 })),
            ].filter((c) => c.count || c.value === group)}
          />
          <ol className="timeline">
            {shown.map((s) => (
              <li key={s.id} className="snap-item">
                <header className="snap-head">
                  <h2>
                    <time dateTime={s.date}>{fmtTime(s.date)}</time>
                  </h2>
                  <span className="muted">{s.summary}</span>
                </header>
                <ul className="changes">
                  {(expanded.has(s.id) ? s.rows : s.rows.slice(0, ROWS_SHOWN)).map((r) => (
                    <li key={r.key}>
                      <span className={`tag tag-change tag-${r.type}`}>{CHANGE_LABELS[r.type]}</span>
                      {r.item ? (
                        <ItemLink item={r.item} loc={loc} className="change-text">
                          {r.text}
                        </ItemLink>
                      ) : (
                        <span className="change-text">{r.text}</span>
                      )}
                    </li>
                  ))}
                </ul>
                {!expanded.has(s.id) && s.rows.length > ROWS_SHOWN && (
                  <button type="button" className="link-btn more-changes" onClick={() => setExpanded(new Set(expanded).add(s.id))}>
                    Show all {s.rows.length} changes<span className="sr-only"> of {fmtTime(s.date)}</span>
                  </button>
                )}
                {group === "all" && s.notListed > 0 && (
                  <p className="muted small">And {plural(s.notListed, "more change")}, not listed in the feed.</p>
                )}
              </li>
            ))}
          </ol>
          {shown.length < matching.length && (
            <button type="button" className="btn more-btn" onClick={() => setOlder(true)}>
              Show {matching.length - shown.length} older snapshots
            </button>
          )}
        </>
      )}
    </div>
  );
}
