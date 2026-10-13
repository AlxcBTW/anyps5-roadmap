// Small pieces every view uses. Real links and buttons throughout, so keyboard, middle-click and
// screen readers work without extra code.

import { Fragment, useEffect, useId, useRef, type AnchorHTMLAttributes, type MouseEvent, type ReactNode } from "react";
import { statusRef, type BlockerRow } from "../data/model";
import { itemHref, navigate, openItem, setFocusOnOpen, setOpener, type Item, type Location } from "../lib/router";
import type { Dir, Sort } from "../lib/sort";
import { SearchIcon, SortIcon } from "./Icons";

function plainClick(e: MouseEvent) {
  return e.button === 0 && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey;
}

/** A link to a view; a plain click navigates without a reload. */
export function ViewLink({ to, className, children, ...rest }: { to: string; className?: string; children: ReactNode } & Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href">) {
  return (
    <a
      {...rest}
      href={to}
      className={className}
      onClick={(e) => {
        rest.onClick?.(e);
        if (e.defaultPrevented || !plainClick(e)) return;
        e.preventDefault();
        navigate(to);
        scrollTo({ top: 0 });
      }}
    >
      {children}
    </a>
  );
}

/** A link that opens a blocker or game in the drawer over the current view. */
export function ItemLink({ item, loc, className, children, ...rest }: { item: Item; loc: Location; className?: string; children: ReactNode } & Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href">) {
  return (
    <a
      {...rest}
      href={itemHref(item)}
      className={className}
      onClick={(e) => {
        rest.onClick?.(e);
        if (e.defaultPrevented || !plainClick(e)) return;
        e.preventDefault();
        setFocusOnOpen(e.detail === 0 && e.nativeEvent.isTrusted); // Enter, not a mouse click or the arrow keys
        setOpener(e.currentTarget);
        openItem(item, loc, !!loc.route.item); // moving inside the drawer replaces, opening it pushes
      }}
    >
      {children}
    </a>
  );
}

/** How far a game gets: one segment per stage, filled up to its stage. The stage name beside it carries the meaning. */
export function StageMeter({ rank, total }: { rank: number; total: number }) {
  return (
    <span className="meter" aria-hidden="true">
      {Array.from({ length: total }, (_, i) => (
        <i key={i} className={i <= rank ? "on" : undefined} />
      ))}
    </span>
  );
}

/** What kind of game it is, as quiet text chips. Inside a row link they stay spans, so the link reads as one line. */
export function GameTags({ tags, list = false }: { tags: string[]; list?: boolean }) {
  if (!tags.length) return null;
  if (list) {
    return (
      <ul className="game-tags" role="list" aria-label="Tags">
        {tags.map((t) => (
          <li key={t} className="tag game-tag">
            {t}
          </li>
        ))}
      </ul>
    );
  }
  return (
    <span className="game-tags">
      <span className="sr-only">Tags: </span>
      {tags.map((t, i) => (
        <Fragment key={t}>
          {i > 0 && <span className="sr-only">, </span>}
          <span className="tag game-tag">{t}</span>
        </Fragment>
      ))}
    </span>
  );
}

/** The fix status of a blocker: a dot (filled: fix in review, green: fixed, hollow: no fix) and its label. */
export function StatusPill({ row, withRef = true }: { row: BlockerRow; withRef?: boolean }) {
  const r = withRef ? statusRef(row) : null;
  return (
    <span className={`status status-${row.fix.kind}`}>
      <i aria-hidden="true" />
      {row.fix.label}
      {r && <span className="mono">{r}</span>}
    </span>
  );
}

export interface Chip {
  value: string;
  label: string;
  count?: number;
}

/** Single-choice filter chips (radio buttons underneath). */
export function Chips({ legend, chips, value, onChange }: { legend: string; chips: Chip[]; value: string; onChange: (v: string) => void }) {
  const name = useId();
  return (
    <fieldset className="chips">
      <legend className="sr-only">{legend}</legend>
      {chips.map((c) => (
        <label key={c.value} className="chip">
          <input type="radio" name={name} value={c.value} checked={value === c.value} onChange={() => onChange(c.value)} />
          {c.label}
          {c.count != null && <span className="chip-n">{c.count.toLocaleString("en")}</span>}
        </label>
      ))}
    </fieldset>
  );
}

/** The search field of a list. "/" focuses it from anywhere; Escape clears it. The large one shows its label. */
export function SearchField({ label, placeholder, value, onChange, large = false }: { label: string; placeholder: string; value: string; onChange: (v: string) => void; large?: boolean }) {
  const ref = useRef<HTMLInputElement>(null);
  const id = useId();
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (document.activeElement as HTMLElement | null)?.tagName ?? "";
      if (e.key === "/" && !e.ctrlKey && !e.metaKey && !e.altKey && !/INPUT|TEXTAREA|SELECT/.test(tag)) {
        e.preventDefault();
        ref.current?.focus();
      }
    };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, []);
  return (
    <div className={large ? "search search-lg" : "search"}>
      <label htmlFor={id} className={large ? "search-label" : "sr-only"}>
        {label}
      </label>
      <div className="search-box">
        <SearchIcon />
        <input
          id={id}
          ref={ref}
          type="search"
          value={value}
          placeholder={placeholder}
          autoComplete="off"
          spellCheck={false}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape" && value) {
              e.preventDefault(); // keeps an open drawer open
              onChange("");
            }
          }}
        />
        <kbd aria-hidden="true">/</kbd>
      </div>
    </div>
  );
}

/** A sortable column header: a button inside the th, with aria-sort on the th. */
export function SortHeader<K extends string>({ label, k, sort, natural, onSort, className }: { label: ReactNode; k: K; sort: Sort<K>; natural: Dir; onSort: (k: K, natural: Dir) => void; className?: string }) {
  const active = sort.key === k;
  return (
    <th scope="col" className={className} aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : undefined}>
      <button type="button" className="sort" onClick={() => onSort(k, natural)}>
        {label}
        <SortIcon dir={active ? sort.dir : null} />
      </button>
    </th>
  );
}

/** A sort control for the card layout, where there are no column headers. */
export function SortSelect<K extends string>({ options, sort, onChange }: { options: { key: K; label: string; dir: Dir }[]; sort: Sort<K>; onChange: (s: Sort<K>) => void }) {
  const current = options.find((o) => o.key === sort.key && o.dir === sort.dir) ?? options.find((o) => o.key === sort.key);
  return (
    <label className="select sort-select">
      <span>Sort</span>
      <select
        value={current ? `${current.key}:${current.dir}` : ""}
        onChange={(e) => {
          const [key, dir] = e.target.value.split(":") as [K, Dir];
          onChange({ key, dir });
        }}
      >
        {options.map((o) => (
          <option key={`${o.key}:${o.dir}`} value={`${o.key}:${o.dir}`}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function ViewHead({ title, count, children }: { title: string; count?: string; children?: ReactNode }) {
  return (
    <header className="view-head">
      <h1>
        {title}
        {count && <span className="view-count">{count}</span>}
      </h1>
      {children && <p className="view-sub">{children}</p>}
    </header>
  );
}

/** An empty filter result: says what matched nothing and offers the way out. */
export function Empty({ title, hint, onClear }: { title: string; hint: string; onClear?: () => void }) {
  return (
    <div className="empty" role="status">
      <p className="empty-title">{title}</p>
      <p className="muted">{hint}</p>
      {onClear && (
        <button type="button" className="btn" onClick={onClear}>
          Clear filters
        </button>
      )}
    </div>
  );
}

export function External({ href, children, ...rest }: { href: string; children: ReactNode } & Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href" | "rel" | "target">) {
  return (
    <a {...rest} href={href} target="_blank" rel="noreferrer">
      {children}
    </a>
  );
}
