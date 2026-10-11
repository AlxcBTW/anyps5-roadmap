import { describe, expect, it } from "vitest";
import { sortRows } from "../lib/sort";
import { fixture } from "../test/fixture";
import { blockerAccessors, board, filterBlockers, filterGames, gameAccessors, gameCount, stageCounts } from "./lists";
import { buildModel } from "./model";

const model = buildModel(fixture);
const ids = (rows: { id: string }[]) => rows.map((r) => r.id);

describe("roadmap board", () => {
  it("splits open blockers into in review and next up, and lists the resolved ones", () => {
    const b = board(model, new Map());
    expect(ids(b.review)).toEqual(["10", "pr-30", "pr-33"]); // ranked first, then not linked to a game
    expect(ids(b.next)).toEqual(["13~pthread_sigmask", "13~uEtgPWgPxOk", "11"]);
    expect(b.fixed.map((f) => f.row.id)).toEqual(["12"]);
  });

  it("dates a fix from the feed when the feed saw it resolved", () => {
    const b = board(model, new Map([["12", "2026-10-11T04:50:34Z"]]));
    expect(b.fixed[0]).toMatchObject({ date: "2026-10-11T04:50:34Z", fromFeed: true });
  });
});

describe("blocker filters", () => {
  const all = { status: "open", area: "", q: "" } as const;

  it("filters by status, area and search text", () => {
    expect(filterBlockers(model.blockers, all)).toHaveLength(7);
    expect(ids(filterBlockers(model.blockers, { ...all, status: "unlinked" }))).toEqual(["pr-33", "13"]);
    expect(ids(filterBlockers(model.blockers, { ...all, status: "resolved" }))).toEqual(["12"]);
    expect(ids(filterBlockers(model.blockers, { ...all, area: "Shader recompiler" }))).toEqual(["10"]);
    // an error line pasted from a log finds the blocker that carries it
    expect(ids(filterBlockers(model.blockers, { ...all, q: "  PACKED PIXEL ancillary " }))).toEqual(["10"]);
    expect(ids(filterBlockers(model.blockers, { ...all, q: "#11" }))).toEqual(["11"]);
  });

  it("sorts by games with empty values last", () => {
    const rows = sortRows(model.blockers, blockerAccessors, { key: "games", dir: "desc" });
    expect(ids(rows).slice(0, 3)).toEqual(["13~pthread_sigmask", "13~uEtgPWgPxOk", "10"]);
    expect(rows.at(-1)!.id).toBe("12"); // resolved: no game count
  });
});

describe("game filters", () => {
  it("filters by stage, including no stage, and by search text", () => {
    expect(ids(filterGames(model.games, { stage: "Presents", q: "" })).sort()).toEqual(["PPSA02100", "PPSA30279"]);
    expect(ids(filterGames(model.games, { stage: "none", q: "" }))).toEqual(["PPSA01746"]);
    expect(ids(filterGames(model.games, { stage: "all", q: "ppsa02929" }))).toEqual(["PPSA02929"]);
    // a game is found through the error line of a blocker that stops it
    expect(ids(filterGames(model.games, { stage: "all", q: "color views of several" }))).toEqual(["PPSA01746"]);
  });

  it("counts games per stage chip, by name", () => {
    const n = stageCounts(model.games);
    expect([n.get("all"), n.get("Converts"), n.get("Presents"), n.get("none")]).toEqual([12, 8, 2, 1]);
    expect(gameCount(model.games)).toBe(12);
  });

  it("sorts by stage without ever using an unverified claim", () => {
    const rows = sortRows(model.games, gameAccessors, { key: "stage", dir: "desc" });
    expect(rows[0].id).toBe("PPSA02929");
    expect(rows.at(-1)!.id).toBe("PPSA01746"); // claims Ingame, but has no stage
  });
});
