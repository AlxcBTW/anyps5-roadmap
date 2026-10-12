import { viewHref, type View } from "../lib/router";
import { useTheme } from "../lib/theme";
import { GitHubMark, ThemeIcon } from "./Icons";
import { External, ViewLink } from "./ui";

// Four places a visitor goes. Coverage lives under About; the games list is the front page.
const NAV: { to: string; label: string; views: View[] }[] = [
  { to: viewHref("roadmap"), label: "Games", views: ["roadmap", "games"] },
  { to: viewHref("blockers"), label: "Blockers", views: ["blockers"] },
  { to: viewHref("changes"), label: "Changes", views: ["changes"] },
  { to: viewHref("data"), label: "About", views: ["data", "coverage"] },
];

const THEME_NAMES = { system: "System", light: "Light", dark: "Dark" } as const;

export function TopBar({ view, project }: { view: View; project: string }) {
  const [theme, cycle] = useTheme();
  return (
    <header className="bar">
      <div className="page bar-in">
        <ViewLink to="#/" className="brand">
          AnyPS5 <span className="brand-sub">Blocker map</span>
        </ViewLink>
        <nav className="nav" aria-label="Main">
          {NAV.map((n) => (
            <ViewLink key={n.label} to={n.to} aria-current={n.views.includes(view) ? "page" : undefined}>
              {n.label}
            </ViewLink>
          ))}
        </nav>
        <div className="bar-end">
          <button type="button" className="icon-btn" onClick={cycle} aria-label={`Theme: ${THEME_NAMES[theme]}`} title={`Theme: ${THEME_NAMES[theme]}`}>
            <ThemeIcon mode={theme} />
          </button>
          <External href={`https://github.com/${project}`} className="icon-btn" aria-label="Source on GitHub" title="Source on GitHub">
            <GitHubMark />
          </External>
        </div>
      </div>
    </header>
  );
}
