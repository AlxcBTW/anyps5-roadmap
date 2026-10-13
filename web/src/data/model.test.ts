import { describe, expect, it } from "vitest";
import { fixture } from "../test/fixture";
import type { RoadmapDoc } from "./schema";
import { blockerReport, buildModel, gameReport, ref, sourceLabel, statusRef, tagSourceLabel } from "./model";

const model = buildModel(fixture);
const query = (url: string) => Object.fromEntries(new URL(url).searchParams);

describe("ranking", () => {
  it("ranks linked blockers by their score over games, in the data's order", () => {
    const ranked = model.blockers.filter((r) => r.rank != null);
    expect(ranked.map((r) => [r.id, r.rank, r.score])).toEqual([
      ["13~pthread_sigmask", 1, 30],
      ["13~uEtgPWgPxOk", 2, 18],
      ["10", 3, 10],
      ["pr-30", 4, 6],
      ["11", 5, 1],
    ]);
    const ten = model.blocker("10")!;
    expect([ten.games, ten.firstStop, ten.onlyStop]).toEqual([3, 2, 1]);
  });

  it("keeps blockers without a game, and resolved ones, after the ranking", () => {
    expect(model.blockers.map((r) => r.id).slice(5)).toEqual(["pr-33", "13", "12"]);
    expect(model.blocker("13")!.rank).toBeNull();
    expect(model.blocker("12")!.open).toBe(false);
  });

  it("names blockers the way the page does", () => {
    expect(ref({ id: "2548", issue: 2548 })).toBe("#2548");
    expect(ref({ id: "pr-2106", issue: null })).toBe("PR #2106");
    expect(ref({ id: "1578~atoll", issue: null })).toBe("1578~atoll");
  });
});

describe("game order", () => {
  it("lists games furthest stage first, then by name the way the Name sort orders them", () => {
    const doc = structuredClone(fixture) as RoadmapDoc;
    const named: Record<string, string> = { ppsa99001: "Game 10", ppsa99002: "game 9", ppsa99003: "Éclair" };
    for (const g of doc.games ?? []) if (named[g.id]) g.name = named[g.id];
    const games = buildModel(doc).games;
    const ranks = games.map((g) => g.stageRank);
    expect(ranks).toEqual([...ranks].sort((a, z) => z - a));
    expect(games.filter((g) => g.stage === "Converts").map((g) => g.name).slice(0, 3)).toEqual(["Éclair", "game 9", "Game 10"]);
  });
});

describe("tags", () => {
  it("gives every game its tags in the order of the tag list, and the list itself", () => {
    expect(model.tags.map((t) => t.name).slice(0, 3)).toEqual(["2D", "3D", "Shooter"]);
    expect(model.tags.at(-1)).toMatchObject({ name: "App", group: "Kind" });
    expect(model.game("PPSA02100")!.tags).toEqual(["Puzzle", "Adventure"]);
    expect(model.game("PPSA02929")!.tags).toEqual(["2D", "Platformer", "Adventure"]);
    expect(model.game("PPSA01746")!.tags).toEqual([]);
  });

  it("gives a game's tags to every title ID of it and finds the game by them", () => {
    const doc: RoadmapDoc = {
      ...fixture,
      games: fixture.games.map((g) => (g.id === "stray" ? { ...g, title_ids: [...g.title_ids, "PPSA02101"] } : g)),
    };
    const m = buildModel(doc);
    expect(m.game("PPSA02101")).toBe(m.game("stray"));
    expect(m.game("PPSA02101")!.tags).toEqual(["Puzzle", "Adventure"]);
    expect(m.game("PPSA02101")!.search).toContain("ppsa02101");
  });

  it("reads without tags", () => {
    const old = { ...fixture, tags: undefined, games: fixture.games.map((g) => ({ ...g, tags: [] })) };
    const m = buildModel(old);
    expect(m.tags).toEqual([]);
    expect(m.games.every((g) => g.tags.length === 0)).toBe(true);
  });

  it("names a tag source by its site", () => {
    expect(tagSourceLabel("https://www.wikidata.org/wiki/Q96247255")).toBe("Wikidata");
    expect(tagSourceLabel("https://store.playstation.com/en-us/concept/10000176")).toBe("PlayStation Store");
    expect(tagSourceLabel("https://steamspy.com/app/296870")).toBe("SteamSpy");
    expect(tagSourceLabel("https://github.com/ZiZc3/VLC")).toBe("the homebrew’s README");
  });
});

describe("fix status", () => {
  it("reads open, merged and closed fix PRs, in that order", () => {
    expect(model.blocker("10")!.fix).toMatchObject({ kind: "review", label: "Fix in review" });
    expect(model.blocker("pr-33")!.fix.pr?.ref).toBe("#34"); // the open resubmission, not the closed PR
    expect(model.blocker("13~pthread_sigmask")!.fix.kind).toBe("none"); // a related PR is no fix
    expect(model.blocker("12")!.fix.kind).toBe("resolved");
  });

  it("does not repeat a PR blocker's own number in its status", () => {
    expect(statusRef(model.blocker("pr-30")!)).toBeNull();
    expect(statusRef(model.blocker("10")!)).toBe("#20");
  });
});

describe("games", () => {
  it("lists one row per game with a stage, a stop or a claim, highest stage first", () => {
    expect(model.games).toHaveLength(12);
    expect(model.counts).toMatchObject({ games: 12, titleIds: 13 });
    expect(model.game("PPSA21564")).toBeUndefined(); // no stage, stop or claim
    expect(model.games[0].name).toBe("Dreaming Sarah");
    expect(model.games.at(-1)!.name).toBe("Kena: Bridge of Spirits"); // no stage sorts last
  });

  it("holds every title ID of a game in one row, found by any of them", () => {
    const kena = model.game("PPSA01802")!;
    expect(kena).toBe(model.game("PPSA01746"));
    expect(kena.id).toBe("kena-bridge-of-spirits");
    expect(kena.ids).toEqual(["PPSA01746", "PPSA01802"]);
    expect(kena.search).toContain("ppsa01802");
    // its region ID stops at #11 too, and the blocker counts the game once
    expect(model.blocker("11")!.games).toBe(1);
  });

  it("carries the confidence of the stage", () => {
    expect(model.game("PPSA02929")!.reports).toBe("Checked by hand");
    expect(model.game("PPSA02100")!.confidence.level).toBe("reported");
    expect(model.game("PPSA02100")!.reports).toBe("1 report on main");
  });

  it("keeps the stage off main apart from the stage", () => {
    const kena = model.game("PPSA01746")!;
    expect(kena.stage).toBeNull();
    expect(kena.claim).toBeNull(); // its Ingame ran on an integration branch, not on main
    expect(kena.offMain).toMatchObject({ stage: "Ingame", needs: [32], patches: true });
  });

  it("counts the ladder by game, and every listed game once", () => {
    const at = Object.fromEntries(model.ladder.map((r) => [r.stage.name, r.games]));
    expect(at).toMatchObject({ Converts: 8, Starts: 1, Presents: 1, Menus: 1, Ingame: 0 });
    expect(model.noStage).toBe(1);
    expect(model.ladder.reduce((n, r) => n + r.games, 0) + model.noStage).toBe(model.counts.games);
    expect(model.ladder.find((r) => r.stage.name === "Converts")!.heldBy?.row.id).toBe("13~pthread_sigmask");
    expect(model.counts.reachMenus).toBe(at.Menus + at.Ingame + at.Playable);
  });

  it("says what each game hits after a fix", () => {
    const after = Object.fromEntries(
      model.afterFix("10").map((a) => [a.game.name, a.kind === "done" ? "done" : `${a.kind} ${a.then.id}`]),
    );
    expect(after).toEqual({ Stray: "done", "Kena: Bridge of Spirits": "next 11", "Taxi Chaos 2": "earlier pr-30" });
  });
});

describe("correction links", () => {
  it("prefills the wrong-stage form with the stage on the page and its source", () => {
    const sarah = query(gameReport(model, model.game("PPSA02929")!));
    expect(sarah).toMatchObject({
      template: "wrong-stage.yml",
      title: "Stage: Dreaming Sarah (PPSA02929)",
      title_id: "PPSA02929",
      page_stage: "Menus (curated)",
      page_source: "https://github.com/example/AnyPS5/pull/31",
    });
    const kena = query(gameReport(model, model.game("PPSA01746")!));
    expect(kena.page_stage).toBe("No stage yet; Ingame off main");
  });

  it("prefills the blocker form with the blocker, its source and its error line", () => {
    const url = blockerReport(model, model.blocker("10")!);
    expect(url.startsWith("https://github.com/AlxcBTW/anyps5-roadmap/issues/new?")).toBe(true);
    const q = query(url);
    expect(q.template).toBe("blocker.yml");
    expect(q.blocker.startsWith("#10 ")).toBe(true);
    expect(q.page_source).toBe("https://github.com/example/AnyPS5/issues/10");
    expect(q.error).toContain("packed pixel ancillary input");
  });

  it("labels sources like the classic page", () => {
    const repo = "example/AnyPS5";
    expect(sourceLabel("https://github.com/example/AnyPS5/pull/31", repo)).toBe("PR #31");
    expect(sourceLabel("https://github.com/example/AnyPS5/issues/13#issuecomment-3", repo)).toBe("#13 comment");
    expect(sourceLabel("https://github.com/AlxcBTW/AnyPS5/pull/25", repo)).toBe("AlxcBTW#25");
    expect(sourceLabel("https://github.com/example/AnyPS5/blob/main/docs/user/COMPATIBILITY.md", repo)).toBe(
      "COMPATIBILITY.md",
    );
  });
});
