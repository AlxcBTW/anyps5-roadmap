// Fetches the JSON files the Python generator publishes next to index.html.

import { createContext, useContext, useEffect, useState } from "react";
import type { Snapshot } from "./feed";
import type { Model } from "./model";

export type Loaded<T> =
  | { status: "loading" }
  | { status: "ready"; data: T; bytes: number }
  | { status: "missing" } // 404: an offline build has no feed.json
  | { status: "error"; message: string };

export function useJson<T>(url: string): Loaded<T> {
  const [state, setState] = useState<Loaded<T>>({ status: "loading" });
  useEffect(() => {
    const ctl = new AbortController();
    fetch(url, { signal: ctl.signal })
      .then(async (res) => {
        if (res.status === 404) return setState({ status: "missing" });
        if (!res.ok) throw new Error(`${url} answered HTTP ${res.status}`);
        const text = await res.text();
        setState({ status: "ready", data: JSON.parse(text) as T, bytes: new TextEncoder().encode(text).length });
      })
      .catch((e: unknown) => {
        if (!ctl.signal.aborted) setState({ status: "error", message: e instanceof Error ? e.message : String(e) });
      });
    return () => ctl.abort();
  }, [url]);
  return state;
}

export interface Data {
  model: Model;
  snapshots: Snapshot[]; // feed.json, newest first; empty without a feed
  feed: "loading" | "ready" | "missing" | "error";
  resolvedAt: Map<string, string>;
  sizes: Record<string, number>; // bytes of the files the app has read
}

export const DataContext = createContext<Data | null>(null);

export function useData(): Data {
  const d = useContext(DataContext);
  if (!d) throw new Error("useData outside DataContext");
  return d;
}
