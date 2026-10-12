// The front page answers one question first: how far do PS5 games get on AnyPS5? A short hero with
// four numbers and the search, then every game with its stage and the one issue that stops it, then
// how to help.

import { useData } from "../data/load";
import { setParams, type Location } from "../lib/router";
import { HelpLinks } from "../components/HelpLinks";
import { SearchField } from "../components/ui";
import { GameList } from "./Games";

export function Home({ loc }: { loc: Location }) {
  const { model } = useData();
  const c = model.counts;
  const q = loc.under.params.get("q") ?? "";
  const stats: [number, string][] = [
    [c.games, "games tracked"],
    [c.reachMenus, "reach their menus"],
    [c.open, "open blockers"],
    [c.inReview, "fixes in review"],
  ];

  return (
    <div className="home">
      <header className="hero">
        <div className="hero-text">
          <h1>How far PS5 games get on AnyPS5</h1>
          <p className="lede">
            AnyPS5 ports PS5 games to Linux and Windows. This map tracks every game reported on GitHub: how far it
            gets, and the open issue that stops it.
          </p>
        </div>
        <dl className="hero-stats">
          {stats.map(([n, label]) => (
            <div key={label} className="stat">
              <dt>{label}</dt>
              <dd>{n.toLocaleString("en")}</dd>
            </div>
          ))}
        </dl>
        <div className="hero-search">
          <SearchField
            large
            label="Find a game"
            placeholder="Name, PPSA ID or error line"
            value={q}
            onChange={(v) => setParams(loc, { q: v || null })}
          />
        </div>
      </header>
      <GameList loc={loc} />
      <HelpLinks />
    </div>
  );
}
