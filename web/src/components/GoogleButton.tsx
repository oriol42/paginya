"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

type Gsi = { accounts: { id: {
  initialize: (o: { client_id: string; callback: (r: { credential: string }) => void }) => void;
  renderButton: (el: HTMLElement, o: Record<string, string | number>) => void;
} } };

let gsi: Promise<Gsi | null> | null = null;
/** Google's sign-in script, loaded only when a button is shown. */
function loadGsi(): Promise<Gsi | null> {
  gsi ??= new Promise((resolve) => {
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client";
    s.async = true;
    s.onload = () => resolve((window as unknown as { google?: Gsi }).google ?? null);
    s.onerror = () => { gsi = null; resolve(null); };
    document.head.appendChild(s);
  });
  return gsi;
}

/** "Continuer avec Google" for customer accounts: hidden while the server has accounts off. */
export function GoogleButton({ onCredential }: { onCredential: (credential: string) => void }) {
  const box = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);
  const cb = useRef(onCredential);
  useEffect(() => { cb.current = onCredential; }, [onCredential]);
  useEffect(() => {
    let alive = true;
    api.accountConfig().then(async ({ client_id }) => {
      if (!client_id || !alive) return;
      const g = await loadGsi();
      if (!g || !alive || !box.current) return;
      g.accounts.id.initialize({ client_id, callback: (r) => cb.current(r.credential) });
      g.accounts.id.renderButton(box.current, { theme: "outline", size: "large", text: "continue_with", locale: "fr", width: 280 });
      setReady(true);
    }).catch(() => {});
    return () => { alive = false; };
  }, []);
  return <div ref={box} className={ready ? "min-h-11" : "hidden"} />;
}
