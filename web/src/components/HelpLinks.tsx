import { useData } from "../data/load";
import { plural } from "../lib/format";
import { viewHref } from "../lib/router";
import { External, ViewLink } from "./ui";

/** The ways to help, under the game list and on About: correct the map, take a blocker, fix data, report a bug. */
export function HelpLinks() {
  const { model } = useData();
  const helpWanted = model.blockers.filter((r) => r.open && r.helpWanted).length;
  return (
    <section className="section help" aria-labelledby="h-help">
      <h2 id="h-help">Help move a game forward</h2>
      <ul className="help-list">
        <li>
          <External href={`https://github.com/${model.project}/issues/new/choose`}>Report a wrong stage or blocker</External>
          <span>Each game and blocker panel also has a prefilled form.</span>
        </li>
        <li>
          <ViewLink to={viewHref("blockers", { status: "help" })}>Pick a help-wanted blocker</ViewLink>
          <span>
            {plural(helpWanted, "open blocker")} {helpWanted === 1 ? "says" : "say"} what an outside contributor could
            do.
          </span>
        </li>
        <li>
          <External href={`https://github.com/${model.project}/blob/main/CONTRIBUTING.md`}>Fix the data yourself</External>
          <span>A first fix to data/blockers.json takes about five minutes.</span>
        </li>
        <li>
          <External href={`https://github.com/${model.repo}/issues`}>Report a bug in AnyPS5</External>
          <span>Problems with AnyPS5 itself belong in its own issue tracker.</span>
        </li>
      </ul>
    </section>
  );
}
