"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { ADMIN_KEY, api } from "@/lib/api";

type GoogleId = {
  initialize: (o: { client_id: string; callback: (r: { credential: string }) => void }) => void;
  renderButton: (el: HTMLElement, o: Record<string, string | number>) => void;
};

function listen(onChange: () => void) {
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
}

function hasPass() {
  try { return !!localStorage.getItem(ADMIN_KEY); } catch { return false; }
}

export function AdminLogin() {
  const signedIn = useSyncExternalStore(listen, hasPass, () => false);
  const [error, setError] = useState("");
  const button = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (signedIn) return;
    let gone = false;
    (async () => {
      try {
        const { client_id } = await api.adminConfig();
        if (gone) return;
        if (!client_id) { setError("L'accès équipe n'est pas encore activé sur le serveur."); return; }
        const script = document.createElement("script");
        script.src = "https://accounts.google.com/gsi/client";
        script.async = true;
        script.onload = () => {
          const id = (window as unknown as { google?: { accounts: { id: GoogleId } } }).google?.accounts.id;
          if (gone || !id || !button.current) return;
          id.initialize({
            client_id,
            callback: async ({ credential }) => {
              try {
                const { token } = await api.adminLogin(credential);
                localStorage.setItem(ADMIN_KEY, token);
                window.dispatchEvent(new Event("storage"));
              } catch (e) {
                setError((e as Error).message);
              }
            },
          });
          id.renderButton(button.current, { theme: "outline", size: "large", text: "signin_with", locale: "fr", width: 300 });
        };
        script.onerror = () => setError("Google ne répond pas. Vérifie ta connexion et recharge la page.");
        document.head.appendChild(script);
      } catch (e) {
        if (!gone) setError((e as Error).message);
      }
    })();
    return () => { gone = true; };
  }, [signedIn]);

  function signOut() {
    try { localStorage.removeItem(ADMIN_KEY); } catch { /* ignore */ }
    window.dispatchEvent(new Event("storage"));
  }

  return (
    <div className="w-full max-w-sm">
      <h1 className="font-display text-[34px] leading-[0.95] font-black uppercase">Équipe Paginya</h1>
      {signedIn ? (
        <>
          <p className="mt-3 text-[16px] text-ink/75">
            Cet appareil est connecté pour 30 jours. Au moment de payer, choisis « Équipe Paginya : débloquer sans payer ».
          </p>
          <button type="button" onClick={signOut} className="mt-5 text-[15px] font-semibold text-ink/60 underline">Se déconnecter sur cet appareil</button>
        </>
      ) : (
        <>
          <p className="mt-3 text-[16px] text-ink/75">Connecte-toi avec le compte Google de l&apos;équipe : tes documents seront gratuits sur cet appareil.</p>
          <div ref={button} className="mt-5 min-h-11" />
          {error && <p className="mt-3 text-[14px] text-pin">{error}</p>}
        </>
      )}
    </div>
  );
}
