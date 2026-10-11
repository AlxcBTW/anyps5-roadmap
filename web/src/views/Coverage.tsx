// Coverage: what AnyPS5 implements of the PS5's system libraries and GPU. Loaded on demand, with
// its own stylesheet, the first time someone opens it.

import { useMemo, useState } from "react";
import "./coverage.css";
import { layout, type Tile } from "../coverage/treemap";
import { useData } from "../data/load";
import type { CoverageGroup } from "../data/schema";
import { pct, plural } from "../lib/format";
import { setParams, type Location } from "../lib/router";
import { nextSort, sortRows, type Dir, type Sort } from "../lib/sort";
import { useMedia } from "../lib/useMedia";
import { External, ItemLink, SortHeader, ViewHead } from "../components/ui";
import { CloseIcon } from "../components/Icons";

type Kind = "hle" | "isa";
const UNIT: Record<Kind, string> = { hle: "functions", isa: "instructions" };
const nameOf = (g: CoverageGroup) => g.label || g.library || g.encoding || "?";

export default function Coverage({ loc }: { loc: Location }) {
  const { model } = useData();
  const cov = model.doc.coverage ?? {};
  const hle = cov.hle?.total ? cov.hle : null;
  const isa = cov.isa?.total ? cov.isa : null;
  const pm4 = cov.pm4?.total ? cov.pm4 : null;
  const narrow = useMedia("(max-width: 759px)");
  const sel = loc.under.params.get("sel") ?? "";
  const [selKind, selName] = sel.includes(":") ? (sel.split(/:(.*)/s) as [Kind, string]) : [null, ""];
  const groups = { hle: hle?.groups ?? [], isa: isa?.groups ?? [] };
  const selected = selKind && selKind in groups ? groups[selKind].find((g) => nameOf(g) === selName) : undefined;
  const select = (kind: Kind, g: CoverageGroup | null) => setParams(loc, { sel: g ? `${kind}:${nameOf(g)}` : null });

  if (!hle && !isa && !pm4) {
    return (
      <div className="list-view">
        <ViewHead title="Coverage" />
        <p className="muted">This snapshot was built without coverage data.</p>
      </div>
    );
  }
  const two = !!(hle && isa && !narrow);
  return (
    <div className="list-view coverage">
      <ViewHead title="Coverage">
        What AnyPS5 implements of the PS5's system libraries and GPU. Same data as the project's own{" "}
        <External href="https://boykopovar.github.io/AnyPS5/">progress page</External>.
      </ViewHead>

      <ul className="kpis kpis-3" aria-label="Coverage in numbers">
        {hle && <CovKpi label="System library functions" done={hle.done} total={hle.total} />}
        {isa && <CovKpi label="GPU shader instructions" done={isa.done} total={isa.total} />}
        {pm4 && <CovKpi label="GPU command packets (PM4)" done={pm4.counts.handled ?? 0} total={pm4.total} part={pm4.counts.conditional ?? 0} />}
      </ul>

      {(hle || isa) && (
        <figure className="tm">
          <figcaption className="tm-head">
            <span className="tm-legend" aria-hidden="true">
              <i className="lg-done" />
              Implemented
              <i className="lg-miss" />
              Missing
            </span>
            <span className="tm-hint">One cell per function or instruction. Select a block to list what is missing.</span>
          </figcaption>
          <div className={two ? "tm-panels two" : "tm-panels"}>
            {hle && (
              <CovMap
                kind="hle"
                title="System library functions"
                groups={hle.groups}
                width={two ? 640 : narrow ? 400 : 1000}
                height={narrow ? 440 : 330}
                done={hle.done}
                total={hle.total}
                selected={selKind === "hle" ? selName : ""}
                onSelect={(g) => select("hle", g)}
              />
            )}
            {isa && (
              <CovMap
                kind="isa"
                title="GPU shader instructions"
                groups={isa.groups}
                width={two ? 360 : 400}
                height={two ? 330 : 280}
                done={isa.done}
                total={isa.total}
                selected={selKind === "isa" ? selName : ""}
                onSelect={(g) => select("isa", g)}
              />
            )}
          </div>
        </figure>
      )}

      {selected && selKind && <Selected kind={selKind} g={selected} loc={loc} onClose={() => select(selKind, null)} />}

      {hle && <Asked groups={hle.groups} loc={loc} />}
      {hle && (
        <Libraries
          groups={hle.groups}
          selected={selKind === "hle" ? selName : ""}
          onSelect={(g) => {
            select("hle", g);
            requestAnimationFrame(() => document.getElementById("h-sel")?.focus());
          }}
        />
      )}

      {pm4 && (
        <section className="block" aria-labelledby="h-pm4">
          <div className="block-head">
            <h2 id="h-pm4">GPU command packets (PM4)</h2>
          </div>
          <div className="pm4">
            <span className="cv-bar" aria-hidden="true">
              <i style={{ width: `${(100 * (pm4.counts.handled ?? 0)) / pm4.total}%` }} />
              <i className="part" style={{ width: `${(100 * (pm4.counts.conditional ?? 0)) / pm4.total}%` }} />
            </span>
            <span>
              {pm4.counts.handled ?? 0} of {pm4.total} handled, {pm4.counts.conditional ?? 0} in part.
            </span>
          </div>
          {pm4.rows.some((r) => r.status === "rejected" && r.kind === "type-3") && (
            <p className="small">
              <span className="muted">Rejected: </span>
              <span className="mono">
                {pm4.rows
                  .filter((r) => r.status === "rejected" && r.kind === "type-3")
                  .map((r) => r.name)
                  .join(", ")}
              </span>
            </p>
          )}
        </section>
      )}
    </div>
  );
}

function CovKpi({ label, done, total, part }: { label: string; done: number; total: number; part?: number }) {
  return (
    <li className="kpi kpi-static">
      <span className="kpi-n">{pct(done, total)}</span>
      <span className="kpi-label">{label}</span>
      <span className="kpi-sub">
        {done.toLocaleString("en")} of {total.toLocaleString("en")}
        {part ? `, ${part} in part` : ""}
      </span>
    </li>
  );
}

function CovMap({ kind, title, groups, width, height, done, total, selected, onSelect }: {
  kind: Kind;
  title: string;
  groups: CoverageGroup[];
  width: number;
  height: number;
  done: number;
  total: number;
  selected: string;
  onSelect: (g: CoverageGroup | null) => void;
}) {
  const tiles = useMemo(() => layout(groups, width, height), [groups, width, height]);
  const [tip, setTip] = useState<{ g: CoverageGroup; x: number; y: number } | null>(null);
  const label = `Treemap of ${tiles.length} ${kind === "hle" ? "system libraries" : "shader instruction encodings"}, ${done.toLocaleString("en")} of ${total.toLocaleString("en")} ${UNIT[kind]} implemented`;
  return (
    <div className="tm-panel">
      <h2 className="tm-sub">
        {title} <span className="tm-n">{pct(done, total)}</span>
      </h2>
      <div
        className="tm-area"
        style={{ aspectRatio: `${width} / ${height}` }}
        role="img"
        aria-label={label}
        onPointerLeave={() => setTip(null)}
      >
        {tiles.map((t) => (
          <TileView
            key={nameOf(t.item)}
            t={t}
            selected={nameOf(t.item) === selected}
            onClick={() => onSelect(nameOf(t.item) === selected ? null : t.item)}
            onHover={(x, y) => setTip({ g: t.item, x, y })}
          />
        ))}
      </div>
      {tip && <Tip g={tip.g} x={tip.x} y={tip.y} unit={UNIT[kind]} />}
    </div>
  );
}

function TileView({ t, selected, onClick, onHover }: { t: Tile<CoverageGroup>; selected: boolean; onClick: () => void; onHover: (x: number, y: number) => void }) {
  return (
    <div
      className={selected ? "tm-tile sel" : "tm-tile"}
      style={{
        left: `calc(${t.x}% + 1.5px)`,
        top: `calc(${t.y}% + 1.5px)`,
        width: `calc(${t.w}% - 3px)`,
        height: `calc(${t.h}% - 3px)`,
      }}
      onClick={onClick}
      onPointerMove={(e) => e.pointerType === "mouse" && onHover(e.clientX, e.clientY)}
    >
      {t.bands.map((b, i) => (
        <div
          key={i}
          className={b.grid ? "tm-band grid" : "tm-band"}
          style={{ top: `${b.top}%`, height: `${b.height}%`, ["--c" as string]: b.cols, ["--r" as string]: b.rows }}
        >
          {b.missing.map(([l, tp, w, h], j) => (
            <i key={j} style={{ left: `${l}%`, top: `${tp}%`, width: `${w}%`, height: `${h}%` }} />
          ))}
        </div>
      ))}
      <span className="tm-l">{nameOf(t.item)}</span>
    </div>
  );
}

function Tip({ g, x, y, unit }: { g: CoverageGroup; x: number; y: number; unit: string }) {
  const miss = g.todo_names ?? [];
  const w = 320;
  const left = x + 14 + w > innerWidth - 8 ? x - w - 14 : x + 14;
  return (
    <div className="tm-tip" aria-hidden="true" style={{ left: Math.max(8, left), top: Math.min(y + 14, innerHeight - 160) }}>
      <b>{nameOf(g)}</b>
      <div className="tt-n">
        {g.done} of {g.done + g.todo} {unit}
        {miss.length ? `, ${miss.length} missing` : ""}
      </div>
      {miss.slice(0, 8).map((m) => (
        <div key={m} className="tt-m">
          {m}
        </div>
      ))}
      {miss.length > 8 && <div className="tt-n">and {miss.length - 8} more</div>}
    </div>
  );
}

function IssueLinks({ issues, loc }: { issues: number[]; loc: Location }) {
  const { model } = useData();
  return (
    <span className="issue-links">
      {issues.map((n) =>
        model.blocker(String(n)) ? (
          <ItemLink key={n} item={{ kind: "blocker", id: String(n) }} loc={loc} className="mono">
            #{n}
          </ItemLink>
        ) : (
          <External key={n} href={`https://github.com/${model.repo}/issues/${n}`} className="mono">
            #{n}
          </External>
        ),
      )}
    </span>
  );
}

function Selected({ kind, g, loc, onClose }: { kind: Kind; g: CoverageGroup; loc: Location; onClose: () => void }) {
  const asked = g.requested ?? {};
  const missing = [...(g.todo_names ?? [])].sort((a, z) => Number(z in asked) - Number(a in asked) || a.localeCompare(z));
  return (
    <section className="tm-selected" aria-labelledby="h-sel">
      <div className="block-head">
        <h2 id="h-sel" tabIndex={-1}>
          {nameOf(g)}{" "}
          <span className="tm-n">
            {g.done} of {g.done + g.todo} {UNIT[kind]}
            {g.library && g.label && g.library !== g.label ? ` · ${g.library}` : ""}
          </span>
        </h2>
        <button type="button" className="icon-btn" onClick={onClose}>
          <CloseIcon />
          <span className="sr-only">Close {nameOf(g)}</span>
        </button>
      </div>
      {missing.length ? (
        <ul className="fn-list">
          {missing.map((m) => (
            <li key={m}>
              <span className="mono">{m}</span>
              {asked[m] && (
                <span className="muted small">
                  asked in <IssueLinks issues={asked[m]} loc={loc} />
                </span>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">Nothing missing.</p>
      )}
    </section>
  );
}

type AskedKey = "fn" | "lib" | "issues";

function Asked({ groups, loc }: { groups: CoverageGroup[]; loc: Location }) {
  const rows = useMemo(
    () =>
      groups
        .flatMap((g) => Object.entries(g.requested ?? {}).map(([fn, issues]) => ({ fn, lib: nameOf(g), issues })))
        .sort((a, z) => z.issues.length - a.issues.length || a.lib.localeCompare(z.lib) || a.fn.localeCompare(z.fn)),
    [groups],
  );
  const [sort, setSort] = useState<Sort<AskedKey>>({ key: "issues", dir: "desc" });
  const sorted = useMemo(
    () => sortRows(rows, { fn: (r) => r.fn, lib: (r) => r.lib, issues: (r) => r.issues.length }, sort),
    [rows, sort],
  );
  if (!rows.length) return null;
  const onSort = (k: AskedKey, natural: Dir) => setSort(nextSort(sort, k, natural));
  return (
    <details className="block disclose">
      <summary>
        <h2>
          Missing functions that open issues ask for <span className="h-n">{rows.length}</span>
        </h2>
      </summary>
      <table className="table small-table">
        <thead>
          <tr>
            <SortHeader k="fn" label="Function" sort={sort} natural="asc" onSort={onSort} className="c-main" />
            <SortHeader k="lib" label="Library" sort={sort} natural="asc" onSort={onSort} />
            <SortHeader k="issues" label="Asked in" sort={sort} natural="desc" onSort={onSort} />
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={`${r.lib}/${r.fn}`}>
              <td className="c-main mono">{r.fn}</td>
              <td data-label="Library">{r.lib}</td>
              <td data-label="Asked in">
                <IssueLinks issues={r.issues} loc={loc} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}

type LibKey = "lib" | "done" | "todo";

function Libraries({ groups, selected, onSelect }: { groups: CoverageGroup[]; selected: string; onSelect: (g: CoverageGroup) => void }) {
  const rows = useMemo(() => groups.filter((g) => g.todo), [groups]);
  const [sort, setSort] = useState<Sort<LibKey>>({ key: "todo", dir: "desc" });
  const sorted = useMemo(
    () => sortRows(rows, { lib: nameOf, done: (g) => g.done / (g.done + g.todo), todo: (g) => g.todo }, sort),
    [rows, sort],
  );
  if (!rows.length) return null;
  const onSort = (k: LibKey, natural: Dir) => setSort(nextSort(sort, k, natural));
  return (
    <details className="block disclose">
      <summary>
        <h2>
          Libraries with missing functions <span className="h-n">{rows.length}</span>
        </h2>
      </summary>
      <table className="table small-table">
        <thead>
          <tr>
            <SortHeader k="lib" label="Library" sort={sort} natural="asc" onSort={onSort} className="c-main" />
            <SortHeader k="done" label="Implemented" sort={sort} natural="desc" onSort={onSort} />
            <SortHeader k="todo" label="Missing" sort={sort} natural="desc" onSort={onSort} className="c-num" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((g) => (
            <tr key={nameOf(g)} aria-current={nameOf(g) === selected ? "true" : undefined}>
              <td className="c-main">
                <button type="button" className="link-btn" onClick={() => onSelect(g)}>
                  {nameOf(g)}
                </button>
              </td>
              <td data-label="Implemented">
                <span className="lib-done">
                  <span className="cv-bar" aria-hidden="true">
                    <i style={{ width: `${(100 * g.done) / (g.done + g.todo)}%` }} />
                  </span>
                  <span className="mono">
                    {g.done}/{g.done + g.todo}
                  </span>
                </span>
              </td>
              <td className="c-num mono" data-label="Missing">
                {plural(g.todo, "function")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}
