// One row per title ID: the highest confirmed stage, where it stops now and what follows.
// Unverified claims show as a marked note and are never sorted on.

import { useMemo } from "react";
import { GAME_SORTS, filterGames, gameAccessors, gameCount, gameNatural, stageCounts, type GameSort } from "../data/lists";
import { useData } from "../data/load";
import { fmtDate, plural } from "../lib/format";
import { setParams, type Location } from "../lib/router";
import { formatSort, nextSort, parseSort, sortRows, type Dir, type Sort } from "../lib/sort";
import { Chips, Empty, ItemLink, Pips, SearchField, SortHeader, SortSelect, ViewHead } from "../components/ui";
import { ListKeys } from "./listKeys";

const DEFAULT: Sort<GameSort> = { key: "stage", dir: "desc" };

const SORT_OPTIONS: { key: GameSort; label: string; dir: Dir }[] = [
  { key: "stage", label: "Highest stage", dir: "desc" },
  { key: "stage", label: "Lowest stage", dir: "asc" },
  { key: "name", label: "Name, A to Z", dir: "asc" },
  { key: "stop", label: "Stop, by rank", dir: "asc" },
  { key: "chain", label: "Most stops", dir: "desc" },
  { key: "report", label: "Latest report", dir: "desc" },
];

export function Games({ loc }: { loc: Location }) {
  const { model } = useData();
  const p = loc.under.params;
  const stage = p.get("stage") ?? "all";
  const q = p.get("q") ?? "";
  const sort = parseSort(p.get("sort"), GAME_SORTS, DEFAULT);
  const counts = useMemo(() => stageCounts(model.games), [model]);
  const rows = useMemo(
    () => sortRows(filterGames(model.games, { stage, q }), gameAccessors, sort),
    [model, stage, q, sort],
  );
  const set = (changes: Record<string, string | null>) => setParams(loc, changes);
  const onSort = (k: GameSort, natural: Dir) => {
    const s = nextSort(sort, k, natural);
    set({ sort: k === DEFAULT.key && s.dir === DEFAULT.dir ? null : formatSort(s) });
  };
  const head = (k: GameSort, label: string, className?: string) => (
    <SortHeader k={k} label={label} sort={sort} natural={gameNatural[k]} onSort={onSort} className={className} />
  );
  const stages = model.stages.length;
  const chips = [
    { value: "all", label: "All", count: counts.get("all") },
    ...[...model.stages].reverse().map((s) => ({ value: s.name, label: s.name, count: counts.get(s.name) ?? 0 })),
    { value: "none", label: "No stage yet", count: counts.get("none") ?? 0 },
  ].filter((c) => c.count || c.value === stage);

  return (
    <div className="list-view">
      <ViewHead title="Games" count={String(model.counts.games)}>
        The highest stage confirmed on AnyPS5 main for each title ID, and what stops it now.
      </ViewHead>
      <details className="explain">
        <summary>What the stages mean</summary>
        <ol className="stage-defs">
          {model.ladder.map((r, i) => (
            <li key={r.stage.name}>
              <Pips rank={i} total={stages} />
              <span className="sd-name">{r.stage.name}</span>
              <span className="sd-def">{r.stage.meaning}</span>
              {r.heldBy && (
                <span className="sd-held muted">
                  {plural(r.heldBy.games, "game")} here {r.heldBy.games === 1 ? "stops" : "stop"} first at{" "}
                  <ItemLink item={{ kind: "blocker", id: r.heldBy.row.id }} loc={loc} className="mono">
                    {r.heldBy.row.ref}
                  </ItemLink>
                </span>
              )}
            </li>
          ))}
        </ol>
        <p className="muted small">
          Mined stages of Menus or higher count only after someone reviews them; until then they show as unverified claims.
        </p>
      </details>

      <div className="toolbar">
        <SearchField label="Search games and errors" placeholder="Game, PPSA ID, engine or log line" value={q} onChange={(v) => set({ q: v || null })} />
        <SortSelect options={SORT_OPTIONS} sort={sort} onChange={(s) => set({ sort: s.key === DEFAULT.key && s.dir === DEFAULT.dir ? null : formatSort(s) })} />
      </div>
      <Chips legend="Stage" value={stage} onChange={(v) => set({ stage: v === "all" ? null : v })} chips={chips} />
      <p className="result" role="status">
        {plural(gameCount(rows), "game")} in {plural(rows.length, "title ID")}
      </p>

      {rows.length ? (
        <ListKeys loc={loc}>
          <table className="table games-table">
            <thead>
              <tr>
                {head("name", "Game", "c-main")}
                {head("stage", "Stage", "c-stage")}
                {head("stop", "Stops at", "c-stop")}
                {head("chain", "Stops left", "c-num")}
                {head("report", "Last report", "c-date")}
              </tr>
            </thead>
            <tbody>
              {rows.map((g) => (
                <tr key={g.id} aria-current={loc.route.item?.id === g.id ? "true" : undefined}>
                  <td className="c-main">
                    <ItemLink item={{ kind: "game", id: g.id }} loc={loc} className="row-link" data-row-link="">
                      {g.name}
                    </ItemLink>
                    <span className="row-sub">
                      {g.named && <span className="mono">{g.id}</span>}
                      {g.title.engine && <span>{g.title.engine}</span>}
                    </span>
                  </td>
                  <td className="c-stage" data-label="Stage">
                    <span className="stage">
                      <Pips rank={g.stageRank} total={stages} />
                      <span className={g.stage ? undefined : "muted"}>{g.stage ?? "No stage yet"}</span>
                    </span>
                    {(g.reports || g.claim) && (
                      <span className="row-sub">
                        {g.reports && <span>{g.reports}</span>}
                        {g.claim && <span className="claim-note">Claims {g.claim.stage}, unverified</span>}
                      </span>
                    )}
                  </td>
                  <td className="c-stop" data-label="Stops at">
                    {g.firstStop ? (
                      <>
                        <span className="stop-line">
                          <span className="mono">{g.firstStop.ref}</span> {g.firstStop.title}
                        </span>
                        {g.steps[0].scope && <span className="row-sub">{g.steps[0].scope.join(", ")}</span>}
                      </>
                    ) : (
                      <span className="muted">None known</span>
                    )}
                  </td>
                  <td className="c-num mono" data-label="Stops left">
                    {g.steps.length || "–"}
                  </td>
                  <td className="c-date" data-label="Last report">
                    {fmtDate(g.lastReport)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ListKeys>
      ) : (
        <Empty
          title={`No title IDs match${q ? ` “${q}”` : ""}${stage !== "all" ? ` at ${stage === "none" ? "no stage" : stage}` : ""}`}
          hint="Try a game name, a PPSA ID, an engine such as Unity, an issue number or part of an error line."
          onClear={() => set({ q: null, stage: null })}
        />
      )}
    </div>
  );
}
