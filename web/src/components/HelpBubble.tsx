"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Icon } from "./Icon";

const HIDDEN = ["/aide", "/coulisses", "/outils", "/dev"];
const SEEN = "propre:help-seen";

/** Floating "Une question ?" bubble, on every page: it settles in after a moment, says what it is once, then
 *  stays a small round button. It sits above any bar fixed at the bottom ([data-bottom-bar]: Télécharger…),
 *  under the sheets and dialogs. */
export function HelpBubble() {
  const path = usePathname();
  const [shown, setShown] = useState(false);
  const [open, setOpen] = useState(false); // the label is out
  const [bottom, setBottom] = useState(0);

  useEffect(() => {
    let t2: ReturnType<typeof setTimeout> | undefined;
    const t1 = setTimeout(() => {
      setShown(true);
      // the label shows for 4 s the first time in the visit (a remount meanwhile shows what is left of it)
      let at = Date.now();
      try {
        at = Number(sessionStorage.getItem(SEEN)) || at;
        sessionStorage.setItem(SEEN, String(at));
      } catch { /* private mode: shown on each page */ }
      const left = at + 4000 - Date.now();
      if (left > 0) {
        setOpen(true);
        t2 = setTimeout(() => setOpen(false), left);
      }
    }, 1200);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  // stays above the bars fixed at the bottom, whatever opens or closes in them (the editor's drawer…)
  useEffect(() => {
    let frame = 0;
    const measure = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        let h = 0;
        document.querySelectorAll<HTMLElement>("[data-bottom-bar]").forEach((el) => {
          const r = el.getBoundingClientRect();
          if (r.height > 0 && r.bottom >= window.innerHeight - 2) h = Math.max(h, window.innerHeight - r.top);
        });
        setBottom(h);
      });
    };
    measure();
    const mo = new MutationObserver(measure);
    mo.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] });
    window.addEventListener("resize", measure);
    return () => { mo.disconnect(); window.removeEventListener("resize", measure); cancelAnimationFrame(frame); };
  }, [path]);

  if (!shown || HIDDEN.some((p) => path?.startsWith(p))) return null;
  // from a document, the message says which one it is about (only drawn in the browser: window is there)
  const doc = new URLSearchParams(window.location.search).get("doc");
  const href = doc ? `/aide/?commande=${encodeURIComponent(doc)}` : "/aide";
  return (
    <Link
      href={href}
      aria-label="Une question ? Écris-nous"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
      className="help-bubble group fixed right-4 z-[45] flex h-12 items-center rounded-full bg-paper text-board shadow-[0_8px_22px_-6px_rgba(0,0,0,.45),0_2px_0_0_rgba(0,0,0,.08)] ring-1 ring-black/10 transition-[bottom,transform,box-shadow] duration-300 ease-[cubic-bezier(.16,1,.3,1)] hover:-translate-y-0.5 active:translate-y-0 active:scale-95"
      style={{ bottom: `calc(${bottom ? `${bottom}px + 12px` : "max(1.25rem, env(safe-area-inset-bottom))"})` }}
    >
      <span className="help-ping pointer-events-none absolute inset-0 rounded-full" aria-hidden />
      <span className="grid h-12 w-12 shrink-0 place-items-center">
        <Icon name="message-circle" size={22} stroke={2.2} />
      </span>
      <span
        className={`grid overflow-hidden whitespace-nowrap text-[15px] font-bold transition-[grid-template-columns,opacity,padding] duration-300 ease-[cubic-bezier(.16,1,.3,1)] ${open ? "grid-cols-[1fr] pr-4 opacity-100" : "grid-cols-[0fr] pr-0 opacity-0"}`}
      >
        <span className="min-w-0">Une question ?</span>
      </span>
    </Link>
  );
}
