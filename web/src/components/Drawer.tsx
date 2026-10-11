// The detail drawer. On wide screens it is a side panel over the list, which stays usable; on
// narrow ones it is a modal sheet over everything (the rest of the page is made inert by App).

import { useEffect, useRef, type ReactNode } from "react";
import { getOpener, takeFocusOnOpen } from "../lib/router";
import { CloseIcon } from "./Icons";

export function Drawer({ modal, label, itemKey, onClose, children }: {
  modal: boolean;
  label: string; // what kind of item this is ("Blocker", "Game"); the item's h2#drawer-title names the dialog
  itemKey: string; // changes when another item opens in the same drawer
  onClose: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLElement>(null);

  // give focus back to the link that opened the drawer (ItemLink records it) when the drawer closes
  useEffect(
    () => () => {
      const el = getOpener();
      // after the commit, once the page is no longer inert; only when focus was lost with the drawer
      setTimeout(() => {
        const active = document.activeElement;
        if ((!active || active === document.body) && el?.isConnected) el.focus({ preventScroll: true });
      });
    },
    [],
  );

  useEffect(() => {
    ref.current?.querySelector(".drawer-body")?.scrollTo({ top: 0 });
    if (takeFocusOnOpen() || modal) ref.current?.querySelector<HTMLElement>("h2")?.focus({ preventScroll: true });
  }, [itemKey, modal]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !e.defaultPrevented) onClose();
    };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    if (!modal) return;
    const root = document.documentElement;
    const prev = root.style.overflow;
    root.style.overflow = "hidden";
    return () => {
      root.style.overflow = prev;
    };
  }, [modal]);

  return (
    <>
      {modal && <div className="scrim" onClick={onClose} aria-hidden="true" />}
      <aside ref={ref} className="drawer" role="dialog" aria-modal={modal || undefined} aria-labelledby="drawer-title">
        <div className="drawer-bar">
          <span className="drawer-kind">{label}</span>
          <button type="button" className="icon-btn" onClick={onClose}>
            <CloseIcon />
            <span className="sr-only">Close</span>
          </button>
        </div>
        <div className="drawer-body">{children}</div>
      </aside>
    </>
  );
}
