// Every blocker in one sortable table: the ranking, the ones no game is linked to yet, and the
// resolved ones. A row opens the blocker in the drawer.

import { useMemo, type ReactNode } from "react";
import {
  BLOCKER_FILTERS,
  BLOCKER_SORTS,
  blockerAccessors,
  blockerNatural,
  filterBlockers,
  type BlockerFilter,
  type BlockerSort,
} from "../data/lists";
import { useData } from "../data/load";
import { fmtDate, plural } from "../lib/format";
import { setParams, type Location } from "../lib/router";
import { formatSort, nextSort, parseSort, sortRows, type Dir, type Sort } from "../lib/sort";
import { Chips, Dots, Empty, ItemLink, SearchField, SortHeader, SortSelect, StatusPill, ViewHead } from "../components/ui";
import { ListKeys } from "./listKeys";

const DEFAULT: Sort<BlockerSort> = { key: "rank", dir: "asc" };

const SORT_OPTIONS: { key: BlockerSort; label: string; dir: Dir }[] = [
  { key: "rank", label: "Rank", dir: "asc" },
  { key: "games", label: "Most games", dir: "desc" },
  { key: "score", label: "Highest score", dir: "desc" },
  { key: "activity", label: "Latest activity", dir: "desc" },
  { key: "title", label: "Title, A to Z", dir: "asc" },
  { key: "area", label: "Area, A to Z", dir: "asc" },
  { key: "status", label: "Fix status", dir: "asc" },
];

export function Blockers({ loc }: { loc: Location }) {
  const { model } = useData();
  const p = loc.under.params;
  const status = (p.get("status") ?? "open") in BLOCKER_FILTERS ? ((p.get("status") ?? "open") as BlockerFilter) : "open";
  const area = p.get("area") ?? "";
  const q = p.get("q") ?? "";
  const sort = parseSort(p.get("sort"), BLOCKER_SORTS, DEFAULT);

  const counts = useMemo(() => {
    const n = {} as Record<BlockerFilter, number>;
    for (const k of Object.keys(BLOCKER_FILTERS) as BlockerFilter[]) n[k] = model.blockers.filter(BLOCKER_FILTERS[k].test).length;
    return n;
  }, [model]);
  const areas = useMemo(() => {
    const n = new Map<string, number>();
    for (const r of model.blockers) if (BLOCKER_FILTERS[status].test(r)) n.set(r.area, (n.get(r.area) ?? 0) + 1);
    return [...n].sort((a, z) => z[1] - a[1] || a[0].localeCompare(z[0]));
  }, [model, status]);
  const rows = useMemo(
    () => sortRows(filterBlockers(model.blockers, { status, area, q }), blockerAccessors, sort),
    [model, status, area, q, sort],
  );

  const set = (changes: Record<string, string | null>) => setParams(loc, changes);
  const onSort = (k: BlockerSort, natural: Dir) => {
    const s = nextSort(sort, k, natural);
    set({ sort: k === DEFAULT.key && s.dir === DEFAULT.dir ? null : formatSort(s) });
  };
  const resolvedView = status === "resolved";
  const head = (k: BlockerSort, label: ReactNode, className?: string) => (
    <SortHeader k={k} label={label} sort={sort} natural={blockerNatural[k]} onSort={onSort} className={className} />
  );

  return (
    <div className="list-view">
      <ViewHead title="Blockers" count={String(counts.open)}>
        Open issues and PRs that stop games, ranked by how many games a fix moves.
      </ViewHead>
      <details className="explain">
        <summary>How the ranking works</summary>
        <p>
          Score = 3 × games for which it is the only stop left + 2 × games it stops first + every game that lists it.
          Games are counted by name, so the region IDs of one game count once. In the dots, a filled dot is a game it
          stops first, a hollow one a game that hits it later.
        </p>
      </details>

      <div className="toolbar">
        <SearchField label="Search blockers" placeholder="Issue number, title or error line" value={q} onChange={(v) => set({ q: v || null })} />
        <label className="select">
          <span>Area</span>
          <select value={area} onChange={(e) => set({ area: e.target.value || null })}>
            <option value="">All areas</option>
            {areas.map(([a, n]) => (
              <option key={a} value={a}>
                {a} ({n})
              </option>
            ))}
            {area && !areas.some(([a]) => a === area) && <option value={area}>{area} (0)</option>}
          </select>
        </label>
        <SortSelect options={SORT_OPTIONS} sort={sort} onChange={(s) => set({ sort: s.key === DEFAULT.key && s.dir === DEFAULT.dir ? null : formatSort(s) })} />
      </div>
      <Chips
        legend="Show"
        value={status}
        onChange={(v) => set({ status: v === "open" ? null : v })}
        chips={(Object.keys(BLOCKER_FILTERS) as BlockerFilter[])
          .filter((k) => counts[k] || k === status)
          .map((k) => ({ value: k, label: BLOCKER_FILTERS[k].label, count: counts[k] }))}
      />
      <p className="result" role="status">
        {plural(rows.length, "blocker")}
        {(q || area) && " match"}
      </p>

      {rows.length ? (
        <ListKeys loc={loc}>
          <table className="table blockers-table">
            <thead>
              <tr>
                {head("rank", <>#<span className="sr-only"> Rank</span></>, "c-rank")}
                {head("title", "Blocker", "c-main")}
                {head("area", "Area", "c-area")}
                {head("status", "Fix", "c-status")}
                {!resolvedView && head("games", "Games", "c-games")}
                {!resolvedView && head("score", "Score", "c-num")}
                {head("activity", "Last activity", "c-date")}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} aria-current={loc.route.item?.id === r.id ? "true" : undefined}>
                  <td className="c-rank mono" data-label="Rank">
                    {r.rank != null ? String(r.rank).padStart(2, "0") : "–"}
                  </td>
                  <td className="c-main">
                    <ItemLink item={{ kind: "blocker", id: r.id }} loc={loc} className="row-link" data-row-link="">
                      {r.title}
                    </ItemLink>
                    <span className="row-sub">
                      <span className="mono">{r.ref}</span>
                      <span className="sub-area">{r.area}</span>
                      {r.blocker.signature && <span className="sig-line mono">{r.blocker.signature}</span>}
                    </span>
                  </td>
                  <td className="c-area" data-label="Area">{r.area}</td>
                  <td className="c-status" data-label="Fix">
                    <StatusPill row={r} />
                  </td>
                  {!resolvedView && (
                    <td className="c-games" data-label="Games">
                      {r.games ? (
                        <span className="games-cell">
                          <Dots dots={r.dots} max={8} />
                          <span className="mono">{r.games}</span>
                          <span className="sr-only">
                            {" "}games, first stop for {r.firstStop}
                          </span>
                        </span>
                      ) : (
                        <span className="muted">None linked</span>
                      )}
                    </td>
                  )}
                  {!resolvedView && (
                    <td className="c-num mono" data-label="Score">
                      {r.games ? r.score : "–"}
                    </td>
                  )}
                  <td className="c-date" data-label="Last activity">
                    {fmtDate(r.lastActivity)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ListKeys>
      ) : (
        <Empty
          title={`No blockers match${q ? ` “${q}”` : ""}`}
          hint="Try an issue number, part of an error line, or another area or status."
          onClear={() => set({ q: null, area: null, status: null })}
        />
      )}
    </div>
  );
}
