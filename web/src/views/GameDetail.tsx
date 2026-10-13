import { Fragment, type ReactNode } from "react";
import { gameReport, sourceLabel, tagSourceLabel, type GameRow } from "../data/model";
import { useData } from "../data/load";
import type { Evidence, TimelineStep } from "../data/schema";
import { fmtDate, plural } from "../lib/format";
import { viewHref, type Location } from "../lib/router";
import { Cover } from "../components/Cover";
import { External, GameTags, StageMeter, ViewLink } from "../components/ui";
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
        <p className="detail-note">This snapshot has no stage, stop or claim for that game or title ID.</p>
        <footer className="detail-foot">
          <ViewLink to={viewHref("games", { q: id })} className="btn">
            Search the games for {id}
          </ViewLink>
        </footer>
      </article>
    );
  }
  const game = g.game;
  const best = game.stage;
  const stages = model.stages.length;
  const resolved = game.resolved_blockers.map((b) => model.blocker(b)).filter((r) => !!r);
  const evidence = game.evidence ?? [];
  const meaning = model.stages.find((s) => s.name === g.stage)?.meaning;
  const several = game.title_ids.length > 1;
  const timeline = game.timeline ?? [];
  const mentions = game.issues.length + game.prs.length + (game.discussions?.length ?? 0);
  // one link per kind of source: two region IDs often both have a store page
  const tagSources = [...new Map(game.tag_sources.map((url) => [tagSourceLabel(url), url])).entries()];

  return (
    <article className="detail">
      <header className="detail-head game-head">
        <Cover image={game.image} name={g.name} named={g.named} size="detail" />
        <div className="game-head-text">
          <p className="detail-meta">
            <TitleIds g={g} />
            {game.engine && <span>{game.engine}</span>}
            {game.kind && <span>{game.kind === "retail" ? "Retail" : "Homebrew"}</span>}
          </p>
          <h2 id="drawer-title" tabIndex={-1}>
            {g.name}
          </h2>
          {game.aliases.length > 0 && (
            <p className="aka">
              Also known as{" "}
              {list(
                game.aliases.length > 4
                  ? [...game.aliases.slice(0, 3), `${game.aliases.length - 3} more`]
                  : game.aliases,
              )}
            </p>
          )}
        </div>
        {g.tags.length > 0 && (
          <div className="detail-game-tags">
            <GameTags tags={g.tags} list />
            {tagSources.length > 0 && (
              <p className="tag-sources">
                Tags from{" "}
                {tagSources.map(([label, url], i) => (
                  <Fragment key={url}>
                    {i > 0 && (i === tagSources.length - 1 ? " and " : ", ")}
                    <External href={url}>{label}</External>
                  </Fragment>
                ))}
              </p>
            )}
          </div>
        )}
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
            {best?.url && <Source e={best} repo={model.repo} brief several={several} />}
            {g.reports && <span className={`tag sure sure-${g.confidence.level ?? "reported"}`}>{g.reports}</span>}
          </p>
        )}
      </section>

      {g.claim && (
        <section className="claim" aria-label="Unverified claim">
          <p className="claim-head">
            <span className="tag tag-claim">Unverified</span>
            Claimed {g.claim.stage} on main
            {g.claimReports >= 2 && <span className="muted"> in {g.claimReports} reports</span>}
          </p>
          {g.claim.quote && <blockquote>{g.claim.quote}</blockquote>}
          <p className="small">
            <External href={g.claim.url}>{sourceLabel(g.claim.url, model.repo)}</External>
            <span className="muted"> · not counted until someone reviews it</span>
          </p>
        </section>
      )}

      {g.offMain && <OffMain off={g.offMain} repo={model.repo} rank={model.stageRank(g.offMain.stage)} total={stages} />}

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
                      {several && s.title && <span className="mono muted">{s.title}</span>}
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

      {timeline.length > 1 && (
        <section className="detail-sec">
          <h3>Stage history</h3>
          <ol className="stage-history">
            {timeline.map((step, i) => (
              <TimelineRow key={`${step.url}-${i}`} step={step} repo={model.repo} rank={model.stageRank(step.stage)} total={stages} />
            ))}
          </ol>
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

      {game.stage_reviews.length > 0 && (
        <section className="detail-sec">
          <h3>
            Stage reviews <span className="h-n">{game.stage_reviews.length}</span>
          </h3>
          <ul className="reviews">
            {game.stage_reviews.map((rv, i) => (
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
              Reports <span className="h-n">{game.evidence_count ?? evidence.length}</span>
            </span>
          </summary>
          <ul className="evidence">
            {evidence.map((e, i) => (
              <li key={i}>
                <p className="ev-line">
                  <span className="ev-stage">{e.stage}</span>
                  <Source e={e} repo={model.repo} several={several} />
                </p>
                {e.quote && <blockquote>{e.quote}</blockquote>}
              </li>
            ))}
          </ul>
          {(game.evidence_count ?? 0) > evidence.length && (
            <p className="muted small">The {evidence.length} furthest of {plural(game.evidence_count, "report")}.</p>
          )}
        </details>
      )}

      {game.image?.page && (
        <p className="cover-credit">
          Cover art from the <External href={game.image.page}>{game.image.source}</External>. It belongs to its
          publisher.
        </p>
      )}

      <footer className="detail-foot">
        <a className="report" href={gameReport(model, g)}>
          Report a correction
          <span className="sr-only"> for {g.named ? `${g.name} (${g.ids[0]})` : g.ids[0]}</span>
        </a>
        {g.lastReport && <span className="muted small">Last report {fmtDate(g.lastReport)}</span>}
        {mentions > 0 && (
          <span className="muted small">
            Named in {list([plural(game.issues.length, "issue"), plural(game.prs.length, "PR"), game.discussions?.length ? plural(game.discussions.length, "discussion") : ""].filter(Boolean))}
          </span>
        )}
      </footer>
    </article>
  );
}

/** How far a game gets off main, and what it waits for: open PRs, and patches no PR carries yet. */
function OffMain({ off, repo, rank, total }: { off: NonNullable<GameRow["offMain"]>; repo: string; rank: number; total: number }) {
  const prs = off.needs.map((n) => (
    <External key={n} href={`https://github.com/${repo}/pull/${n}`} className="mono">
      #{n}
    </External>
  ));
  const parts: ReactNode[] = [];
  prs.forEach((link, i) => {
    if (i > 0) parts.push(i === prs.length - 1 && !off.patches ? " and " : ", ");
    parts.push(link);
  });
  if (off.patches) parts.push(prs.length ? " and local patches" : "local patches no PR carries yet");
  return (
    <section className="claim off-main" aria-label="Off main">
      <p className="claim-head off-main-head">
        <span className="tag tag-claim">Off main</span>
        <StageMeter rank={rank} total={total} />
        <span>{off.stage}</span>
      </p>
      <p className="off-main-needs">
        {prs.length ? (
          <>
            {prs.length === 1 ? "With open PR " : "With open PRs "}
            {parts}
          </>
        ) : (
          <>With {parts}</>
        )}
        .
      </p>
      {off.quote && <blockquote>{off.quote}</blockquote>}
      <p className="small">
        <External href={off.url}>{sourceLabel(off.url, repo)}</External>
        {off.confidence.label && <span className="muted"> · {off.confidence.label}</span>}
        <span className="muted"> · counts once it runs on main</span>
      </p>
    </section>
  );
}

/** "A", "A and B", "A, B and C". */
function list(items: string[]): string {
  return items.length < 2 ? (items[0] ?? "") : `${items.slice(0, -1).join(", ")} and ${items.at(-1)}`;
}

/** Every title ID of the game with its region: "PPSA04263 EU · PPSA04264 US". */
function TitleIds({ g }: { g: GameRow }) {
  const byId = new Map((g.game.titles ?? []).map((t) => [t.id, t]));
  return (
    <>
      {g.ids.map((tid) => {
        const t = byId.get(tid);
        return (
          <span key={tid} className="title-id">
            <span className="mono">{tid}</span>
            {t?.region && <span className="region">{t.region}</span>}
            {t?.platform === "PS4" && <span className="region">PS4</span>}
          </span>
        );
      })}
    </>
  );
}

function TimelineRow({ step, repo, rank, total }: { step: TimelineStep; repo: string; rank: number; total: number }) {
  return (
    <li>
      <span className="tl-date">{step.date ? fmtDate(step.date) : "Earlier"}</span>
      <span className="tl-stage">
        <StageMeter rank={rank} total={total} />
        <span>{step.stage}</span>
      </span>
      <span className="tl-source">
        <External href={step.url}>{sourceLabel(step.url, repo)}</External>
        {step.origin === "curated" && <span className="muted"> · checked by hand</span>}
      </span>
    </li>
  );
}

/** Where a stage was seen and its link. The brief form, in the stage box, leaves the build and author to the reports. */
function Source({ e, repo, brief = false, several = false }: { e: Evidence; repo: string; brief?: boolean; several?: boolean }) {
  const where = [e.os, e.gpu].filter(Boolean).join(" · ");
  const parts = [
    where,
    !brief && e.build && `build ${e.build}`,
    !brief && e.author && `by ${e.author}`,
    several && e.title,
    e.date && fmtDate(e.date),
    !brief && e.also?.length && `also quoted ${e.also.length === 1 ? "once more" : `${e.also.length} more times`}`,
  ].filter(Boolean);
  return (
    <span className="source">
      <External href={e.url}>{sourceLabel(e.url, repo)}</External>
      {parts.length > 0 && <span className="muted"> · {parts.join(" · ")}</span>}
      {!brief && e.origin && e.origin !== "mined" && <span className="tag">{e.origin === "curated" ? "Checked by hand" : "From the AnyPS5 list"}</span>}
    </span>
  );
}
