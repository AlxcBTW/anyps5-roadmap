"""Upstream sources: files read from a local checkout at a fixed ref, or raw from GitHub."""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from .config import RAW_URL


def http_get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "anyps5-roadmap"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


USER_AGENT = "anyps5-roadmap (+https://github.com/AlxcBTW/anyps5-roadmap)"


def fetch_cached(url: str, path: Path, timeout: int = 60, log=print, opener=urllib.request.urlopen) -> bytes | None:
    """GET `url` into the file `path`, revalidating with the ETag and Last-Modified kept in
    `<path>.meta.json`. A 304 or a network error returns the cached bytes (None when there are
    none); a 200 rewrites the file and the sidecar. `opener` is urlopen, replaceable in tests."""
    meta_path = path.with_name(path.name + ".meta.json")
    cached = path.read_bytes() if path.exists() else None
    headers = {"User-Agent": USER_AGENT}
    if cached is not None:
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
        if meta.get("etag"):
            headers["If-None-Match"] = meta["etag"]
        if meta.get("last_modified"):
            headers["If-Modified-Since"] = meta["last_modified"]
    try:
        with opener(urllib.request.Request(url, headers=headers), timeout=timeout) as resp:
            if getattr(resp, "status", 200) == 304 and cached is not None:
                return cached
            data = resp.read()
            etag, modified = resp.headers.get("ETag"), resp.headers.get("Last-Modified")
    except urllib.error.HTTPError as e:
        if e.code == 304 and cached is not None:
            return cached
        log(f"  fetch failed for {url}: HTTP {e.code}; {'using the cached copy' if cached is not None else 'no copy'}")
        return cached
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        log(f"  fetch failed for {url}: {e}; {'using the cached copy' if cached is not None else 'no copy'}")
        return cached
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    meta = {
        "etag": etag,
        "last_modified": modified,
        "fetched_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "url": url,
    }
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    return data


class Upstream:
    """Reads upstream files from a local checkout at a fixed ref (git show)."""

    def __init__(self, checkout: Path | None, ref: str, repo: str, fetch: bool, log, network: bool = True):
        self.checkout, self.ref, self.repo, self.log, self.network = checkout, ref, repo, log, network
        self.commit = None
        if checkout:
            if fetch:
                subprocess.run(["git", "-C", str(checkout), "fetch", "-q", "origin"], check=False)
            proc = subprocess.run(["git", "-C", str(checkout), "rev-parse", ref], capture_output=True, text=True)
            if proc.returncode == 0:
                self.commit = proc.stdout.strip()

    def show(self, path: str) -> str | None:
        if not self.checkout:
            return None
        proc = subprocess.run(
            ["git", "-C", str(self.checkout), "show", f"{self.ref}:{path}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return proc.stdout if proc.returncode == 0 else None

    def files(self, prefix: str) -> list[str]:
        if not self.checkout:
            return []
        proc = subprocess.run(
            ["git", "-C", str(self.checkout), "ls-tree", "-r", "--name-only", self.ref, "--", prefix],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return proc.stdout.split() if proc.returncode == 0 else []

    def grep(self, pattern: str, prefix: str) -> dict[str, int]:
        """Return {path: match count} for an extended regex under prefix at ref."""
        if not self.checkout:
            return {}
        proc = subprocess.run(
            ["git", "-C", str(self.checkout), "grep", "-c", "-E", "-i", pattern, self.ref, "--", prefix],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        out = {}
        for line in proc.stdout.splitlines():
            parts = line.rsplit(":", 1)
            if len(parts) == 2 and parts[1].isdigit():
                out[parts[0].split(":", 1)[-1]] = int(parts[1])
        return out

    def raw(self, path: str) -> str | None:
        """Fetch a file raw from GitHub main; fall back to the checkout (always the checkout without network)."""
        if not self.network:
            return self.show(path)
        try:
            return http_get(RAW_URL.format(repo=self.repo, path=path)).decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as e:
            self.log(f"  raw fetch failed for {path}: {e}; using checkout")
            return self.show(path)
