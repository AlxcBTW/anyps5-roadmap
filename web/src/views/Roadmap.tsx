// The landing view: how far games get, what is being fixed, what comes next. Numbers and labels,
// one sentence; everything dense lives on the other views.

import { useMemo, type ReactNode } from "react";
import { board } from "../data/lists";
import { useData } from "../data/load";
import type { BlockerRow } from "../data/model";
import { fmtDate, plural } from "../lib/format";
import { viewHref, type Location } from "../lib/router";
import { ArrowIcon } from "../components/Icons";
import { ItemLink, Pips, StatusPill, ViewLink } from "../components/ui";
import { useMedia } from "../lib/useMedia";

export function Roadmap({ loc }: { loc: Location }) {
  const { model, resolvedAt } = useData();
  const lanes = useMemo(() => board(model, resolvedAt), [model, resolvedAt]);
  const c = model.counts;
  const days = model.doc.window?.days ?? 60;
  const stages = model.stages.length;
  const size = useMedia("(max-width: 759px)") ? 3 : 5; // cards per lane

  return (
    <div className="roadmap">
      <header className="hero">
        <h1>How far PS5 games get in AnyPS5</h1>
        <p className="lede">AnyPS5 ports PS5 executables to Linux and Windows; this map shows what stops each game and what is being fixed.</p>
      </header>

      <ul className="kpis" aria-label="In numbers">
        <Kpi to={viewHref("games")} n={c.games} label="games tracked" sub={`${c.gamesWithStage} with a confirmed stage`} />
        <Kpi to={viewHref("blockers")} n={c.open} label="open blockers" sub={`stop ${plural(c.gamesWaiting, "game")}`} />
        <Kpi to={viewHref("blockers", { status: "review" })} n={c.inReview} label="fixes in review" sub="open fix PRs" />
        <Kpi to={viewHref("blockers", { status: "resolved" })} n={c.resolved} label="fixed" sub={`in the last ${days} days`} />
      </ul>

      <section className="block" aria-labelledby="h-ladder">
        <div className="block-head">
          <h2 id="h-ladder">Games by stage</h2>
          <ViewLink to={viewHref("games")} className="more-link">
            All games <ArrowIcon />
          </ViewLink>
        </div>
        <ol className="ladder">
          {model.ladder.map((r, i) => {
            const inner = (
              <>
                <Pips rank={i} total={stages} />
                <span className="r-n">{r.games}</span>
                <span className="r-name">{r.stage.name}</span>
              </>
            );
            return (
              <li key={r.stage.name} className={r.games ? undefined : "zero"}>
                {r.games ? (
                  <ViewLink to={viewHref("games", { stage: r.stage.name })} className="rung" title={r.stage.meaning}>
                    <span className="sr-only">Show the </span>
                    {inner}
                    <span className="sr-only"> games</span>
                  </ViewLink>
                ) : (
                  <span className="rung" title={r.stage.meaning}>
                    {inner}
                  </span>
                )}
              </li>
            );
          })}
        </ol>
        {model.noStage > 0 && (
          <p className="ladder-note">
            <ViewLink to={viewHref("games", { stage: "none" })}>{plural(model.noStage, "more game")}</ViewLink>
            <span className="muted"> without a confirmed stage</span>
          </p>
        )}
      </section>

      <section className="block" aria-labelledby="h-board">
        <div className="block-head">
          <h2 id="h-board">Blockers by status</h2>
          <ViewLink to={viewHref("blockers")} className="more-link">
            Full ranking <ArrowIcon />
          </ViewLink>
        </div>
        <div className="board">
          <Lane
            id="review"
            title="In review"
            caption="A fix PR is open"
            size={size}
            count={lanes.review.length}
            more={viewHref("blockers", { status: "review" })}
          >
            {lanes.review.slice(0, size).map((r) => (
              <Card key={r.id} row={r} loc={loc} />
            ))}
          </Lane>
          <Lane
            id="next"
            title="Next up"
            caption="Highest ranked without an open fix"
            size={size}
            count={lanes.next.length}
            more={viewHref("blockers", { status: "nofix" })}
          >
            {lanes.next.slice(0, size).map((r) => (
              <Card key={r.id} row={r} loc={loc} />
            ))}
          </Lane>
          <Lane
            id="fixed"
            title="Recently fixed"
            caption={`Resolved in the last ${days} days`}
            size={size}
            count={lanes.fixed.length}
            more={viewHref("blockers", { status: "resolved" })}
          >
            {lanes.fixed.slice(0, size).map((f) => (
              <Card key={f.row.id} row={f.row} loc={loc} date={f.date} fromFeed={f.fromFeed} />
            ))}
          </Lane>
        </div>
      </section>
    </div>
  );
}

function Kpi({ to, n, label, sub }: { to: string; n: number; label: string; sub: string }) {
  return (
    <li>
      <ViewLink to={to} className="kpi">
        <span className="kpi-n">{n.toLocaleString("en")}</span>
        <span className="kpi-label">{label}</span>
        <span className="kpi-sub">{sub}</span>
      </ViewLink>
    </li>
  );
}

function Lane({ id, title, caption, count, size, more, children }: { id: string; title: string; caption: string; count: number; size: number; more: string; children: ReactNode }) {
  return (
    <section className="lane" aria-labelledby={`lane-${id}`}>
      <header className="lane-head">
        <h3 id={`lane-${id}`}>
          {title} <span className="lane-n">{count}</span>
        </h3>
        <p className="lane-cap">{caption}</p>
      </header>
      {count ? <ol className="cards">{children}</ol> : <p className="lane-empty">Nothing here in this snapshot.</p>}
      {count > size && (
        <ViewLink to={more} className="lane-more">
          All {count} <ArrowIcon />
        </ViewLink>
      )}
    </section>
  );
}

function gamesLine(r: BlockerRow): string {
  if (r.firstStop) return `Stops ${plural(r.firstStop, "game")}`;
  if (r.games) return `Later stop for ${plural(r.games, "game")}`;
  return "No game linked";
}

function Card({ row, loc, date, fromFeed }: { row: BlockerRow; loc: Location; date?: string | null; fromFeed?: boolean }) {
  return (
    <li>
      <ItemLink item={{ kind: "blocker", id: row.id }} loc={loc} className="card">
        <span className="card-title">{row.title}</span>
        <span className="card-meta">
          <span className="mono">{row.ref}</span>
          <span>{row.area}</span>
        </span>
        <span className="card-foot">
          <StatusPill row={row} />
          {row.open ? (
            <span className={row.firstStop ? "card-games" : "card-games muted"}>{gamesLine(row)}</span>
          ) : (
            date && (
              <span className="card-games muted">
                {fromFeed ? "Resolved" : "Last activity"} {fmtDate(date)}
              </span>
            )
          )}
        </span>
      </ItemLink>
    </li>
  );
}
