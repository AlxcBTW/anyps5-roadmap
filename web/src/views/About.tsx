// One level down from the games: what the stages and the ranking mean, how to help, and the data
// behind the page (files, numbers, known gaps).

import { useData } from "../data/load";
import { fmtSize, fmtTime, plural } from "../lib/format";
import { HelpLinks } from "../components/HelpLinks";
import { viewHref, type Location } from "../lib/router";
import { ArrowIcon } from "../components/Icons";
import { External, ItemLink, StageMeter, ViewHead, ViewLink } from "../components/ui";

const FILES: [string, string][] = [
  ["roadmap.json", "Everything on the map, for tools and scripts"],
  ["feed.json", "What changed in each snapshot, for feed readers"],
  ["llms.txt", "Entry point for language models"],
  ["ROADMAP.md", "Ranking, games and coverage as Markdown tables"],
  ["AGENTS.md", "How to add or correct an entry"],
  ["classic.html", "The whole map as one static page; works without JavaScript"],
];

export function About({ loc }: { loc: Location }) {
  const { model, sizes, feed } = useData();
  const doc = model.doc;
  const s = doc.stats;
  const gaps = doc.gaps ?? [];
  const total = model.stages.length;
  const numbers: [string, number | undefined][] = [
    ["Issues read", s.issues_scanned],
    ["Pull requests read", s.prs_scanned],
    ["Title IDs", s.titles],
    ["Stage reviews", s.stage_reviews],
    ["Curated blockers", s.blockers_curated as number | undefined],
    ["Evidence items", s.evidence_items as number | undefined],
  ];

  return (
    <div className="view about">
      <ViewHead title="About this map">
        A community map of how far PS5 games get on AnyPS5, rebuilt every hour from public issues and pull requests in{" "}
        <External href={`https://github.com/${model.repo}`}>{model.repo}</External>. Every stage and every blocker links
        its source.
      </ViewHead>

      <section className="section prose" aria-labelledby="h-stages">
        <h2 id="h-stages">Stages</h2>
        <p>Each game shows the furthest stage confirmed on AnyPS5 main, from lowest to highest.</p>
        <ol className="stage-defs stage-table">
          {model.ladder.map((r, i) => (
            <li key={r.stage.name}>
              <StageMeter rank={i} total={total} />
              <span className="sd-name">{r.stage.name}</span>
              <span className="sd-def">
                {r.stage.meaning}
                {r.heldBy && (
                  <span className="sd-held">
                    {" "}
                    Most games here stop first at{" "}
                    <ItemLink item={{ kind: "blocker", id: r.heldBy.row.id }} loc={loc} className="mono">
                      {r.heldBy.row.ref}
                    </ItemLink>
                    .
                  </span>
                )}
              </span>
              <span className="sd-n">{plural(r.games, "game")}</span>
            </li>
          ))}
        </ol>
        <p>
          A stage counts when it was reached on main, or on main plus pull requests that are merged now. Menus and
          higher, the stages people share screenshots of, count only after someone checks the report. Until then the
          game shows the report as an unverified claim.
        </p>
      </section>

      {model.tags.length > 0 && (
        <section className="section prose" aria-labelledby="h-tags">
          <h2 id="h-tags">Tags</h2>
          <p>
            A tag describes a title: 2D or 3D, a genre such as Shooter or Platformer, or App for anything that is not a
            game. Filter the game list by one with the Tag menu.
          </p>
          <p>
            A tag is shown only when a public source names it, and each game links its sources. They are the genres on
            Wikidata and the PlayStation Store, the user tags on SteamSpy, and for homebrew its own README. A title that
            no source describes has no tags.
          </p>
        </section>
      )}

      <section className="section prose" aria-labelledby="h-ranking">
        <h2 id="h-ranking">Blockers and the ranking</h2>
        <p>
          A blocker is an open issue or pull request in AnyPS5 that stops at least one game. Each one scores 3 points for
          every game it is the only stop of, 2 for every game it stops first, and 1 for every game that hits it at all.
          The top of the ranking is where a fix moves the most games.
        </p>
        <p>
          <ViewLink to={viewHref("blockers")} className="go">
            See the ranking <ArrowIcon />
          </ViewLink>
        </p>
      </section>

      <HelpLinks />

      <section className="section prose" aria-labelledby="h-coverage">
        <h2 id="h-coverage">Coverage</h2>
        <p>How much of the PS5's system libraries, GPU shader instructions and GPU command packets AnyPS5 implements.</p>
        <p>
          <ViewLink to={viewHref("coverage")} className="go">
            Open the coverage map <ArrowIcon />
          </ViewLink>
        </p>
      </section>

      <section className="section" aria-labelledby="h-files">
        <h2 id="h-files">Data files</h2>
        <ul className="files">
          {FILES.filter(([f]) => f !== "feed.json" || feed === "ready").map(([f, purpose]) => (
            <li key={f}>
              <a className="mono" href={f}>
                {f}
              </a>
              <span className="muted mono">{sizes[f] ? fmtSize(sizes[f]) : ""}</span>
              <span className="file-purpose">{purpose}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="section" aria-labelledby="h-numbers">
        <div className="section-head">
          <h2 id="h-numbers">This snapshot</h2>
          <span className="muted small">{fmtTime(doc.generated_at)}</span>
        </div>
        <dl className="numbers">
          {numbers
            .filter(([, n]) => typeof n === "number")
            .map(([label, n]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{n!.toLocaleString("en")}</dd>
              </div>
            ))}
        </dl>
      </section>

      {gaps.length > 0 && (
        <details className="disclose">
          <summary>
            <span className="disclose-title">
              Known gaps in the data <span className="h-n">{gaps.length}</span>
            </span>
          </summary>
          <ul className="gaps">
            {gaps.map((g) => (
              <li key={g}>{g}</li>
            ))}
          </ul>
        </details>
      )}

      {(doc.not_blockers ?? []).length > 0 && (
        <details className="disclose">
          <summary>
            <span className="disclose-title">
              Issues kept out of the ranking <span className="h-n">{doc.not_blockers!.length}</span>
            </span>
          </summary>
          <ul className="gaps">
            {doc.not_blockers!.map((n) => (
              <li key={n.issue}>
                <External href={`https://github.com/${model.repo}/issues/${n.issue}`} className="mono">
                  #{n.issue}
                </External>{" "}
                {n.reason}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
