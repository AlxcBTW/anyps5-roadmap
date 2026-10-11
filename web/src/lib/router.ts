// Hash routing, so every view and every blocker or game has a link that works on GitHub Pages.
//
//   #/                         roadmap          #/blockers?status=review&area=AGC+driver&sort=-games
//   #/blockers/2548            a blocker        #/games?stage=Presents&q=unity
//   #/games/PPSA01746          a game (title)   #/coverage  #/changes  #/data
//
// A blocker or game opens in a drawer over the view it was opened from. That view travels in
// history.state.under, so the link itself stays the canonical one. Opened from a link (no state),
// the drawer sits over the blocker or game list. The classic page's anchors (#b-2548, #g-PPSA01746,
// #fix-next, #games, #coverage, #data), which feed.json links to, map onto these routes.

import { useMemo, useSyncExternalStore } from "react";

export const VIEWS = ["roadmap", "blockers", "games", "coverage", "changes", "data"] as const;
export type View = (typeof VIEWS)[number];

export interface Item {
  kind: "blocker" | "game";
  id: string;
}

export interface Route {
  view: View;
  item: Item | null;
  params: URLSearchParams;
  hash: string; // canonical
}

const LEGACY: Record<string, string> = {
  top: "#/",
  "fix-next": "#/blockers",
  games: "#/games",
  coverage: "#/coverage",
  data: "#/data",
};

function decode(s: string): string {
  try {
    return decodeURIComponent(s);
  } catch {
    return s;
  }
}

/** The app's form of any hash, including the classic page's anchors. */
export function canonical(hash: string): string {
  const h = hash.replace(/^#/, "");
  if (h.startsWith("/")) return `#${h}`;
  const id = decode(h);
  if (id.startsWith("b-") && id.length > 2) return itemHref({ kind: "blocker", id: id.slice(2) });
  if (id.startsWith("g-") && id.length > 2) return itemHref({ kind: "game", id: id.slice(2) });
  return LEGACY[id] ?? "#/";
}

export function parseHash(hash: string): Route {
  const c = canonical(hash);
  const [path, query = ""] = c.slice(1).split("?");
  const parts = path.split("/").filter(Boolean).map(decode);
  const view: View = (VIEWS as readonly string[]).includes(parts[0]) ? (parts[0] as View) : "roadmap";
  let item: Item | null = null;
  if (parts[1] && view === "blockers") item = { kind: "blocker", id: parts[1] };
  if (parts[1] && view === "games") item = { kind: "game", id: parts[1] };
  return { view, item, params: new URLSearchParams(query), hash: c };
}

export function viewHref(view: View, params?: Record<string, string | null | undefined> | URLSearchParams): string {
  const q = new URLSearchParams();
  const entries = params instanceof URLSearchParams ? [...params] : Object.entries(params ?? {});
  for (const [k, v] of entries) if (v) q.set(k, v);
  const qs = q.toString();
  return `#/${view === "roadmap" ? "" : view}${qs ? `?${qs}` : ""}`;
}

export function itemHref(item: Item): string {
  return `#/${item.kind === "blocker" ? "blockers" : "games"}/${encodeURIComponent(item.id)}`;
}

// -- the location as a store ---------------------------------------------------

interface Snap {
  hash: string;
  under: string | null;
}

function read(): Snap {
  const st = history.state as { under?: unknown } | null;
  return { hash: location.hash, under: typeof st?.under === "string" ? st.under : null };
}

let snap: Snap = typeof window === "undefined" ? { hash: "", under: null } : read();
const listeners = new Set<() => void>();

function emit() {
  const next = read();
  if (next.hash !== snap.hash || next.under !== snap.under) snap = next;
  listeners.forEach((l) => l());
}

if (typeof window !== "undefined") {
  addEventListener("popstate", emit);
  addEventListener("hashchange", emit);
}

function subscribe(l: () => void) {
  listeners.add(l);
  return () => listeners.delete(l);
}

export function navigate(to: string, opts: { replace?: boolean; under?: string | null } = {}) {
  const state = opts.under ? { under: opts.under } : null;
  if (opts.replace) history.replaceState(state, "", to);
  else history.pushState(state, "", to);
  emit();
}

/** Rewrites a classic-page anchor in the address bar to its route, once at start. */
export function adoptLegacyHash() {
  if (location.hash && !location.hash.startsWith("#/")) history.replaceState(null, "", canonical(location.hash));
  snap = read();
}

export interface Location {
  route: Route; // what the address says
  under: Route; // the view rendered beneath the drawer (or the view itself)
}

export function useLocation(): Location {
  const s = useSyncExternalStore(subscribe, () => snap);
  return useMemo(() => {
    const route = parseHash(s.hash);
    let under = route.item ? parseHash(viewHref(route.view)) : route;
    if (route.item && s.under) {
      const bg = parseHash(s.under);
      if (!bg.item) under = bg;
    }
    return { route, under };
  }, [s]);
}

/** Opens a blocker or game over the current view. */
export function openItem(item: Item, loc: Location, replace = false) {
  navigate(itemHref(item), { under: loc.under.hash, replace });
}

/** Closes the drawer onto the view beneath it. */
export function closeItem(loc: Location) {
  navigate(loc.under.hash);
}

/** Replaces the query of the view beneath the drawer (filters, search, sort) without a history entry. */
export function setParams(loc: Location, changes: Record<string, string | null>) {
  const params = new URLSearchParams(loc.under.params);
  for (const [k, v] of Object.entries(changes)) {
    if (v) params.set(k, v);
    else params.delete(k);
  }
  const under = viewHref(loc.under.view, params);
  if (loc.route.item) navigate(loc.route.hash, { replace: true, under });
  else navigate(under, { replace: true });
}

// Whether the drawer should take focus when it opens: yes after Enter on a link, no after a mouse
// click or the arrow keys in a list (those keep focus where it is, so the list stays usable).
let focusNext = false;
export function setFocusOnOpen(v: boolean) {
  focusNext = v;
}
export function takeFocusOnOpen(): boolean {
  const v = focusNext;
  focusNext = false;
  return v;
}
