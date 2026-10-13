// A game's cover: its square key art from the PlayStation Store, or its library art on Steam, loaded from
// their CDN only when the row comes near the screen. Until it arrives, and for a game without one, a quiet
// tile with the game's initials in the pixel face of the headline numbers. Decorative: the name sits next to it.

import { useState } from "react";
import type { ImageRef } from "../data/schema";

const SIZES = { row: 48, detail: 88 } as const;

/** The image URL for a tile of `px` CSS pixels, with a 2x source where the CDN resizes on request. */
export function coverSrc(image: ImageRef | null | undefined, px: number): { src: string; srcSet?: string } | null {
  const url = image?.square ?? image?.portrait ?? image?.wide;
  if (!image || !url) return null;
  if (image.sizing === "w") return { src: `${url}?w=${px}`, srcSet: `${url}?w=${px} 1x, ${url}?w=${px * 2} 2x` };
  return { src: url };
}

/** Up to two initials: "Grand Theft Auto V" → "GT", "PICO-8 for PS5" → "P8", one character for CJK names. */
export function initials(name: string): string {
  const words = name.replace(/[^\p{L}\p{N}]+/gu, " ").trim().split(" ").filter(Boolean);
  if (!words.length) return "";
  if (/\p{Script=Han}|\p{Script=Hiragana}|\p{Script=Katakana}|\p{Script=Hangul}/u.test(words[0][0])) return words[0][0];
  return words
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

export function Cover({ image, name, named, size }: { image: ImageRef | null | undefined; name: string; named: boolean; size: keyof typeof SIZES }) {
  const px = SIZES[size];
  const [state, setState] = useState<"loading" | "ready" | "failed">("loading");
  const src = state === "failed" ? null : coverSrc(image, px);
  return (
    <span className={`cover cover-${size}`} data-state={src ? state : "none"} aria-hidden="true">
      {named && <span className="cover-initials">{initials(name)}</span>}
      {src && (
        <img
          src={src.src}
          srcSet={src.srcSet}
          alt=""
          width={px}
          height={px}
          loading="lazy"
          decoding="async"
          referrerPolicy="no-referrer"
          // a cached image can finish before React attaches onLoad
          ref={(img) => {
            if (img?.complete && img.naturalWidth > 0 && state === "loading") setState("ready");
          }}
          onLoad={() => setState("ready")}
          onError={() => setState("failed")}
        />
      )}
    </span>
  );
}
