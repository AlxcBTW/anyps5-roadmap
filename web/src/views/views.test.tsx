// The list views through the DOM: the front page search, filter chips, sort menus, and rows that open the drawer.
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { DataContext, type Data } from "../data/load";
import { buildModel } from "../data/model";
import { useLocation } from "../lib/router";
import { fixture } from "../test/fixture";
import { Blockers } from "./Blockers";
import { GameDetail } from "./GameDetail";
import { GameList } from "./Games";
import { Home } from "./Home";

const data: Data = { model: buildModel(fixture), snapshots: [], feed: "missing", resolvedAt: new Map(), sizes: {} };

function Harness({ view }: { view: "home" | "games" | "blockers" }) {
  const loc = useLocation();
  return (
    <DataContext.Provider value={data}>
      {view === "home" ? <Home loc={loc} /> : view === "games" ? <GameList loc={loc} /> : <Blockers loc={loc} />}
    </DataContext.Provider>
  );
}

function go(hash: string) {
  act(() => {
    history.replaceState(null, "", hash);
    dispatchEvent(new PopStateEvent("popstate"));
  });
}

const rowNames = () => [...document.querySelectorAll("[data-row-link] .row-title")].map((n) => n.textContent);

beforeEach(() => go("#/"));
afterEach(cleanup);

describe("Front page", () => {
  it("searches the games from the hero and keeps the search in the address", () => {
    go("#/");
    render(<Harness view="home" />);
    expect(rowNames()).toHaveLength(12);
    fireEvent.change(screen.getByRole("searchbox", { name: "Find a game" }), { target: { value: "stray" } });
    expect(location.hash).toBe("#/?q=stray");
    expect(rowNames()).toEqual(["Stray"]);
    expect(screen.getByRole("status").textContent).toBe("1 game matching “stray”");
  });
});

describe("Games", () => {
  it("filters by a stage chip and writes the filter into the address", () => {
    go("#/games");
    render(<Harness view="games" />);
    fireEvent.click(screen.getByRole("radio", { name: /Presents/ }));
    expect(rowNames()).toEqual(["Taxi Chaos 2"]);
    expect(location.hash).toBe("#/games?stage=Presents");
    expect(screen.getByRole("status").textContent).toBe("1 game at Presents");
  });

  it("filters by a tag, counts the stages within it and clears it with the other filters", () => {
    go("#/games");
    render(<Harness view="games" />);
    const menu = screen.getByRole("combobox", { name: "Tag" });
    expect([...menu.querySelectorAll("option")].map((o) => o.textContent)).toEqual([
      "All",
      "2D (1)",
      "Platformer (1)",
      "Puzzle (1)",
      "Adventure (2)",
    ]);
    expect([...menu.querySelectorAll("optgroup")].map((g) => g.label)).toEqual(["Dimension", "Genre"]);
    fireEvent.change(menu, { target: { value: "Adventure" } });
    expect(location.hash).toBe("#/games?tag=Adventure");
    expect(rowNames()).toEqual(["Dreaming Sarah", "Stray"]);
    expect(screen.getByRole("status").textContent).toBe("2 games tagged Adventure");
    // the stage chips count only games with that tag
    expect(screen.getAllByRole("radio").map((r) => r.parentElement!.textContent)).toEqual(["All2", "Menus1", "Starts1"]);
    fireEvent.click(screen.getByRole("radio", { name: /Menus/ }));
    expect(screen.getByRole("status").textContent).toBe("1 game tagged Adventure at Menus");
    go("#/games?tag=Adventure&stage=Converts");
    expect(screen.getByText("No games tagged Adventure at Converts")).toBeTruthy();
    expect(screen.getByText("Pick another tag or stage, or clear the filters.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(location.hash).toBe("#/games");
  });

  it("shows a game's tags in its row", () => {
    go("#/games");
    render(<Harness view="games" />);
    const row = [...document.querySelectorAll("[data-row-link]")].find((r) => r.querySelector(".row-title")!.textContent === "Stray")!;
    expect(row.querySelector(".game-tags")!.textContent).toBe("Tags: Puzzle, Adventure");
  });

  it("shows a game's cover, or its initials, and the confidence of its stage", () => {
    go("#/games");
    render(<Harness view="games" />);
    const row = (name: string) =>
      [...document.querySelectorAll("[data-row-link]")].find((r) => r.querySelector(".row-title")!.textContent === name)!;
    const img = row("Stray").querySelector<HTMLImageElement>(".cover img")!;
    expect(img.getAttribute("alt")).toBe("");
    expect(img.getAttribute("loading")).toBe("lazy");
    expect(img.getAttribute("srcset")).toMatch(/[?]w=48 1x, .*[?]w=96 2x$/);
    expect(row("Taxi Chaos 2").querySelector(".cover img")).toBeNull();
    expect(row("Taxi Chaos 2").querySelector(".cover-initials")!.textContent).toBe("TC");
    expect(row("Taxi Chaos 2").querySelector(".g-sure")!.textContent).toBe("Checked by hand");
    expect(row("Kena: Bridge of Spirits").querySelector(".g-off")!.textContent).toBe("Ingame off main");
    // two title IDs, one row
    expect(row("Kena: Bridge of Spirits").querySelector(".row-meta .mono")!.textContent).toBe("PPSA01746 +1 and 1 more title ID");
  });

  it("sorts from the sort menu", () => {
    go("#/games");
    render(<Harness view="games" />);
    expect(rowNames()[0]).toBe("Dreaming Sarah"); // furthest first
    expect(rowNames().at(-1)).toBe("Kena: Bridge of Spirits"); // no stage
    fireEvent.change(screen.getByRole("combobox", { name: "Sort" }), { target: { value: "name:asc" } });
    expect(location.hash).toBe("#/games?sort=name");
    expect(rowNames().slice(0, 3)).toEqual(["Dreaming Sarah", "Kena: Bridge of Spirits", "PPSA99001"]);
  });

  it("names the search and offers a way out when nothing matches", () => {
    go("#/games?q=nothing-like-this");
    render(<Harness view="games" />);
    expect(screen.getByText("No games match “nothing-like-this”")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(location.hash).toBe("#/games");
  });
});

function Drawer({ id }: { id: string }) {
  const loc = useLocation();
  return (
    <DataContext.Provider value={data}>
      <GameDetail id={id} loc={loc} />
    </DataContext.Provider>
  );
}

describe("Game drawer", () => {
  it("opens a game by any of its title IDs and lists all of them with their regions", () => {
    render(<Drawer id="PPSA01802" />);
    expect(screen.getByRole("heading", { level: 2 }).textContent).toBe("Kena: Bridge of Spirits");
    expect([...document.querySelectorAll(".title-id")].map((n) => n.textContent)).toEqual(["PPSA01746US", "PPSA01802EU"]);
    // its cover: none on the store, so its initials
    expect(document.querySelector(".cover-detail .cover-initials")!.textContent).toBe("KB");
    expect(screen.queryByText(/Cover art from/)).toBeNull();
  });

  it("shows how far a game gets off main and the open PRs it needs", () => {
    render(<Drawer id="kena-bridge-of-spirits" />);
    const box = screen.getByRole("region", { name: "Off main" });
    expect(box.querySelector(".off-main-head")!.textContent).toBe("Off mainIngame");
    expect(box.querySelector(".off-main-needs")!.textContent).toBe("With open PR #32 and local patches.");
    expect(box.querySelector(".off-main-needs a")!.getAttribute("href")).toBe("https://github.com/boykopovar/AnyPS5/pull/32");
    expect(box.textContent).toContain("1 report off main");
    expect(box.textContent).toContain("counts once it runs on main");
  });

  it("credits the cover's source and links the store page", () => {
    render(<Drawer id="stray" />);
    expect(document.querySelector<HTMLImageElement>(".cover-detail img")!.getAttribute("src")).toMatch(/[?]w=88$/);
    const credit = screen.getByText(/Cover art from the/);
    expect(credit.querySelector("a")!.getAttribute("href")).toBe("https://store.playstation.com/en-us/concept/10001114");
    expect(screen.getByText("1 report on main")).toBeTruthy();
  });

  it("says when a game is not on the map", () => {
    render(<Drawer id="PPSA00001" />);
    expect(screen.getByRole("heading", { level: 2 }).textContent).toBe("PPSA00001 is not on the map");
  });
});

describe("Blockers", () => {
  it("opens a blocker over the list and keeps the list's filters underneath", () => {
    go("#/blockers?status=review");
    render(<Harness view="blockers" />);
    expect(rowNames()).toEqual([
      "Packed pixel ancillary word",
      "Direct memory stall on Windows",
      "pthread_set_name_np is not exported", // no game linked yet: after the ranked ones
    ]);
    fireEvent.click(document.querySelector<HTMLAnchorElement>("[data-row-link]")!);
    expect(location.hash).toBe("#/blockers/10");
    expect((history.state as { under?: string }).under).toBe("#/blockers?status=review");
  });

  it("filters by area and search text together", () => {
    go("#/blockers");
    render(<Harness view="blockers" />);
    fireEvent.change(screen.getByRole("combobox", { name: "Area" }), { target: { value: "libkernel" } });
    expect(location.hash).toBe("#/blockers?area=libkernel");
    fireEvent.change(screen.getByRole("searchbox", { name: "Search blockers" }), { target: { value: "pthread" } });
    // two by title, one through its error line
    expect(rowNames().sort()).toEqual([
      "Homebrew catalog: where each title stops",
      "pthread_set_name_np is not exported",
      "pthread_sigmask (JZKw5+Wrnaw) is not exported by libkernel",
    ]);
  });
});
