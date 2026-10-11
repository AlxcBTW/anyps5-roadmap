import type { Model } from "../data/model";
import { fmtDate } from "../lib/format";
import { viewHref, type View } from "../lib/router";
import { useTheme } from "../lib/theme";
import { FilesIcon, GitHubMark, ThemeIcon } from "./Icons";
import { External, ViewLink } from "./ui";

const NAV: [View, string][] = [
  ["roadmap", "Roadmap"],
  ["blockers", "Blockers"],
  ["games", "Games"],
  ["coverage", "Coverage"],
  ["changes", "Changes"],
  ["data", "Data"],
];

const THEME_NAMES = { system: "System", light: "Light", dark: "Dark" } as const;

export function TopBar({ view, model }: { view: View; model: Model | null }) {
  const [theme, cycle] = useTheme();
  const project = model?.project ?? "AlxcBTW/anyps5-roadmap";
  const up = model?.doc.upstream;
  return (
    <header className="bar">
      <div className="wrap bar-in">
        <ViewLink to="#/" className="brand">
          <span className="brand-mark">AnyPS5</span>
          <span className="brand-sub">Blocker map</span>
        </ViewLink>
        <nav className="nav" aria-label="Views">
          {NAV.map(([v, label]) => (
            <ViewLink key={v} to={viewHref(v)} className={`nav-${v}`} aria-current={v === view ? "page" : undefined}>
              {label}
            </ViewLink>
          ))}
        </nav>
        <div className="bar-end">
          {up && (
            <span className="snap">
              Upstream{" "}
              {up.commit ? (
                <External href={`https://github.com/${up.repo}/commit/${up.commit}`} className="mono">
                  {up.commit.slice(0, 7)}
                </External>
              ) : (
                up.ref
              )}{" "}
              · {fmtDate(model.doc.generated_at)}
            </span>
          )}
          <ViewLink to={viewHref("data")} className="icon-btn bar-data" aria-current={view === "data" ? "page" : undefined}>
            <FilesIcon />
            <span className="sr-only">Data</span>
          </ViewLink>
          <button type="button" className="ghost theme" onClick={cycle} aria-label={`Theme: ${THEME_NAMES[theme]}`}>
            <ThemeIcon mode={theme} />
            <span className="theme-t" aria-hidden="true">
              Theme: {THEME_NAMES[theme]}
            </span>
          </button>
          <External href={`https://github.com/${project}`} className="ghost gh">
            <GitHubMark />
            <span className="gh-t">GitHub</span>
          </External>
        </div>
      </div>
    </header>
  );
}
