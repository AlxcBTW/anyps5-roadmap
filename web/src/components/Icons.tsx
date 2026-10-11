// 16 px icons drawn in currentColor; 1.5 px strokes next to regular text.

const base = { width: 16, height: 16, viewBox: "0 0 16 16", "aria-hidden": true, focusable: false } as const;
const stroke = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round",
  strokeLinejoin: "round",
} as const;

/** Octicons mark-github. */
export function GitHubMark() {
  return (
    <svg {...base} className="icon">
      <path
        fill="currentColor"
        d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"
      />
    </svg>
  );
}

export function SearchIcon() {
  return (
    <svg {...base} className="icon">
      <circle cx="7" cy="7" r="4.5" {...stroke} />
      <path d="M10.5 10.5L14 14" {...stroke} />
    </svg>
  );
}

export function CloseIcon() {
  return (
    <svg {...base} className="icon">
      <path d="M4 4l8 8M12 4l-8 8" {...stroke} />
    </svg>
  );
}

export function ChevronIcon() {
  return (
    <svg {...base} className="icon chev">
      <path d="M6 4l4 4-4 4" {...stroke} />
    </svg>
  );
}

export function ArrowIcon() {
  return (
    <svg {...base} className="icon">
      <path d="M3 8h10M9 4l4 4-4 4" {...stroke} />
    </svg>
  );
}

export function SortIcon({ dir }: { dir: "asc" | "desc" | null }) {
  return (
    <svg {...base} className="icon sort-icon" data-dir={dir ?? "none"}>
      <path d="M5 6.5L8 3.5l3 3" {...stroke} className="up" />
      <path d="M5 9.5L8 12.5l3-3" {...stroke} className="down" />
    </svg>
  );
}

export function ThemeIcon({ mode }: { mode: "system" | "light" | "dark" }) {
  if (mode === "light")
    return (
      <svg {...base} className="icon">
        <circle cx="8" cy="8" r="3" {...stroke} />
        <path d="M8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5M3.4 3.4l1 1M11.6 11.6l1 1M3.4 12.6l1-1M11.6 4.4l1-1" {...stroke} />
      </svg>
    );
  if (mode === "dark")
    return (
      <svg {...base} className="icon">
        <path d="M13.5 9.5A5.5 5.5 0 0 1 6.5 2.5a5.5 5.5 0 1 0 7 7Z" {...stroke} />
      </svg>
    );
  return (
    <svg {...base} className="icon">
      <rect x="2" y="2.5" width="12" height="8.5" rx="1.5" {...stroke} />
      <path d="M5.5 13.5h5M8 11v2.5" {...stroke} />
    </svg>
  );
}
