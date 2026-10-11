// The coverage treemap layout, ported from render_html.py so both pages draw the same map:
// a squarified treemap of groups, each a grid with one cell per function or instruction.

export interface Rect<T> {
  item: T;
  x: number;
  y: number;
  w: number;
  h: number;
}

/** Squarified treemap (Bruls et al.): [value, item] pairs, largest first, laid out in w × h. */
export function squarify<T>(items: [number, T][], x: number, y: number, w: number, h: number): Rect<T>[] {
  const kept = items.filter(([v]) => v > 0);
  const total = kept.reduce((s, [v]) => s + v, 0);
  const out: Rect<T>[] = [];
  if (!kept.length || w <= 0 || h <= 0) return out;
  let rest = kept.map(([v, item]) => [(v * w * h) / total, item] as [number, T]);
  const worst = (row: [number, T][], side: number) => {
    const area = row.reduce((s, [a]) => s + a, 0);
    const max = Math.max(...row.map(([a]) => a));
    const min = Math.min(...row.map(([a]) => a));
    return Math.max((side * side * max) / (area * area), (area * area) / (side * side * min));
  };
  while (rest.length) {
    const side = Math.min(w, h);
    const row = [rest[0]];
    for (const it of rest.slice(1)) {
      if (worst([...row, it], side) > worst(row, side)) break;
      row.push(it);
    }
    rest = rest.slice(row.length);
    const area = row.reduce((s, [a]) => s + a, 0);
    if (w >= h) {
      const colW = area / h;
      let cy = y;
      for (const [a, item] of row) {
        out.push({ item, x, y: cy, w: colW, h: a / colW });
        cy += a / colW;
      }
      x += colW;
      w -= colW;
    } else {
      const rowH = area / w;
      let cx = x;
      for (const [a, item] of row) {
        out.push({ item, x: cx, y, w: a / rowH, h: rowH });
        cx += a / rowH;
      }
      y += rowH;
      h -= rowH;
    }
  }
  return out;
}

/** Columns and rows for n near-square cells in w × h, preferring grids with no empty cells. */
export function gridFor(n: number, w: number, h: number): [number, number] {
  const ideal = Math.max(1, Math.round(w / Math.sqrt((w * h) / n)));
  let best: { key: [number, number]; cols: number; rows: number } | null = null;
  for (let cols = Math.max(1, ideal - 4); cols <= Math.min(n, ideal + 4); cols++) {
    const rows = Math.ceil(n / cols);
    const aspect = w / cols / (h / rows);
    if (!(aspect >= 0.55 && aspect <= 1.8) && cols !== ideal) continue;
    const key: [number, number] = [rows * cols - n, Math.abs(Math.log(aspect))];
    if (!best || key[0] < best.key[0] || (key[0] === best.key[0] && key[1] < best.key[1])) best = { key, cols, rows };
  }
  return best ? [best.cols, best.rows] : [ideal, Math.ceil(n / ideal)];
}

/** Cells [start, end) of a row-major grid as rectangles [col, row, cols wide, rows high]. */
export function cellRuns(start: number, end: number, cols: number): [number, number, number, number][] {
  const runs: [number, number, number, number][] = [];
  while (start < end) {
    const row = Math.floor(start / cols);
    const col = start % cols;
    if (col === 0 && end - start >= cols) {
      const rows = Math.floor((end - start) / cols);
      runs.push([0, row, cols, rows]);
      start += rows * cols;
    } else {
      const stop = Math.min(end, (row + 1) * cols);
      runs.push([col, row, stop - start, 1]);
      start = stop;
    }
  }
  return runs;
}

export interface Band {
  top: number; // % of the tile
  height: number;
  cols: number;
  rows: number;
  missing: [number, number, number, number][]; // % rectangles inside the band
  grid: boolean; // cells big enough to draw grid lines
}

export interface Tile<T> {
  item: T;
  x: number; // % of the map
  y: number;
  w: number;
  h: number;
  bands: Band[];
}

function band(top: number, height: number, first: number, count: number, cols: number, done: number, cell: number): Band {
  const rows = Math.ceil(count / cols);
  return {
    top,
    height,
    cols,
    rows,
    grid: cell >= 3.2,
    missing: cellRuns(Math.max(done - first, 0), count, cols).map(([c, r, nc, nr]) => [
      (100 * c) / cols,
      (100 * r) / rows,
      (100 * nc) / cols,
      (100 * nr) / rows,
    ]),
  };
}

/**
 * One tile per group, one cell per function. The last row is stretched to the tile's width, so every
 * cell is a function and no slot stays empty. Implemented cells come first, missing ones last.
 */
export function layout<T extends { done: number; todo: number }>(groups: T[], width: number, height: number): Tile<T>[] {
  const items = groups
    .filter((g) => g.done + g.todo)
    .map((g) => [g.done + g.todo, g] as [number, T])
    .sort((a, z) => z[0] - a[0]);
  return squarify(items, 0, 0, width, height).map(({ item: g, x, y, w, h }) => {
    const n = g.done + g.todo;
    const [cols, rows] = gridFor(n, w, h);
    const full = rows * cols === n ? n : (rows - 1) * cols;
    const cell = Math.min(w / cols, h / rows);
    const bands: Band[] = [];
    if (full) bands.push(band(0, (100 * Math.floor(full / cols)) / rows, 0, full, cols, g.done, cell));
    if (full < n) bands.push(band((100 * (rows - 1)) / rows, 100 / rows, full, n - full, n - full, g.done, cell));
    return { item: g, x: (100 * x) / width, y: (100 * y) / height, w: (100 * w) / width, h: (100 * h) / height, bands };
  });
}
