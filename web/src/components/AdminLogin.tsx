"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { ADMIN_KEY, api } from "@/lib/api";
import { keepAccount } from "@/lib/account";
import { FunnelStats } from "./FunnelStats";
import { GoogleButton } from "./GoogleButton";
import { Icon } from "./Icon";
import { Logo } from "./Logo";
import { SupportInbox } from "./SupportInbox";

const EMAIL_KEY = "propre:admin-email";

function listen(onChange: () => void) {
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
}

function read(key: string) {
  try { return localStorage.getItem(key) ?? ""; } catch { return ""; }
}

/** The team's desk: Google sign-in on a pinned sheet, then the shared support inbox and the visitor stats. */
export function AdminLogin() {
  const pass = useSyncExternalStore(listen, () => read(ADMIN_KEY), () => "");
  const email = useSyncExternalStore(listen, () => read(EMAIL_KEY), () => "");
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"support" | "stats">("support");
  const [waiting, setWaiting] = useState(0);
  const [on, setOn] = useState<boolean | null>(null);

  useEffect(() => {
    api.adminConfig().then(({ client_id }) => setOn(!!client_id)).catch(() => setOn(false));
  }, []);

  async function signIn(credential: string) {
    setError("");
    try {
      const r = await api.adminLogin(credential);
      localStorage.setItem(ADMIN_KEY, r.token);
      localStorage.setItem(EMAIL_KEY, r.email);
      if (r.account) keepAccount(r.account); // the same sign-in unlocks the team's documents by itself
      window.dispatchEvent(new Event("storage"));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  function signOut() {
    try { localStorage.removeItem(ADMIN_KEY); localStorage.removeItem(EMAIL_KEY); } catch { /* ignore */ }
    keepAccount(null);
    window.dispatchEvent(new Event("storage"));
  }

  if (!pass) {
    return (
      <main className="board board-frame relative grid min-h-dvh place-items-center overflow-hidden px-5 py-10">
        <div className="paper relative w-full max-w-[400px] -rotate-1 rounded-[2px] px-7 pt-11 pb-8 text-center">
          <span className="pin top-3 left-1/2 -translate-x-1/2" aria-hidden />
          <Logo />
          <h1 className="mt-6 font-display text-[44px] leading-[0.9] font-black uppercase">Coulisses</h1>
          <p className="mx-auto mt-3 max-w-[30ch] text-[16px] leading-snug text-ink/70">
            Réservé à l&apos;équipe Paginya : messages des clients, visiteurs, documents sans payer.
          </p>
          <div className="mx-auto mt-7 flex min-h-11 justify-center">
            {on === false ? (
              <p className="text-[14px] text-pin">L&apos;accès équipe n&apos;est pas encore activé sur le serveur.</p>
            ) : (
              <GoogleButton onCredential={signIn} text="signin_with" theme="filled_black" width={300} />
            )}
          </div>
          {error && (
            <p className="mt-4 flex items-start justify-center gap-1.5 text-[14px] text-pin">
              <Icon name="triangle-alert" size={16} className="mt-0.5 shrink-0" />{error}
            </p>
          )}
          <p className="mt-7 flex items-center justify-center gap-1.5 border-t border-dashed border-ink/20 pt-4 text-[13px] text-ink/50">
            <Icon name="lock" size={14} /> Seuls les Gmail de l&apos;équipe peuvent entrer
          </p>
        </div>
      </main>
    );
  }

  const tabs = [["support", "Support", waiting], ["stats", "Visiteurs", 0]] as const;
  return (
    <div className="flex min-h-dvh flex-col bg-wall">
      <header className="board">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-3 px-5 pt-[max(1rem,env(safe-area-inset-top))] pb-3">
          <div className="flex items-center gap-3">
            <Logo tone="board" />
            <span className="hidden rounded bg-white/10 px-2 py-1 text-[12px] font-bold tracking-wide text-white/80 uppercase sm:inline">Coulisses</span>
          </div>
          <div className="flex items-center gap-3 text-[14px] text-white/75">
            <span className="hidden sm:inline">{email}</span>
            <button type="button" onClick={signOut} className="press rounded-md px-3 py-1.5 font-semibold ring-1 ring-white/25 hover:text-white">Se déconnecter</button>
          </div>
        </div>
        <nav className="mx-auto flex w-full max-w-5xl gap-1 px-5">
          {tabs.map(([id, label, badge]) => (
            <button key={id} type="button" onClick={() => setTab(id)}
              className={`flex items-center gap-2 rounded-t-md px-4 pt-2.5 pb-2 font-display text-[19px] font-black tracking-wide uppercase ${tab === id ? "bg-wall text-ink" : "text-white/70 hover:text-white"}`}>
              {label}
              {badge > 0 && <span className={`rounded-[4px] border-[1.5px] px-1.5 text-[15px] leading-tight ${tab === id ? "border-stamp text-stamp" : "border-white/60 text-white"}`}>{badge}</span>}
            </button>
          ))}
        </nav>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-5 py-6">
        <p className="mb-5 flex items-center gap-2 text-[14px] text-ink/60">
          <Icon name="badge-check" size={16} className="text-board" /> Sur cet appareil, tes documents se téléchargent sans payer, sans limite (30 jours).
        </p>
        <div className={tab === "support" ? "" : "hidden"}><SupportInbox onWaiting={setWaiting} /></div>
        {tab === "stats" && <div className="paper rounded-[2px] p-5 sm:p-7"><FunnelStats /></div>}
      </main>
    </div>
  );
}
