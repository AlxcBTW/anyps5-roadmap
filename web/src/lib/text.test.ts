import { describe, expect, it } from "vitest";
import { fold, matchesTerms, searchTerms } from "./text";

describe("fold", () => {
  it("lowers case and drops accents", () => {
    expect(fold("Ghost of Yōtei")).toBe("ghost of yotei");
    expect(fold("POKÉMON")).toBe("pokemon");
    expect(fold("PPSA01325 #2106")).toBe("ppsa01325 #2106");
  });

  it("leaves marks of other scripts alone", () => {
    expect(fold("ガ")).not.toBe(fold("カ"));
    expect(fold("हिंदी").normalize("NFC")).toBe("हिंदी");
  });
});

describe("searchTerms", () => {
  it("splits a query into folded words and ignores extra spaces", () => {
    expect(searchTerms("  Yōtei   GHOST ")).toEqual(["yotei", "ghost"]);
    expect(searchTerms("   ")).toEqual([]);
  });

  it("keeps a quoted part as one term", () => {
    expect(searchTerms('"Descriptor 6 is  not" poll')).toEqual(["descriptor 6 is  not", "poll"]);
    expect(searchTerms('"" "unclosed quote')).toEqual(["unclosed", "quote"]);
  });
});

describe("matchesTerms", () => {
  const haystack = fold("Ghost of Yōtei PPSA12345 pr #2106");

  it("needs every word, in any order", () => {
    expect(matchesTerms(haystack, searchTerms("yotei ghost"))).toBe(true);
    expect(matchesTerms(haystack, searchTerms("PR 2106"))).toBe(true);
    expect(matchesTerms(haystack, searchTerms("ghost tsushima"))).toBe(false);
  });

  it("matches everything for an empty query and still finds partial IDs", () => {
    expect(matchesTerms(haystack, searchTerms(""))).toBe(true);
    expect(matchesTerms(haystack, searchTerms("12345"))).toBe(true);
  });
});
