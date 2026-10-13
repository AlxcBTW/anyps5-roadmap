// Sorting for the list views. One column at a time; empty values always sort last.

export type Dir = "asc" | "desc";
export type SortValue = string | number | null | undefined;

export interface Sort<K extends string> {
  key: K;
  dir: Dir;
}

export type Accessors<T, K extends string> = Record<K, (row: T) => SortValue>;

const collator = new Intl.Collator("en", { numeric: true, sensitivity: "base" });

/** Names in one order everywhere: digits by value, case and accents ignored. */
export function compareText(a: string, z: string): number {
  return collator.compare(a, z);
}

function compare(a: SortValue, z: SortValue): number {
  if (typeof a === "number" && typeof z === "number") return a - z;
  return collator.compare(String(a), String(z));
}

/** A sorted copy. Ties keep their input order, so the default order breaks them. */
export function sortRows<T, K extends string>(rows: readonly T[], by: Accessors<T, K>, sort: Sort<K>): T[] {
  const get = by[sort.key];
  const sign = sort.dir === "asc" ? 1 : -1;
  return rows
    .map((row, i) => ({ row, i, v: get(row) }))
    .sort((a, z) => {
      const ae = a.v == null || a.v === "";
      const ze = z.v == null || z.v === "";
      if (ae || ze) return ae === ze ? a.i - z.i : ae ? 1 : -1;
      return sign * compare(a.v, z.v) || a.i - z.i;
    })
    .map((x) => x.row);
}

/** "games" -> {games, asc}; "-games" -> {games, desc}; anything unknown -> the fallback. */
export function parseSort<K extends string>(text: string | null, keys: readonly K[], fallback: Sort<K>): Sort<K> {
  if (!text) return fallback;
  const desc = text.startsWith("-");
  const key = (desc ? text.slice(1) : text) as K;
  return keys.includes(key) ? { key, dir: desc ? "desc" : "asc" } : fallback;
}

export function formatSort<K extends string>(sort: Sort<K>): string {
  return (sort.dir === "desc" ? "-" : "") + sort.key;
}

/** Clicking a header: a new column starts in its natural direction, the same column flips. */
export function nextSort<K extends string>(cur: Sort<K>, key: K, natural: Dir): Sort<K> {
  if (cur.key !== key) return { key, dir: natural };
  return { key, dir: cur.dir === "asc" ? "desc" : "asc" };
}
