import { describe, expect, it } from "vitest";
import { resolvedAt, snapshots } from "./feed";
import type { Feed } from "./schema";

const feed: Feed = {
  version: "https://jsonfeed.org/version/1.1",
  items: [
    {
      id: "2026-10-11T04:50:34Z",
      title: "1 blocker resolved, 1 title changed",
      date_published: "2026-10-11T04:50:34Z",
      content_text: "#12 “Old crash” is resolved.\nPPSA15186 now stops at #3274 “Deferred compute”.",
      _anyps5: {
        since: "2026-10-11T04:48:06Z",
        changes: [
          { type: "resolved", blocker: "12" },
          { type: "stop", title: "PPSA15186", blocker: "3274", was: null },
        ],
      },
    },
    {
      id: "2026-10-10T21:43:48Z",
      date_published: "2026-10-10T21:43:48Z",
      _anyps5: { changes: [{ type: "resolved", blocker: "12" }] },
    },
    { bogus: true } as never,
  ],
};

describe("change feed", () => {
  it("pairs each record with its sentence and with what it opens", () => {
    const [s] = snapshots(feed);
    expect(s.summary).toBe("1 blocker resolved, 1 title changed");
    expect(s.rows.map((r) => [r.type, r.text, r.item])).toEqual([
      ["resolved", "#12 “Old crash” is resolved.", { kind: "blocker", id: "12" }],
      ["stop", "PPSA15186 now stops at #3274 “Deferred compute”.", { kind: "game", id: "PPSA15186" }],
    ]);
  });

  it("skips malformed items, writes a sentence when the feed has none, and sorts newest first", () => {
    const all = snapshots(feed);
    expect(all.map((s) => s.id)).toEqual(["2026-10-11T04:50:34Z", "2026-10-10T21:43:48Z"]);
    expect(all[1].rows[0].text).toBe("12 is resolved.");
    expect(snapshots(null)).toEqual([]);
  });

  it("dates a resolved blocker by the oldest snapshot that lists it", () => {
    expect(resolvedAt(feed).get("12")).toBe("2026-10-10T21:43:48Z");
  });
});
