// The published files, the snapshot's numbers, the known gaps and where everything comes from.

import { useData } from "../data/load";
import { fmtSize, fmtTime } from "../lib/format";
import { External, ViewHead } from "../components/ui";

const FILES: [string, string][] = [
  ["roadmap.json", "Everything on the map, for tools and scripts"],
  ["feed.json", "What changed in each snapshot, for feed readers"],
  ["llms.txt", "Entry point for language models"],
  ["ROADMAP.md", "Ranking, games and coverage as Markdown tables"],
  ["AGENTS.md", "How to add or correct an entry"],
  ["classic.html", "The whole map as one static page; works without JavaScript"],
];

export function Data() {
  const { model, sizes, feed } = useData();
  const doc = model.doc;
  const s = doc.stats;
  const gaps = doc.gaps ?? [];
  const numbers: [string, number | undefined][] = [
    ["Issues read", s.issues_scanned],
    ["Pull requests read", s.prs_scanned],
    ["Title IDs", s.titles],
    ["Stage reviews", s.stage_reviews],
    ["Curated blockers", s.blockers_curated as number | undefined],
    ["Evidence items", s.evidence_items as number | undefined],
  ];

  return (
    <div className="list-view">
      <ViewHead title="Data">
        Regenerated from GitHub by roadmap.py. Corrections go into data/blockers.json, which always wins over mined
        text.
      </ViewHead>

      <section className="block" aria-labelledby="h-files">
        <div className="block-head">
          <h2 id="h-files">Files</h2>
        </div>
        <ul className="files">
          {FILES.filter(([f]) => f !== "feed.json" || feed === "ready").map(([f, purpose]) => (
            <li key={f}>
              <a className="mono" href={f}>
                {f}
              </a>
              <span className="muted mono">{sizes[f] ? fmtSize(sizes[f]) : ""}</span>
              <span>{purpose}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="block" aria-labelledby="h-numbers">
        <div className="block-head">
          <h2 id="h-numbers">This snapshot</h2>
          <span className="muted small">{fmtTime(doc.generated_at)}</span>
        </div>
        <dl className="numbers">
          {numbers
            .filter(([, n]) => typeof n === "number")
            .map(([label, n]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd className="mono">{n!.toLocaleString("en")}</dd>
              </div>
            ))}
        </dl>
      </section>

      {gaps.length > 0 && (
        <details className="block disclose">
          <summary>
            <h2>
              Known gaps in the data <span className="h-n">{gaps.length}</span>
            </h2>
          </summary>
          <ul className="gaps">
            {gaps.map((g) => (
              <li key={g}>{g}</li>
            ))}
          </ul>
        </details>
      )}

      {(doc.not_blockers ?? []).length > 0 && (
        <details className="block disclose">
          <summary>
            <h2>
              Issues kept out of the ranking <span className="h-n">{doc.not_blockers!.length}</span>
            </h2>
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

      <p className="fine">
        Built from public GitHub data of <External href={`https://github.com/${model.repo}`}>{model.repo}</External>
        {doc.upstream.commit && (
          <>
            {" "}at{" "}
            <External href={`https://github.com/${model.repo}/commit/${doc.upstream.commit}`} className="mono">
              {doc.upstream.commit.slice(0, 7)}
            </External>
          </>
        )}
        . Some stages and links come from keyword rules over issue text and can be wrong, so every one links its
        source. A community prototype, not an official AnyPS5 page.
      </p>
    </div>
  );
}
