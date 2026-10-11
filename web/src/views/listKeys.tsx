import { useRef, type ReactNode } from "react";
import type { Location } from "../lib/router";

/**
 * Wraps a list table: a click anywhere on a row opens it, and the arrow keys move between rows
 * (and, while the drawer is open, show the row they land on).
 */
export function ListKeys({ loc, children }: { loc: Location; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  return (
    <div
      ref={ref}
      className="table-wrap"
      onKeyDown={(e) => {
        if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
        const t = e.target as HTMLElement;
        if (!t.matches("[data-row-link]") || !ref.current) return;
        const links = [...ref.current.querySelectorAll<HTMLAnchorElement>("[data-row-link]")];
        const next = links[links.indexOf(t as HTMLAnchorElement) + (e.key === "ArrowDown" ? 1 : -1)];
        if (!next) return;
        e.preventDefault();
        next.focus();
        if (loc.route.item) next.click();
      }}
      onClick={(e) => {
        const t = e.target as HTMLElement;
        if (t.closest("a, button, input, select, summary, label") || getSelection()?.toString()) return;
        t.closest("tr")?.querySelector<HTMLAnchorElement>("[data-row-link]")?.click();
      }}
    >
      {children}
    </div>
  );
}
