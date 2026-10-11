// The list views through the DOM: filter chips, sortable headers, and rows that open the drawer.
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { DataContext, type Data } from "../data/load";
import { buildModel } from "../data/model";
import { useLocation } from "../lib/router";
import { fixture } from "../test/fixture";
import { Blockers } from "./Blockers";
import { Games } from "./Games";

const data: Data = { model: buildModel(fixture), snapshots: [], feed: "missing", resolvedAt: new Map(), sizes: {} };

function Harness({ view }: { view: "games" | "blockers" }) {
  const loc = useLocation();
  return (
    <DataContext.Provider value={data}>
      {view === "games" ? <Games loc={loc} /> : <Blockers loc={loc} />}
    </DataContext.Provider>
  );
}

function go(hash: string) {
  act(() => {
    history.replaceState(null, "", hash);
    dispatchEvent(new PopStateEvent("popstate"));
  });
}

const rowNames = () =>
  screen
    .getAllByRole("row")
    .slice(1)
    .map((r) => within(r).getAllByRole("link")[0].textContent);

beforeEach(() => go("#/"));
afterEach(cleanup);

describe("Games", () => {
  it("filters by a stage chip and writes the filter into the address", () => {
    go("#/games");
    render(<Harness view="games" />);
    expect(screen.getAllByRole("row")).toHaveLength(13); // header + 12 title IDs
    fireEvent.click(screen.getByRole("radio", { name: /Presents/ }));
    expect(rowNames().sort()).toEqual(["Stray", "Taxi Chaos 2"]);
    expect(location.hash).toBe("#/games?stage=Presents");
    expect(screen.getByRole("status").textContent).toBe("2 games in 2 title IDs");
  });

  it("sorts by a column header and marks the sorted column", () => {
    go("#/games");
    render(<Harness view="games" />);
    const header = screen.getByRole("columnheader", { name: /Game/ });
    fireEvent.click(within(header).getByRole("button"));
    expect(header.getAttribute("aria-sort")).toBe("ascending");
    expect(rowNames().slice(0, 3)).toEqual(["Dreaming Sarah", "Kena: Bridge of Spirits", "PPSA99001"]);
    fireEvent.click(within(header).getByRole("button"));
    expect(header.getAttribute("aria-sort")).toBe("descending");
    expect(rowNames()[0]).toBe("Taxi Chaos 2");
  });

  it("names the search and offers a way out when nothing matches", () => {
    go("#/games?q=nothing-like-this");
    render(<Harness view="games" />);
    expect(screen.getByText("No title IDs match “nothing-like-this”")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(location.hash).toBe("#/games");
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
    fireEvent.click(screen.getAllByRole("link")[0]);
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
