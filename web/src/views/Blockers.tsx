// Every blocker in one list: the ranking first, then the ones no game is linked to yet, then the
// fixed ones. A row opens the blocker in the drawer.

import { useMemo } from "react";
import {
  BLOCKER_FILTERS,
  BLOCKER_SORTS,
  blockerAccessors,
  filterBlockers,
  type BlockerFilter,
  type BlockerSort,
} from "../data/lists";
import { useData } from "../data/load";
import type { BlockerRow } from "../data/model";
import { fmtDate, plural } from "../lib/format";
import { setParams, type Location } from "../lib/router";
import { formatSort, parseSort, sortRows, type Dir, type Sort } from "../lib/sort";
import { Chips, Empty, ItemLink, SearchField, SortSelect, StatusPill, ViewHead } from "../components/ui";
import { ListKeys } from "./listKeys";

const DEFAULT: Sort<BlockerSort> = { key: "rank", dir: "asc" };

const SORT_OPTIONS: { key: BlockerSort; label: string; dir: Dir }[] = [
  { key: "rank", label: "Rank", dir: "asc" },
  { key: "games", label: "Most games", dir: "desc" },
  { key: "activity", label: "Latest activity", dir: "desc" },
  { key: "title", label: "Title, A to Z", dir: "asc" },
  { key: "area", label: "Area, A to Z", dir: "asc" },
  { key: "status", label: "Fix status", dir: "asc" },
];

export function Blockers({ loc }: { loc: Location }) {
  const { model, resolvedAt } = useData();
  const p = loc.under.params;
  const status = (p.get("status") ?? "open") in BLOCKER_FILTERS ? ((p.get("status") ?? "open") as BlockerFilter) : "open";
  const area = p.get("area") ?? "";
  const q = p.get("q") ?? "";
  const sort = parseSort(p.get("sort"), BLOCKER_SORTS, DEFAULT);

  const openTotal = useMemo(() => model.blockers.filter(BLOCKER_FILTERS.open.test).length, [model]);
  // each filter counts within the other and the search, so a number always says what choosing it shows
  const counts = useMemo(() => {
    const n = {} as Record<BlockerFilter, number>;
    for (const k of Object.keys(BLOCKER_FILTERS) as BlockerFilter[]) n[k] = filterBlockers(model.blockers, { status: k, area, q }).length;
    return n;
  }, [model, area, q]);
  const areas = useMemo(() => {
    const n = new Map<string, number>();
    for (const r of filterBlockers(model.blockers, { status, area: "", q })) n.set(r.area, (n.get(r.area) ?? 0) + 1);
    return [...n].sort((a, z) => z[1] - a[1] || a[0].localeCompare(z[0]));
  }, [model, status, q]);
  const rows = useMemo(
    () => sortRows(filterBlockers(model.blockers, { status, area, q }), blockerAccessors, sort),
    [model, status, area, q, sort],
  );
  const set = (changes: Record<string, string | null>) => setParams(loc, changes);

  return (
    <div className="view">
      <ViewHead title="Blockers" count={String(openTotal)}>
        Open issues in AnyPS5 that stop games, ranked by how many games a fix would move.
      </ViewHead>

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
          .filter((k) => counts[k] || k === status || k === "open")
          .map((k) => ({ value: k, label: BLOCKER_FILTERS[k].label, count: counts[k] }))}
      />
      <div className="list-meta">
        <p className="result" role="status">
          {plural(rows.length, "blocker")}
          {(q || area) && (rows.length === 1 ? " matches" : " match")}
        </p>
        <details className="explain">
          <summary>How the ranking works</summary>
          <p>
            Each open blocker scores 3 points for every game it is the only stop of, 2 for every game it stops first, and 1
            for every game that hits it at all. Games are counted by name, so the region IDs of one game count once.
          </p>
        </details>
      </div>

      {rows.length ? (
        <ListKeys loc={loc}>
          <ul className="rows">
            {rows.map((r) => (
              <li key={r.id}>
                <BlockerRowLink row={r} loc={loc} fixedOn={resolvedAt.get(r.id)} />
              </li>
            ))}
          </ul>
        </ListKeys>
      ) : (
        <Empty
          title={`No blockers match${q ? ` “${q}”` : ""}`}
          hint="Try an issue number such as 2548, a function name or part of an error line."
          onClear={() => set({ q: null, area: null, status: null })}
        />
      )}
    </div>
  );
}

function gamesLine(r: BlockerRow): string {
  if (!r.open) return "";
  if (r.firstStop) return `Stops ${plural(r.firstStop, "game")}`;
  if (r.games) return `Later stop for ${plural(r.games, "game")}`;
  return "No game linked";
}

function BlockerRowLink({ row, loc, fixedOn }: { row: BlockerRow; loc: Location; fixedOn?: string }) {
  const games = gamesLine(row);
  return (
    <ItemLink
      item={{ kind: "blocker", id: row.id }}
      loc={loc}
      className="row blocker-row"
      data-row-link=""
      aria-current={loc.route.item?.id === row.id ? "true" : undefined}
    >
      <span className="b-rank mono">{row.rank != null ? <><span className="sr-only">Rank </span>{row.rank}</> : ""}</span>
      <span className="b-main">
        <span className="row-title">{row.title}</span>
        <span className="row-meta">
          <span className="mono">{row.ref}</span>
          <span>{row.area}</span>
          <StatusPill row={row} />
        </span>
      </span>
      <span className={row.firstStop ? "b-games" : "b-games muted"}>
        {row.open ? games : fixedOn ? `Fixed ${fmtDate(fixedOn)}` : row.lastActivity && `Last activity ${fmtDate(row.lastActivity)}`}
      </span>
    </ItemLink>
  );
}
