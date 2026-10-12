import { gameReport, sourceLabel } from "../data/model";
import { useData } from "../data/load";
import type { Evidence } from "../data/schema";
import { fmtDate, plural } from "../lib/format";
import { viewHref, type Location } from "../lib/router";
import { External, ItemLink, StageMeter, ViewLink } from "../components/ui";
import { BlockerRef } from "./BlockerDetail";

const VERDICTS = { confirmed: "Confirmed", downgraded: "Downgraded", suppressed: "Suppressed" } as const;

export function GameDetail({ id, loc }: { id: string; loc: Location }) {
  const { model } = useData();
  const g = model.game(id);
  if (!g) {
    return (
      <article className="detail">
        <header className="detail-head">
          <h2 id="drawer-title" tabIndex={-1}>
            {id} is not on the map
          </h2>
        </header>
        <p className="detail-note">This snapshot has no stage, stop or claim for that title ID.</p>
        <footer className="detail-foot">
          <ViewLink to={viewHref("games", { q: id })} className="btn">
            Search the games for {id}
          </ViewLink>
        </footer>
      </article>
    );
  }
  const t = g.title;
  const best = t.best_stage;
  const regions = model.regions(id);
  const stages = model.stages.length;
  const resolved = t.resolved_blockers.map((b) => model.blocker(b)).filter((r) => !!r);
  const evidence = t.evidence ?? [];
  const meaning = model.stages.find((s) => s.name === g.stage)?.meaning;

  return (
    <article className="detail">
      <header className="detail-head">
        <p className="detail-meta">
          <span className="mono">{t.id}</span>
          {t.engine && <span>{t.engine}</span>}
          {t.kind && <span>{t.kind === "retail" ? "Retail" : "Homebrew"}</span>}
        </p>
        <h2 id="drawer-title" tabIndex={-1}>
          {g.name}
        </h2>
      </header>

      <section className="stage-box" aria-label="Stage">
        <div className="stage-line">
          <StageMeter rank={g.stageRank} total={stages} />
          <span className="stage-name">{g.stage ?? "No stage yet"}</span>
          {g.stage && (
            <span className="stage-of muted">
              {g.stageRank + 1} of {stages}
            </span>
          )}
        </div>
        <p className="stage-meaning">{meaning ?? "No report confirms how far it gets on AnyPS5 main yet."}</p>
        {(best?.url || g.reports) && (
          <p className="stage-source">
            {best?.url && <Source e={best} repo={model.repo} brief />}
            {g.reports && <span className="tag">{g.reports}</span>}
          </p>
        )}
      </section>

      <section className="detail-sec">
        <h3>
          Where it stops <span className="h-n">{g.steps.length}</span>
        </h3>
        {g.steps.length ? (
          <ol className="chain">
            {g.steps.map((s, i) => {
              const row = model.blocker(s.id)!;
              return (
                <li key={s.id} className={i === 0 ? "now" : undefined}>
                  <span className="chain-n mono" aria-hidden="true">{i + 1}</span>
                  <div className="chain-body">
                    <BlockerRef row={row} loc={loc} />
                    <span className="chain-meta">
                      {i === 0 && <span className="tag tag-now">Stops here now</span>}
                      {s.scope?.map((p) => (
                        <span key={p} className="tag tag-path">{p}</span>
                      ))}
                      {s.why && <span className="muted">{s.why}</span>}
                    </span>
                  </div>
                </li>
              );
            })}
          </ol>
        ) : (
          <p className="muted">No open stop known.</p>
        )}
      </section>

      {g.claim && (
        <section className="claim" aria-label="Unverified claim">
          <p className="claim-head">
            <span className="tag tag-claim">Unverified</span>
            Claimed {g.claim.stage}
            {g.claimReports >= 2 && <span className="muted"> in {g.claimReports} reports on main</span>}
          </p>
          {g.claim.quote && <blockquote>{g.claim.quote}</blockquote>}
          <p className="small">
            <External href={g.claim.url}>{sourceLabel(g.claim.url, model.repo)}</External>
            <span className="muted"> · not counted until someone reviews it</span>
          </p>
        </section>
      )}

      {resolved.length > 0 && (
        <section className="detail-sec">
          <h3>
            Fixed stops <span className="h-n">{resolved.length}</span>
          </h3>
          <ul className="refs">
            {resolved.map((r) => (
              <li key={r.id}>
                <BlockerRef row={r} loc={loc} />
              </li>
            ))}
          </ul>
        </section>
      )}

      {t.stage_reviews.length > 0 && (
        <section className="detail-sec">
          <h3>
            Stage reviews <span className="h-n">{t.stage_reviews.length}</span>
          </h3>
          <ul className="reviews">
            {t.stage_reviews.map((rv, i) => (
              <li key={i}>
                <p>
                  <span className="tag">{VERDICTS[rv.verdict] ?? rv.verdict}</span> {rv.claim}
                  {rv.stage && rv.stage !== rv.claim && <> → {rv.stage}</>}
                  {" · "}
                  <External href={rv.url || rv.claim_url}>{sourceLabel(rv.url || rv.claim_url, model.repo)}</External>
                </p>
                <blockquote>{rv.quote}</blockquote>
                {rv.reason && <p className="muted small">{rv.reason}</p>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {evidence.length > 0 && (
        <details className="detail-sec more">
          <summary>
            <span className="summary-title">
              Reports <span className="h-n">{evidence.length}</span>
            </span>
          </summary>
          <ul className="evidence">
            {evidence.map((e, i) => (
              <li key={i}>
                <p className="ev-line">
                  <span className="ev-stage">{e.stage}</span>
                  <Source e={e} repo={model.repo} />
                </p>
                {e.quote && <blockquote>{e.quote}</blockquote>}
              </li>
            ))}
          </ul>
        </details>
      )}

      {regions.length > 0 && (
        <section className="detail-sec">
          <h3>Also listed as</h3>
          <ul className="refs">
            {regions.map((r) => (
              <li key={r.id}>
                <ItemLink item={{ kind: "game", id: r.id }} loc={loc} className="mono">
                  {r.id}
                </ItemLink>
                <span className="muted"> {r.stage ?? "No stage yet"}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <footer className="detail-foot">
        <a className="report" href={gameReport(model, t)}>
          Report a correction
          <span className="sr-only">
            {" "}for {t.name ? `${t.name} (${t.id})` : t.id}
          </span>
        </a>
        {g.lastReport && <span className="muted small">Last report {fmtDate(g.lastReport)}</span>}
        {t.issues.length + t.prs.length > 0 && (
          <span className="muted small">
            Named in {plural(t.issues.length, "issue")} and {plural(t.prs.length, "PR")}
          </span>
        )}
      </footer>
    </article>
  );
}

/** Where a stage was seen and its link. The brief form, in the stage box, leaves the build and author to the reports. */
function Source({ e, repo, brief = false }: { e: Evidence; repo: string; brief?: boolean }) {
  const where = [e.os, e.gpu].filter(Boolean).join(" · ");
  const parts = [where, !brief && e.build && `build ${e.build}`, !brief && e.author && `by ${e.author}`, e.date && fmtDate(e.date)].filter(Boolean);
  return (
    <span className="source">
      <External href={e.url}>{sourceLabel(e.url, repo)}</External>
      {parts.length > 0 && <span className="muted"> · {parts.join(" · ")}</span>}
      {e.origin && e.origin !== "mined" && <span className="tag">{e.origin === "curated" ? "Checked by hand" : "From the AnyPS5 list"}</span>}
    </span>
  );
}
