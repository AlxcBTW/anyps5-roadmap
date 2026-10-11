import { describe, expect, it } from "vitest";
import { canonical, itemHref, parseHash, viewHref } from "./router";

describe("routes", () => {
  it("parses views, items and filters", () => {
    const r = parseHash("#/games?stage=Presents&q=unity");
    expect(r.view).toBe("games");
    expect(r.item).toBeNull();
    expect(r.params.get("stage")).toBe("Presents");
    expect(parseHash("#/blockers/1578~libSceOpusDec.prx").item).toEqual({ kind: "blocker", id: "1578~libSceOpusDec.prx" });
    expect(parseHash("#/games/PPSA01746").item).toEqual({ kind: "game", id: "PPSA01746" });
    expect(parseHash("").view).toBe("roadmap");
    expect(parseHash("#/nowhere").view).toBe("roadmap");
  });

  it("keeps the anchors of the classic page and of feed.json working", () => {
    expect(canonical("#b-2548")).toBe("#/blockers/2548");
    expect(canonical("#g-PPSA01746")).toBe("#/games/PPSA01746");
    expect(canonical("#fix-next")).toBe("#/blockers");
    expect(canonical("#coverage")).toBe("#/coverage");
    expect(canonical("#top")).toBe("#/");
  });

  it("writes links that parse back to the same place", () => {
    const href = itemHref({ kind: "blocker", id: "pr-2106" });
    expect(parseHash(href).item).toEqual({ kind: "blocker", id: "pr-2106" });
    expect(viewHref("blockers", { status: "review", q: "", area: null })).toBe("#/blockers?status=review");
    expect(viewHref("roadmap")).toBe("#/");
  });
});
