import { describe, expect, it } from "vitest";
import { sortRows } from "../lib/sort";
import { fixture } from "../test/fixture";
import { blockerAccessors, filterBlockers, filterGames, gameAccessors, gameList, onePerGame, stageCounts, tagCounts } from "./lists";
import { buildModel } from "./model";

const model = buildModel(fixture);
const ids = (rows: { id: string }[]) => rows.map((r) => r.id);

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
  });

  it("keeps one row per game, the first of its title IDs", () => {
    const [a, b] = model.games;
    const twin = { ...b, id: "PPSA00000", name: a.name };
    expect(ids(onePerGame([a, twin, b]))).toEqual([a.id, b.id]);
    expect(onePerGame(model.games)).toHaveLength(12);
  });

  it("lists a game once, at its best title ID, and finds it through any of its title IDs", () => {
    const [a, b] = model.games; // a has the higher stage
    const region = { ...b, name: a.name, search: "ppsa00000 region" };
    const games = [a, region, ...model.games.slice(2)];
    expect(ids(gameList(games, { stage: "all", q: "ppsa00000" }))).toEqual([a.id]);
    expect(gameList(games, { stage: b.stage!, q: "" }).map((g) => g.name)).not.toContain(a.name);
    const n = stageCounts(onePerGame(games));
    expect([...n].filter(([k]) => k !== "all").reduce((sum, [, v]) => sum + v, 0)).toBe(n.get("all"));
  });

  it("filters by tag together with the stage and the search", () => {
    expect(ids(gameList(model.games, { stage: "all", tag: "Adventure", q: "" })).sort()).toEqual(["PPSA02100", "PPSA02929"]);
    expect(ids(gameList(model.games, { stage: "Presents", tag: "Adventure", q: "" }))).toEqual(["PPSA02100"]);
    expect(ids(gameList(model.games, { stage: "all", tag: "Adventure", q: "sarah" }))).toEqual(["PPSA02929"]);
    expect(gameList(model.games, { stage: "all", tag: "Racing", q: "" })).toEqual([]);
  });

  it("counts games per tag once, by name", () => {
    const [sarah] = model.games.filter((g) => g.id === "PPSA02929");
    const region = { ...sarah, id: "PPSA00000" }; // a second title ID of the same game
    const n = tagCounts([...model.games, region]);
    expect([n.get("Adventure"), n.get("2D"), n.get("Puzzle"), n.get("Racing")]).toEqual([2, 1, 1, undefined]);
  });

  it("sorts by stage without ever using an unverified claim", () => {
    const rows = sortRows(model.games, gameAccessors, { key: "stage", dir: "desc" });
    expect(rows[0].id).toBe("PPSA02929");
    expect(rows.at(-1)!.id).toBe("PPSA01746"); // claims Ingame, but has no stage
  });
});
