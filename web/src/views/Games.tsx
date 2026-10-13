// Every game on the map, one row each: its cover, its highest confirmed stage, how sure that stage is, and the
// issue that stops it now. A game holds all of its title IDs (regions, other spellings of its name), so a search
// for any of them finds its one row. Unverified claims live in the drawer and are never shown as a stage or
// sorted on.

import { useEffect, useMemo, useRef, useState } from "react";
import { GAME_SORTS, filterGames, gameAccessors, gameList, stageCounts, tagCounts, type GameSort } from "../data/lists";
import { useData } from "../data/load";
import type { GameRow } from "../data/model";
import { plural } from "../lib/format";
import { setParams, type Location } from "../lib/router";
import { formatSort, parseSort, sortRows, type Dir, type Sort } from "../lib/sort";
import { Chips, Empty, GameTags, ItemLink, SortSelect, StageMeter, StatusPill } from "../components/ui";
import { Cover } from "../components/Cover";
import { ListKeys } from "./listKeys";

const DEFAULT: Sort<GameSort> = { key: "stage", dir: "desc" };
// the groups of the tag menu; Kind holds only App, so the menu says what it means
const TAG_GROUPS = [
  ["Dimension", "Dimension"],
  ["Genre", "Genre"],
  ["Kind", "Not a game"],
] as const;
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
  const tag = p.get("tag") ?? "";
  const q = p.get("q") ?? "";
  const sort = parseSort(p.get("sort"), GAME_SORTS, DEFAULT);
  // each filter counts within the others and the search, so a number always says what choosing it shows
  const games = model.games;
  const counts = useMemo(() => stageCounts(filterGames(games, { stage: "all", tag, q })), [games, tag, q]);
  const tags = useMemo(() => tagCounts(filterGames(games, { stage, q })), [games, stage, q]);
  const tagged = useMemo(() => games.some((g) => g.tags.length), [games]);
  const rows = useMemo(
    () => sortRows(gameList(model.games, { stage, tag, q }), gameAccessors, sort),
    [model, stage, tag, q, sort],
  );
  const [expanded, setExpanded] = useState(false);
  const filtered = !!q.trim() || stage !== "all" || !!tag;
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
  ].filter((c) => c.count || c.value === stage || c.value === "all");

  return (
    <section className="section games" aria-labelledby="h-games">
      <div className="section-head">
        <h2 id="h-games">Games</h2>
        <div className="section-tools">
          {tagged && (
            <label className="select tag-select">
              <span>Tag</span>
              <select value={tag} onChange={(e) => set({ tag: e.target.value || null })}>
                <option value="">All</option>
                {TAG_GROUPS.map(([group, label]) => {
                  const options = model.tags.filter((t) => t.group === group && (tags.get(t.name) || t.name === tag));
                  return options.length ? (
                    <optgroup key={group} label={label}>
                      {options.map((t) => (
                        <option key={t.name} value={t.name}>
                          {t.name} ({tags.get(t.name) ?? 0})
                        </option>
                      ))}
                    </optgroup>
                  ) : null;
                })}
                {tag && !model.tags.some((t) => t.name === tag) && <option value={tag}>{tag} (0)</option>}
              </select>
            </label>
          )}
          <SortSelect options={SORT_OPTIONS} sort={sort} onChange={(s) => set({ sort: s.key === DEFAULT.key && s.dir === DEFAULT.dir ? null : formatSort(s) })} />
        </div>
      </div>
      <Chips legend="Stage" value={stage} onChange={(v) => set({ stage: v === "all" ? null : v })} chips={chips} />
      <div className="list-meta">
        <p className="result" role="status">
          {resultLine(rows.length, stage, tag, q)}
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
          title={`No games${tag ? ` tagged ${tag}` : ""}${stage !== "all" ? ` at ${stage === "none" ? "no stage" : stage}` : ""}${q ? ` match “${q}”` : ""}`}
          hint={
            q || (stage === "all" && !tag)
              ? "Try a game name, a title ID, an engine such as Unity, an issue number or part of an error line."
              : "Pick another tag or stage, or clear the filters."
          }
          onClear={() => set({ q: null, stage: null, tag: null })}
        />
      )}
    </section>
  );
}

function resultLine(n: number, stage: string, tag: string, q: string): string {
  const where = stage === "all" ? "" : stage === "none" ? " without a stage" : ` at ${stage}`;
  return `${plural(n, "game")}${tag ? ` tagged ${tag}` : ""}${where}${q.trim() ? ` matching “${q.trim()}”` : ""}`;
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
        <Cover image={g.game.image} name={g.name} named={g.named} size="row" />
        <span className="row-title">{g.name}</span>
        <span className="row-meta">
          {g.named && (
            <span className="mono">
              {g.ids[0]}
              {g.ids.length > 1 && (
                <>
                  <span className="more-ids" aria-hidden="true">
                    {" "}+{g.ids.length - 1}
                  </span>
                  <span className="sr-only"> and {plural(g.ids.length - 1, "more title ID")}</span>
                </>
              )}
            </span>
          )}
          {g.game.engine && <span>{g.game.engine}</span>}
          <GameTags tags={g.tags} />
        </span>
      </span>
      <span className="g-stage">
        <StageMeter rank={g.stageRank} total={total} />
        <span className={g.stage ? "stage-name" : "stage-name muted"}>{g.stage ?? "No stage yet"}</span>
        {g.sure && <span className="g-sure">{g.sure}</span>}
        {g.offMain && <span className="g-off">{g.offMain.stage} off main</span>}
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
