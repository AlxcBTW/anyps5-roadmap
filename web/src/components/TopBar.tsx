import { useEffect, useRef } from "react";
import type { Model } from "../data/model";
import { fmtDate } from "../lib/format";
import { viewHref, type View } from "../lib/router";
import { useTheme } from "../lib/theme";
import { GitHubMark, ThemeIcon } from "./Icons";
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

// On a narrow phone the tabs may not all fit: keep the current one in view and tell the nav which
// edges still have tabs behind them, so the CSS can fade those edges.
function useNavOverflow(view: View) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    const nav = ref.current;
    if (!nav) return;
    const current = nav.querySelector<HTMLElement>("[aria-current]");
    if (current) {
      const pad = 24;
      if (current.offsetLeft - pad < nav.scrollLeft) nav.scrollLeft = Math.max(0, current.offsetLeft - pad);
      else if (current.offsetLeft + current.offsetWidth + pad > nav.scrollLeft + nav.clientWidth)
        nav.scrollLeft = current.offsetLeft + current.offsetWidth + pad - nav.clientWidth;
    }
    const sync = () => {
      const max = nav.scrollWidth - nav.clientWidth;
      nav.toggleAttribute("data-more-start", nav.scrollLeft > 1);
      nav.toggleAttribute("data-more-end", nav.scrollLeft < max - 1);
    };
    sync();
    nav.addEventListener("scroll", sync, { passive: true });
    window.addEventListener("resize", sync);
    return () => {
      nav.removeEventListener("scroll", sync);
      window.removeEventListener("resize", sync);
    };
  }, [view]);
  return ref;
}

export function TopBar({ view, model }: { view: View; model: Model | null }) {
  const [theme, cycle] = useTheme();
  const nav = useNavOverflow(view);
  const project = model?.project ?? "AlxcBTW/anyps5-roadmap";
  const up = model?.doc.upstream;
  return (
    <header className="bar">
      <div className="wrap bar-in">
        <ViewLink to="#/" className="brand">
          <span className="brand-mark">AnyPS5</span>
          <span className="brand-sub">Blocker map</span>
        </ViewLink>
        <nav className="nav" aria-label="Views" ref={nav}>
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
