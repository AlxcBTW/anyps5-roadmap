/// <reference types="vitest/config" />
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig, type Connect, type Plugin } from "vite";

const here = path.dirname(fileURLToPath(import.meta.url));

// The app reads these next to index.html at runtime. The Pages build copies the app into site/,
// where roadmap.py wrote them. In dev and preview they are served from ROADMAP_DATA (a directory,
// default ../site, the committed snapshot) and then from sample/ (a feed.json for the Changes view).
const DATA_FILES = new Set(["roadmap.json", "feed.json", "llms.txt", "ROADMAP.md", "AGENTS.md", "classic.html"]);
const TYPES: Record<string, string> = {
  ".json": "application/json; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".html": "text/html; charset=utf-8",
};

function roadmapData(): Plugin {
  const dirs = [process.env.ROADMAP_DATA, "../site", "sample"]
    .filter((d): d is string => !!d)
    .map((d) => path.resolve(here, d));
  const serve: Connect.NextHandleFunction = (req, res, next) => {
    const name = decodeURIComponent((req.url ?? "").split("?")[0]).replace(/^\/+/, "");
    if (!DATA_FILES.has(name)) return next();
    for (const dir of dirs) {
      const file = path.join(dir, name);
      if (fs.existsSync(file) && fs.statSync(file).isFile()) {
        res.setHeader("Content-Type", TYPES[path.extname(file)] ?? "application/octet-stream");
        fs.createReadStream(file).pipe(res);
        return;
      }
    }
    res.statusCode = 404;
    res.end();
  };
  return {
    name: "roadmap-data",
    configureServer: (server) => void server.middlewares.use(serve),
    configurePreviewServer: (server) => void server.middlewares.use(serve),
  };
}

export default defineConfig({
  base: "./", // GitHub Pages serves the site under /anyps5-roadmap/
  plugins: [react(), roadmapData()],
  server: { fs: { allow: [".."] } }, // the fonts live in ../site/fonts
  build: { target: "es2022", assetsInlineLimit: 0 },
  test: { environment: "jsdom", include: ["src/**/*.test.{ts,tsx}"] },
});
