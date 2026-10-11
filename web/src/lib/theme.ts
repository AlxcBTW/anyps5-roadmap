// System, light or dark. index.html applies a stored choice before the first paint.

import { useState } from "react";

export type Theme = "system" | "light" | "dark";
const ORDER: Theme[] = ["system", "light", "dark"];

function current(): Theme {
  const t = document.documentElement.dataset.theme;
  return t === "light" || t === "dark" ? t : "system";
}

export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(current);
  const cycle = () => {
    const next = ORDER[(ORDER.indexOf(current()) + 1) % ORDER.length];
    // a theme flip would fire every color transition at once; switch them off for one frame
    const style = document.createElement("style");
    style.textContent = "*,*::before,*::after{transition:none!important}";
    document.head.appendChild(style);
    if (next === "system") delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = next;
    try {
      if (next === "system") localStorage.removeItem("theme");
      else localStorage.setItem("theme", next);
    } catch {
      // private mode: the choice lasts until reload
    }
    void getComputedStyle(document.documentElement).color;
    requestAnimationFrame(() => requestAnimationFrame(() => style.remove()));
    setTheme(next);
  };
  return [theme, cycle];
}
