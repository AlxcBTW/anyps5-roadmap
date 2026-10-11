import { describe, expect, it } from "vitest";
import { layout, squarify } from "./treemap";

// The same checks as tests/test_render.py makes on the classic page's treemap.
describe("treemap", () => {
  it("fills the area", () => {
    const items = [618, 511, 229, 195, 7, 3, 1].map((v, i) => [v, i] as [number, number]);
    const rects = squarify(items, 0, 0, 640, 290);
    expect(rects).toHaveLength(7);
    expect(rects.reduce((s, r) => s + r.w * r.h, 0)).toBeCloseTo(640 * 290, 3);
  });

  it("draws every function as one cell and every missing one as a grey cell", () => {
    const groups = [[599, 19], [195, 34], [0, 4], [7, 0], [1, 1], [113, 22], [40, 11], [3, 23], [5, 25]];
    const sizes = [[640, 290], [80, 40], [12, 30], [300, 9]];
    for (const [done, todo] of groups) {
      for (const [w, h] of sizes) {
        const [tile] = layout([{ done, todo }], w, h);
        let cells = 0;
        let missing = 0;
        for (const b of tile.bands) {
          cells += b.cols * b.rows;
          for (const [, , mw, mh] of b.missing) {
            missing += Math.round((mw * b.cols) / 100) * Math.round((mh * b.rows) / 100);
          }
        }
        expect([cells, missing], `${done}/${todo} in ${w}x${h}`).toEqual([done + todo, todo]);
      }
    }
  });
});
