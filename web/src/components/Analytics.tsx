"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";
import { track, type Step } from "@/lib/track";

export const PIXEL_ID = process.env.NEXT_PUBLIC_META_PIXEL_ID ?? "";

/** Meta's loader, as given by Meta (the first PageView included). */
export const PIXEL_SNIPPET = PIXEL_ID
  ? `!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,document,'script','https://connect.facebook.net/en_US/fbevents.js');fbq('init','${PIXEL_ID}');fbq('track','PageView');`
  : "";

const OPEN: Record<string, Step> = {
  document: "open_document", garde: "open_garde", lettre: "open_lettre", epreuve: "open_epreuve", convertir: "open_convertir",
};

/** One "visit" per visitor, one "open_…" per tool, and a Pixel PageView on each page change after the first. */
export function Analytics() {
  const path = usePathname();
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      track("visit");
    } else {
      (window as unknown as { fbq?: (...a: unknown[]) => void }).fbq?.("track", "PageView");
    }
    const step = OPEN[path.split("/")[1] ?? ""];
    if (step) track(step);
  }, [path]);
  return null;
}
