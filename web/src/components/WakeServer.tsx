"use client";

import { useEffect } from "react";
import { API_URL } from "@/lib/api";

/**
 * The free server sleeps when nobody uses it and takes ~1 min to wake up. Wake it as soon as the site opens
 * (while the visitor reads the page) so the first real action is fast. Once per tab session.
 */
export function WakeServer() {
  useEffect(() => {
    try {
      if (sessionStorage.getItem("wake")) return;
      sessionStorage.setItem("wake", "1");
    } catch { /* private mode: ping anyway */ }
    fetch(`${API_URL}/health`, { mode: "cors", cache: "no-store" }).catch(() => {});
  }, []);
  return null;
}
