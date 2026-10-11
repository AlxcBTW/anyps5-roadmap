import { describe, expect, it } from "vitest";
import { fixture } from "../test/fixture";
import { blockerReport, buildModel, gameReport, ref, sourceLabel, statusRef } from "./model";

const model = buildModel(fixture);
const query = (url: string) => Object.fromEntries(new URL(url).searchParams);

describe("ranking", () => {
  it("ranks linked blockers by a score over game names, like the classic page", () => {
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
    expect(ten.dots).toEqual([true, true, false]); // first stops first
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
  it("lists one row per title ID with a stage, a stop or a claim, highest stage first", () => {
    expect(model.games).toHaveLength(12);
    expect(model.game("PPSA21564")).toBeUndefined(); // no stage, stop or claim
    expect(model.games[0].name).toBe("Dreaming Sarah");
    expect(model.games.at(-1)!.name).toBe("Kena: Bridge of Spirits"); // no stage sorts last
  });

  it("keeps an unverified claim apart from the stage", () => {
    const kena = model.game("PPSA01746")!;
    expect(kena.stage).toBeNull();
    expect(kena.claim?.stage).toBe("Ingame");
  });

  it("counts the ladder by game, and every listed game once", () => {
    const at = Object.fromEntries(model.ladder.map((r) => [r.stage.name, r.games]));
    expect(at).toMatchObject({ Converts: 8, Presents: 2, Menus: 1, Ingame: 0 });
    expect(model.noStage).toBe(1);
    expect(model.ladder.reduce((n, r) => n + r.games, 0) + model.noStage).toBe(model.counts.games);
    expect(model.ladder.find((r) => r.stage.name === "Converts")!.heldBy?.row.id).toBe("13~pthread_sigmask");
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
    const sarah = query(gameReport(model, model.game("PPSA02929")!.title));
    expect(sarah).toMatchObject({
      template: "wrong-stage.yml",
      title: "Stage: Dreaming Sarah (PPSA02929)",
      title_id: "PPSA02929",
      page_stage: "Menus (curated)",
      page_source: "https://github.com/example/AnyPS5/pull/31",
    });
    const kena = query(gameReport(model, model.game("PPSA01746")!.title));
    expect(kena.page_stage).toBe("No stage yet; claimed Ingame, unverified");
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
