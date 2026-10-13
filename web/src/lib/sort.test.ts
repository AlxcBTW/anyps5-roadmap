import { describe, expect, it } from "vitest";
import { compareText, formatSort, nextSort, parseSort, sortRows } from "./sort";

type Row = { n: string; v: number | null };
const rows: Row[] = [
  { n: "b", v: 2 },
  { n: "a", v: null },
  { n: "c", v: 10 },
  { n: "d", v: 2 },
];
const by = { n: (r: Row) => r.n, v: (r: Row) => r.v };

describe("sortRows", () => {
  it("sorts both ways, keeps ties in input order and puts empty values last", () => {
    expect(sortRows(rows, by, { key: "v", dir: "asc" }).map((r) => r.n)).toEqual(["b", "d", "c", "a"]);
    expect(sortRows(rows, by, { key: "v", dir: "desc" }).map((r) => r.n)).toEqual(["c", "b", "d", "a"]);
  });

  it("compares text naturally, ignoring case", () => {
    const names = [{ n: "PPSA10" }, { n: "ppsa9" }, { n: "Astro" }];
    const sorted = sortRows(names, { n: (r) => r.n }, { key: "n", dir: "asc" });
    expect(sorted.map((r) => r.n)).toEqual(["Astro", "ppsa9", "PPSA10"]);
  });

  it("offers the same text order outside a sort", () => {
    expect(["PPSA10", "ppsa9", "Éclair", "Astro", "eclair 2"].sort(compareText)).toEqual(["Astro", "Éclair", "eclair 2", "ppsa9", "PPSA10"]);
  });

  it("does not change its input", () => {
    const copy = [...rows];
    sortRows(rows, by, { key: "n", dir: "desc" });
    expect(rows).toEqual(copy);
  });
});

describe("sort in the address", () => {
  const keys = ["rank", "games"] as const;

  it("round-trips and falls back on anything unknown", () => {
    expect(parseSort("-games", keys, { key: "rank", dir: "asc" })).toEqual({ key: "games", dir: "desc" });
    expect(parseSort("nonsense", keys, { key: "rank", dir: "asc" })).toEqual({ key: "rank", dir: "asc" });
    expect(formatSort({ key: "games", dir: "desc" })).toBe("-games");
  });

  it("starts a new column in its natural direction and flips the same one", () => {
    expect(nextSort({ key: "rank", dir: "asc" }, "games", "desc")).toEqual({ key: "games", dir: "desc" });
    expect(nextSort({ key: "games", dir: "desc" }, "games", "desc")).toEqual({ key: "games", dir: "asc" });
  });
});
