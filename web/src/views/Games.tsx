// Every game on the map, one row each: its highest confirmed stage and the issue that stops it now.
// Region IDs of one game collapse into its best row; the drawer lists the others. Unverified claims
// live in the drawer and are never shown as a stage or sorted on.

import { useEffect, useMemo, useRef, useState } from "react";
import { GAME_SORTS, gameAccessors, gameList, onePerGame, stageCounts, type GameSort } from "../data/lists";
import { useData } from "../data/load";
import type { GameRow } from "../data/model";
import { plural } from "../lib/format";
import { setParams, type Location } from "../lib/router";
import { formatSort, parseSort, sortRows, type Dir, type Sort } from "../lib/sort";
import { Chips, Empty, ItemLink, SortSelect, StageMeter, StatusPill } from "../components/ui";
import { ListKeys } from "./listKeys";

const DEFAULT: Sort<GameSort> = { key: "stage", dir: "desc" };
const FIRST_PAGE = 30;

const SORT_OPTIONS: { key: GameSort; label: string; dir: Dir }[] = [
  { key: "stage", label: "Furthest first", dir: "desc" },
  { key: "stage", label: "Earliest first", dir: "asc" },
  { key: "name", label: "Name, A to Z", dir: "asc" },
  { key: "report", label: "Latest report", dir: "desc" },
];

export function GameList({ loc }: { loc: Location }) {
  const { model } = useData();
  const p = loc.under.params;
  const stage = p.get("stage") ?? "all";
  const q = p.get("q") ?? "";
  const sort = parseSort(p.get("sort"), GAME_SORTS, DEFAULT);
  const counts = useMemo(() => stageCounts(onePerGame(model.games)), [model]);
  const rows = useMemo(
    () => sortRows(gameList(model.games, { stage, q }), gameAccessors, sort),
    [model, stage, q, sort],
  );
  const [expanded, setExpanded] = useState(false);
  const filtered = !!q.trim() || stage !== "all";
  const shown = expanded || filtered ? rows : rows.slice(0, FIRST_PAGE);
  const list = useRef<HTMLUListElement>(null);
  const focusAt = useRef<number | null>(null);
  useEffect(() => {
    if (focusAt.current == null) return;
    list.current?.querySelectorAll<HTMLElement>("[data-row-link]")[focusAt.current]?.focus();
    focusAt.current = null;
  }, [expanded]);

  const set = (changes: Record<string, string | null>) => setParams(loc, changes);
  const total = model.stages.length;
  const chips = [
    { value: "all", label: "All", count: counts.get("all") },
    ...[...model.stages].reverse().map((s) => ({ value: s.name, label: s.name, count: counts.get(s.name) ?? 0 })),
    { value: "none", label: "No stage yet", count: counts.get("none") ?? 0 },
  ].filter((c) => c.count || c.value === stage);

  return (
    <section className="section games" aria-labelledby="h-games">
      <div className="section-head">
        <h2 id="h-games">Games</h2>
        <SortSelect options={SORT_OPTIONS} sort={sort} onChange={(s) => set({ sort: s.key === DEFAULT.key && s.dir === DEFAULT.dir ? null : formatSort(s) })} />
      </div>
      <Chips legend="Stage" value={stage} onChange={(v) => set({ stage: v === "all" ? null : v })} chips={chips} />
      <div className="list-meta">
        <p className="result" role="status">
          {resultLine(rows.length, stage, q)}
        </p>
        <details className="explain">
          <summary>What the stages mean</summary>
          <ol className="stage-defs">
            {model.stages.map((s, i) => (
              <li key={s.name}>
                <StageMeter rank={i} total={total} />
                <span className="sd-name">{s.name}</span>
                <span className="sd-def">{s.meaning}</span>
              </li>
            ))}
          </ol>
          <p className="explain-note">
            A stage counts once it is reached on AnyPS5 main. Menus and higher count only after someone checks the report.
          </p>
        </details>
      </div>

      {rows.length ? (
        <ListKeys loc={loc}>
          <div className="rows-head" aria-hidden="true">
            <span>Game</span>
            <span>Stage</span>
            <span>Stops at</span>
          </div>
          <ul className="rows" ref={list}>
            {shown.map((g) => (
              <li key={g.id}>
                <GameRowLink g={g} loc={loc} total={total} />
              </li>
            ))}
          </ul>
          {shown.length < rows.length && (
            <button
              type="button"
              className="btn more-btn"
              onClick={() => {
                focusAt.current = shown.length;
                setExpanded(true);
              }}
            >
              Show all {rows.length} games
            </button>
          )}
        </ListKeys>
      ) : (
        <Empty
          title={`No games match${q ? ` “${q}”` : ""}${stage !== "all" ? ` at ${stage === "none" ? "no stage" : stage}` : ""}`}
          hint="Try a game name, a PPSA ID, an engine such as Unity, an issue number or part of an error line."
          onClear={() => set({ q: null, stage: null })}
        />
      )}
    </section>
  );
}

function resultLine(n: number, stage: string, q: string): string {
  const where = stage === "all" ? "" : stage === "none" ? " without a stage" : ` at ${stage}`;
  return `${plural(n, "game")}${where}${q.trim() ? ` matching “${q.trim()}”` : ""}`;
}

function GameRowLink({ g, loc, total }: { g: GameRow; loc: Location; total: number }) {
  const stop = g.firstStop;
  return (
    <ItemLink
      item={{ kind: "game", id: g.id }}
      loc={loc}
      className="row game-row"
      data-row-link=""
      aria-current={loc.route.item?.id === g.id ? "true" : undefined}
    >
      <span className="g-game">
        <span className="row-title">{g.name}</span>
        <span className="row-meta">
          {g.named && <span className="mono">{g.id}</span>}
          {g.title.engine && <span>{g.title.engine}</span>}
        </span>
      </span>
      <span className="g-stage">
        <StageMeter rank={g.stageRank} total={total} />
        <span className={g.stage ? "stage-name" : "stage-name muted"}>{g.stage ?? "No stage yet"}</span>
      </span>
      <span className="g-stop">
        {stop ? (
          <>
            <span className="g-stop-label">Stops at </span>
            <span className="g-stop-title">{stop.title}</span>
            <span className="row-meta">
              <span className="mono">{stop.ref}</span>
              {g.steps[0].scope && <span>Only on {g.steps[0].scope.join(", ")}</span>}
              {stop.fix.kind !== "none" && <StatusPill row={stop} withRef={false} />}
            </span>
          </>
        ) : (
          <span className="g-stop-title muted">No open blocker known</span>
        )}
      </span>
    </ItemLink>
  );
}
