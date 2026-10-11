// What each snapshot changed, from feed.json, newest first. Every row opens its blocker or game.

import { useMemo } from "react";
import { CHANGE_GROUPS, CHANGE_LABELS, type ChangeGroup, type ChangeRow } from "../data/feed";
import { useData } from "../data/load";
import { fmtTime, plural } from "../lib/format";
import { setParams, type Location } from "../lib/router";
import { Chips, Empty, ItemLink, ViewHead } from "../components/ui";

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
  const shown = snapshots
    .map((s) => ({ ...s, rows: s.rows.filter((r) => inGroup(r, group)) }))
    .filter((s) => s.rows.length || (group === "all" && s.notListed));

  return (
    <div className="list-view">
      <ViewHead title="Changes" count={snapshots.length ? String(counts.all) : undefined}>
        What each hourly snapshot changed: blockers resolved, moves in the ranking, and games whose stage or first stop
        changed. Also as a <a href="feed.json">JSON feed</a>.
      </ViewHead>
      {feed === "loading" && <p className="result" role="status">Loading the change feed…</p>}
      {(feed === "missing" || feed === "error") && (
        <Empty
          title={feed === "missing" ? "No change feed in this build" : "Unable to load feed.json"}
          hint={
            feed === "missing"
              ? "Offline builds skip feed.json; the live site adds an entry whenever an hourly build changes something."
              : "Check your connection and reload the page."
          }
        />
      )}
      {feed === "ready" && !snapshots.length && (
        <Empty title="No changes recorded yet" hint="An entry appears here when an hourly build changes the ranking, a stage or a stop." />
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
                  {s.rows.map((r) => (
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
                {group === "all" && s.notListed > 0 && (
                  <p className="muted small">And {plural(s.notListed, "more change")}, not listed in the feed.</p>
                )}
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
