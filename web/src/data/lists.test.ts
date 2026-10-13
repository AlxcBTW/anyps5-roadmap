import { describe, expect, it } from "vitest";
import { sortRows } from "../lib/sort";
import { fixture } from "../test/fixture";
import { blockerAccessors, filterBlockers, filterGames, gameAccessors, gameList, stageCounts, tagCounts } from "./lists";
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
    expect(ids(filterGames(model.games, { stage: "Presents", q: "" }))).toEqual(["taxi-chaos-2"]);
    expect(ids(filterGames(model.games, { stage: "none", q: "" }))).toEqual(["kena-bridge-of-spirits"]);
    expect(ids(filterGames(model.games, { stage: "all", q: "ppsa02929" }))).toEqual(["dreaming-sarah"]);
    // a game is found through the error line of a blocker that stops it
    expect(ids(filterGames(model.games, { stage: "all", q: "color views of several" }))).toEqual(["kena-bridge-of-spirits"]);
  });

  it("counts games per stage chip", () => {
    const n = stageCounts(model.games);
    expect([n.get("all"), n.get("Converts"), n.get("Starts"), n.get("Presents"), n.get("none")]).toEqual([12, 8, 1, 1, 1]);
  });

  it("finds a game through any of its title IDs and aliases", () => {
    expect(ids(gameList(model.games, { stage: "all", q: "ppsa01802" }))).toEqual(["kena-bridge-of-spirits"]);
    const games = model.games.map((g) => (g.id === "stray" ? { ...g, search: g.search + " the cat game" } : g));
    expect(ids(gameList(games, { stage: "all", q: "the cat game" }))).toEqual(["stray"]);
  });

  it("filters by tag together with the stage and the search", () => {
    expect(ids(gameList(model.games, { stage: "all", tag: "Adventure", q: "" })).sort()).toEqual(["dreaming-sarah", "stray"]);
    expect(ids(gameList(model.games, { stage: "Starts", tag: "Adventure", q: "" }))).toEqual(["stray"]);
    expect(ids(gameList(model.games, { stage: "all", tag: "Adventure", q: "sarah" }))).toEqual(["dreaming-sarah"]);
    expect(gameList(model.games, { stage: "all", tag: "Racing", q: "" })).toEqual([]);
  });

  it("counts games per tag", () => {
    const n = tagCounts(model.games);
    expect([n.get("Adventure"), n.get("2D"), n.get("Puzzle"), n.get("Racing")]).toEqual([2, 1, 1, undefined]);
  });

  it("sorts by stage without ever using an unverified claim", () => {
    const rows = sortRows(model.games, gameAccessors, { key: "stage", dir: "desc" });
    expect(rows[0].id).toBe("dreaming-sarah");
    expect(rows.at(-1)!.id).toBe("kena-bridge-of-spirits"); // claims Ingame, but has no stage
  });

  it("leaves a search or a tag in the list's order: furthest stage first", () => {
    // Stray is at Starts, Kena has no stage; both run on Unreal Engine 4
    expect(ids(gameList(model.games, { stage: "all", q: "unreal" }))).toEqual(["stray", "kena-bridge-of-spirits"]);
    expect(ids(gameList(model.games, { stage: "all", tag: "Adventure", q: "" }))).toEqual(["dreaming-sarah", "stray"]);
  });

  it("puts games with no stage before the first stage when the earliest come first", () => {
    const rows = sortRows(model.games, gameAccessors, { key: "stage", dir: "asc" });
    const ranks = rows.map((g) => g.stageRank);
    expect(ranks).toEqual([...ranks].sort((a, z) => a - z));
    expect(ranks[0]).toBe(-1);
    expect(rows.at(-1)!.id).toBe("dreaming-sarah");
  });

  it("matches every word of a search in any order, whatever the case or accents", () => {
    expect(ids(gameList(model.games, { stage: "all", q: "spirits KÉNA" }))).toEqual(["kena-bridge-of-spirits"]);
    expect(ids(gameList(model.games, { stage: "all", q: "kena stray" }))).toEqual([]);
    expect(ids(filterBlockers(model.blockers, { status: "open", area: "", q: "stall direct" }))).toEqual(["pr-30"]);
  });

  it("takes a quoted part of a search as written", () => {
    expect(ids(filterBlockers(model.blockers, { status: "open", area: "", q: '"memory stall"' }))).toEqual(["pr-30"]);
    expect(ids(filterBlockers(model.blockers, { status: "open", area: "", q: '"stall memory"' }))).toEqual([]);
    expect(ids(filterBlockers(model.blockers, { status: "open", area: "", q: '"memory stall" windows' }))).toEqual(["pr-30"]);
  });
});
