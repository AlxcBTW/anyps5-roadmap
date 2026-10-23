import { fmtDate } from "../lib/format";
import { External } from "./ui";

/** The map is no longer maintained: every view opens with the date its data is from. */
export function Archived({ builtAt, repo }: { builtAt: string | null; repo: string }) {
  const date = fmtDate(builtAt);
  return (
    <p className="archived">
      <strong>This map is no longer updated.</strong>
      {date && <> Stages and blockers are as of {date}.</>} For newer test reports, see the{" "}
      <External href={`https://github.com/${repo}/discussions/categories/game-bring-up`}>Game bring-up discussions</External> on
      AnyPS5.
    </p>
  );
}
