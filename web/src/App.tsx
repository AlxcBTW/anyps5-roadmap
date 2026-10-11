import { lazy, Suspense, useCallback, useEffect, useMemo, useRef } from "react";
import { Drawer } from "./components/Drawer";
import { TopBar } from "./components/TopBar";
import { resolvedAt, snapshots } from "./data/feed";
import { DataContext, useJson, type Data } from "./data/load";
import { buildModel } from "./data/model";
import type { Feed, RoadmapDoc } from "./data/schema";
import { closeItem, useLocation, type Location } from "./lib/router";
import { useMedia } from "./lib/useMedia";
import { BlockerDetail } from "./views/BlockerDetail";
import { Blockers } from "./views/Blockers";
import { Changes } from "./views/Changes";
import { Data as DataView } from "./views/Data";
import { GameDetail } from "./views/GameDetail";
import { Games } from "./views/Games";
import { Roadmap } from "./views/Roadmap";

const Coverage = lazy(() => import("./views/Coverage"));

const TITLES = {
  roadmap: "AnyPS5 blocker map",
  blockers: "Blockers · AnyPS5 blocker map",
  games: "Games · AnyPS5 blocker map",
  coverage: "Coverage · AnyPS5 blocker map",
  changes: "Changes · AnyPS5 blocker map",
  data: "Data · AnyPS5 blocker map",
} as const;

export function App() {
  const roadmap = useJson<RoadmapDoc>("roadmap.json");
  const feed = useJson<Feed>("feed.json");
  const loc = useLocation();
  const modal = useMedia("(max-width: 899px)");
  const main = useRef<HTMLElement>(null);

  const data = useMemo<Data | null>(() => {
    if (roadmap.status !== "ready") return null;
    const feedDoc = feed.status === "ready" ? feed.data : null;
    return {
      model: buildModel(roadmap.data),
      snapshots: snapshots(feedDoc),
      resolvedAt: resolvedAt(feedDoc),
      feed: feed.status,
      sizes: {
        "roadmap.json": roadmap.bytes,
        ...(feed.status === "ready" ? { "feed.json": feed.bytes } : {}),
      },
    };
  }, [roadmap, feed]);

  const view = loc.under.view;
  useEffect(() => {
    document.title = TITLES[view];
  }, [view]);

  const item = loc.route.item;
  const drawerOpen = !!(item && data);
  const close = useCallback(() => closeItem(loc), [loc]);

  return (
    <>
      <div className="frame" inert={drawerOpen && modal} data-peek={drawerOpen && !modal ? "" : undefined}>
        <a
          className="skip"
          href="#main"
          onClick={(e) => {
            e.preventDefault();
            main.current?.focus();
          }}
        >
          Skip to content
        </a>
        <TopBar view={view} model={data?.model ?? null} />
        <main id="main" ref={main} tabIndex={-1} className="wrap main">
          {roadmap.status === "loading" && (
            <p className="loading" role="status">
              Loading the blocker map…
            </p>
          )}
          {(roadmap.status === "error" || roadmap.status === "missing") && (
            <div className="empty" role="alert">
              <p className="empty-title">Unable to load roadmap.json</p>
              <p className="muted">
                Check your connection and reload. The same data is in <a href="classic.html">the classic page</a> and{" "}
                <a href="ROADMAP.md">ROADMAP.md</a>.
              </p>
            </div>
          )}
          {data && (
            <DataContext.Provider value={data}>
              <ViewSwitch loc={loc} />
            </DataContext.Provider>
          )}
        </main>
      </div>
      {drawerOpen && (
        <DataContext.Provider value={data}>
          <Drawer
            modal={modal}
            label={item.kind === "blocker" ? "Blocker" : "Game"}
            itemKey={`${item.kind}:${item.id}`}
            onClose={close}
          >
            {item.kind === "blocker" ? <BlockerDetail id={item.id} loc={loc} /> : <GameDetail id={item.id} loc={loc} />}
          </Drawer>
        </DataContext.Provider>
      )}
    </>
  );
}

function ViewSwitch({ loc }: { loc: Location }) {
  switch (loc.under.view) {
    case "blockers":
      return <Blockers loc={loc} />;
    case "games":
      return <Games loc={loc} />;
    case "coverage":
      return (
        <Suspense fallback={<p className="loading" role="status">Loading the coverage map…</p>}>
          <Coverage loc={loc} />
        </Suspense>
      );
    case "changes":
      return <Changes loc={loc} />;
    case "data":
      return <DataView />;
    default:
      return <Roadmap loc={loc} />;
  }
}
