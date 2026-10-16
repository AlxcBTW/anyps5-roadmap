import type { Model } from "../data/model";
import { fmtTime } from "../lib/format";
import { viewHref } from "../lib/router";
import { External, ViewLink } from "./ui";

/** Where the data comes from, the secondary pages and the fine print. */
export function Footer({ model }: { model: Model | null }) {
  const project = model?.project ?? "AlxcBTW/anyps5-roadmap";
  const doc = model?.doc;
  return (
    <footer className="foot">
      <div className="page foot-in">
        <nav className="foot-nav" aria-label="More">
          <ViewLink to={viewHref("changes")}>Changes</ViewLink>
          <ViewLink to={viewHref("coverage")}>Coverage</ViewLink>
          <ViewLink to={viewHref("data")}>About</ViewLink>
          <a href="roadmap.json">roadmap.json</a>
          <External href={`https://github.com/${project}`}>Source on GitHub</External>
        </nav>
        {doc && (
          <p className="foot-snap">
            Built {fmtTime(doc.generated_at)} from{" "}
            <External href={`https://github.com/${doc.upstream.repo}`}>{doc.upstream.repo}</External>
            {doc.upstream.commit && (
              <>
                {" "}at{" "}
                <External href={`https://github.com/${doc.upstream.repo}/commit/${doc.upstream.commit}`} className="mono">
                  {doc.upstream.commit.slice(0, 7)}
                </External>
              </>
            )}
            . Rebuilt every few hours. Merged corrections go live within minutes.
          </p>
        )}
        <p className="foot-fine">
          A community project, not an official AnyPS5 page. Not affiliated with Sony Interactive Entertainment;
          PlayStation and PS5 are its trademarks.
        </p>
      </div>
    </footer>
  );
}
