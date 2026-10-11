import { blockerReport, type BlockerRow } from "../data/model";
import { useData } from "../data/load";
import { fmtDate, plural } from "../lib/format";
import type { Location } from "../lib/router";
import { External, ItemLink, StatusPill } from "../components/ui";

export function BlockerDetail({ id, loc }: { id: string; loc: Location }) {
  const { model, resolvedAt } = useData();
  const row = model.blocker(id);
  if (!row) return <Missing id={id} repo={model.repo} days={model.doc.window?.days ?? 60} />;
  const b = row.blocker;
  const after = model.afterFix(id);
  const prs = b.prs.filter((p) => p.link === "fixes" || p.link === "related");
  const mentions = b.prs.length - prs.length;
  const fixedOn = resolvedAt.get(id);

  return (
    <article className="detail">
      <header className="detail-head">
        <p className="detail-meta">
          {row.rank != null && <span className="mono">No. {String(row.rank).padStart(2, "0")}</span>}
          <span className="mono">{row.ref}</span>
          <span>{row.area}</span>
        </p>
        <h2 id="drawer-title" tabIndex={-1}>
          {row.title}
        </h2>
        <div className="detail-tags">
          <StatusPill row={row} />
          {b.origin === "curated" && <span className="tag">Curated</span>}
          {b.help_wanted && <span className="tag">Help wanted</span>}
        </div>
      </header>

      {row.open ? (
        <dl className="stats">
          <Stat n={row.firstStop} label={row.firstStop === 1 ? "Game stops here first" : "Games stop here first"} />
          <Stat n={row.onlyStop} label={row.onlyStop === 1 ? "Game has no other stop" : "Games have no other stop"} />
          <Stat n={row.games} label={row.games === 1 ? "Game in total" : "Games in total"} />
          <Stat n={row.score} label="Score" hint={`3×${row.onlyStop} + 2×${row.firstStop} + ${row.games}`} />
        </dl>
      ) : (
        <p className="detail-note">
          Fixed
          {row.fix.pr && (
            <>
              {" "}by <External href={row.fix.pr.url} className="mono">{row.fix.pr.ref}</External>
            </>
          )}
          {fixedOn && `, first seen in the snapshot of ${fmtDate(fixedOn)}`}. It no longer stops any game on the map.
        </p>
      )}

      {after.length > 0 && (
        <section className="detail-sec">
          <h3>After this fix</h3>
          <ul className="after">
            {after.map((a) => (
              <li key={`${a.game.id}-${a.kind}`}>
                <ItemLink item={{ kind: "game", id: a.game.id }} loc={loc} className="after-game">
                  {a.game.name}
                </ItemLink>
                {a.kind === "done" && <span className="muted">no known stop left</span>}
                {a.kind !== "done" && (
                  <span className="after-then">
                    <span className="muted">{a.kind === "next" ? "then" : "stops earlier at"}</span>{" "}
                    <BlockerRef row={a.then} loc={loc} named={a.kind === "next"} />
                  </span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {b.next && (
        <section className="detail-sec">
          <h3>Next step</h3>
          <p>{b.next}</p>
        </section>
      )}
      {b.help_wanted && (
        <section className="detail-sec">
          <h3>Help wanted</h3>
          <p>{b.help_wanted}</p>
        </section>
      )}
      {b.signature && (
        <section className="detail-sec">
          <h3>Error</h3>
          <pre className="sig">
            <code>{b.signature}</code>
          </pre>
        </section>
      )}
      {prs.length > 0 && (
        <section className="detail-sec">
          <h3>
            Pull requests <span className="h-n">{prs.length}</span>
          </h3>
          <ul className="prs">
            {prs.map((p) => (
              <li key={p.key}>
                <span className="pr-line">
                  <External href={p.url} className="mono">{p.ref}</External>
                  <span className={`tag tag-${p.state}`}>{p.state}</span>
                  <span className="muted">{p.link === "fixes" ? "fix" : "related"}</span>
                </span>
                {p.title && <span className="pr-title">{p.title}</span>}
                {p.note && <span className="pr-note">{p.note}</span>}
              </li>
            ))}
          </ul>
          {mentions > 0 && <p className="muted small">{plural(mentions, "more PR")} only mention it.</p>}
        </section>
      )}

      <footer className="detail-foot">
        <External href={b.url} className="btn btn-primary">
          Open {row.ref} on GitHub
        </External>
        <a className="report" href={blockerReport(model, row)}>
          Report a correction<span className="sr-only"> for {row.ref}</span>
        </a>
        {b.last_activity && <span className="muted small">Last activity {fmtDate(b.last_activity)}</span>}
      </footer>
    </article>
  );
}

function Stat({ n, label, hint }: { n: number; label: string; hint?: string }) {
  return (
    <div className="stat">
      <dt>
        {label}
        {hint && <span className="stat-hint mono">{hint}</span>}
      </dt>
      <dd className="stat-n">{n}</dd>
    </div>
  );
}

export function BlockerRef({ row, loc, named = true }: { row: BlockerRow; loc: Location; named?: boolean }) {
  return (
    <ItemLink item={{ kind: "blocker", id: row.id }} loc={loc} className="b-link">
      <span className="mono">{row.ref}</span>
      {named && <span className="b-name"> {row.title}</span>}
    </ItemLink>
  );
}

function Missing({ id, repo, days }: { id: string; repo: string; days: number }) {
  const issue = /^\d+$/.test(id) ? id : null;
  return (
    <article className="detail">
      <header className="detail-head">
        <h2 id="drawer-title" tabIndex={-1}>
          {issue ? `#${issue}` : id} is not on the map
        </h2>
      </header>
      <p className="detail-note">This snapshot has no blocker with that ID. It may have been merged into another one or left the {days}-day window.</p>
      {issue && (
        <footer className="detail-foot">
          <External href={`https://github.com/${repo}/issues/${issue}`} className="btn">
            Open #{issue} on GitHub
          </External>
        </footer>
      )}
    </article>
  );
}
