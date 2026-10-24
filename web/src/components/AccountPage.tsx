"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, formatXaf, operatorOf, type TicketStatus } from "@/lib/api";
import { hasPass, keepAccount, refreshAccount, savedAccount, type Account } from "@/lib/account";
import { perDayText, PLANS, type Plan } from "@/lib/plans";
import { GoogleButton } from "./GoogleButton";
import { Icon } from "./Icon";
import { PHONE_KEY } from "./PaySheet";
import { Input, PinLabel } from "./ui";

const TICKET_LABEL: Record<TicketStatus, string> = { NEW: "En attente de notre réponse", ANSWERED: "On t'a répondu", CLOSED: "Résolu" };
const PENDING_TIMEOUT_MS = 10 * 60 * 1000;

/** The customer's Google account: the pass (plan, days left, today's documents), buying or renewing it, their support messages. */
export function AccountPage() {
  // Client-only (under Suspense because of useSearchParams): the browser's storage can be read right away.
  const wanted = useSearchParams().get("formule");
  const [account, setAccount] = useState<Account | null>(() => savedAccount());
  const [loaded, setLoaded] = useState(false);
  const [plan, setPlan] = useState<Plan>(wanted === "pro" ? "pro" : "essentiel");
  const [phone, setPhone] = useState(() => {
    try { return localStorage.getItem(PHONE_KEY) ?? ""; } catch { return ""; }
  });
  const [phase, setPhase] = useState<"idle" | "pending" | "paid" | "failed">("idle");
  const [link, setLink] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [tickets, setTickets] = useState<{ id: string; status: TicketStatus; last: string }[]>([]);
  const payingId = useRef("");

  useEffect(() => {
    refreshAccount().then((a) => { setAccount(a); setLoaded(true); });
  }, []);

  useEffect(() => {
    if (account) api.myTickets(account.token).then(setTickets).catch(() => {});
  }, [account?.token]); // eslint-disable-line react-hooks/exhaustive-deps -- once per account

  useEffect(() => {
    if (phase !== "pending") return;
    const started = Date.now();
    const t = setInterval(async () => {
      try {
        const o = await api.getOrder(payingId.current);
        if (o.status === "PAID") {
          setAccount(await refreshAccount());
          setPhase("paid");
        } else if (o.status === "FAILED" || o.status === "EXPIRED" || Date.now() - started > PENDING_TIMEOUT_MS) setPhase("failed");
      } catch { /* keep polling on flaky networks */ }
    }, 3000);
    return () => clearInterval(t);
  }, [phase]);

  async function signIn(credential: string) {
    setError("");
    try {
      const a = await api.accountGoogle(credential);
      keepAccount(a);
      setAccount(a);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function pay() {
    if (!account) return;
    setError("");
    setBusy(true);
    try {
      try { localStorage.setItem(PHONE_KEY, phone); } catch { /* ignore */ }
      const p = await api.buyPass(account.token, plan);
      payingId.current = p.id;
      const o = await api.pay(p.id, phone);
      if (o.pay_link) setLink(o.pay_link);
      setPhase("pending");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function signOut() {
    keepAccount(null);
    setAccount(null);
    setTickets([]);
  }

  if (!loaded && !account) return <p className="text-ink/60">Chargement…</p>;

  if (!account) {
    return (
      <>
        <p>Ton compte garde ton pass : tu le retrouves sur n&apos;importe quel téléphone ou ordinateur. Pas de mot de passe, tu te connectes avec Google.</p>
        <GoogleButton onCredential={signIn} />
        {error && <p className="text-[14px] text-pin">{error}</p>}
        <p className="text-[14px] text-ink/60">Pour un seul document, pas besoin de compte : tu paies {formatXaf(550)} au moment de télécharger.</p>
      </>
    );
  }

  const active = hasPass(account);
  const current = account.plan ? PLANS[account.plan] : null;
  const operator = operatorOf(phone);

  return (
    <>
      <div className="rounded-md bg-ink/[0.04] p-5">
        <p className="text-[14px] text-ink/60">Connecté : {account.email}</p>
        {account.team ? (
          <p className="mt-2 flex items-center gap-2 text-[18px] font-bold text-board"><Icon name="badge-check" size={22} /> Équipe Paginya : accès illimité, sans payer</p>
        ) : active && current ? (
          <>
            <p className="mt-2 flex items-center gap-2 text-[18px] font-bold text-board"><Icon name="badge-check" size={22} /> Pass {current.name} · encore {account.pass_days} jour{account.pass_days > 1 ? "s" : ""}</p>
            <p className="mt-1 text-[15px]">{account.per_day ? <>Aujourd&apos;hui : <b>{account.used_today} / {account.per_day}</b> documents. Le compteur repart à minuit.</> : <>Documents illimités ({account.used_today} aujourd&apos;hui).</>}</p>
            <p className="mt-1 text-[14px] text-ink/60">Fin du pass le {new Date(account.pass_until * 1000).toLocaleDateString("fr-FR", { day: "numeric", month: "long" })}. Rien n&apos;est prélevé automatiquement.</p>
          </>
        ) : (
          <p className="mt-2 text-[16px] font-semibold">Pas de pass en cours.</p>
        )}
      </div>

      {!account.team && phase === "idle" && (
        <>
          <h2>{active ? "Prolonger ou changer" : "Prendre un pass"}</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {(Object.keys(PLANS) as Plan[]).map((id) => (
              <button key={id} type="button" onClick={() => setPlan(id)}
                className={`relative rounded-md p-4 text-left ring-1 ${plan === id ? "bg-hi/30 ring-2 ring-ink" : "ring-black/10"}`}>
                {id === "essentiel" && <span className="absolute -top-2.5 right-3 rounded bg-board px-2 py-0.5 text-[11px] font-bold tracking-wide text-white uppercase">Conseillé</span>}
                <span className="block text-[17px] font-bold text-ink">{PLANS[id].name}</span>
                <span className="block font-display text-[28px] leading-tight font-black text-ink">{formatXaf(PLANS[id].price)}<span className="text-[15px] font-semibold text-ink/60"> / 30 jours</span></span>
                <span className="block text-[14px]">{perDayText(PLANS[id].perDay)}</span>
                <span className="block text-[13px] text-ink/60">{PLANS[id].who}</span>
              </button>
            ))}
          </div>
          {active && account.plan && account.plan !== plan && (
            <p className="text-[14px] text-ink/65">Les jours qui te restent sont gardés, convertis à leur valeur dans la nouvelle formule.</p>
          )}
          <label className="block">
            <span className="mb-1.5 block text-[13px] font-bold text-ink/80">Ton numéro Mobile Money</span>
            <div className="flex items-center gap-2">
              <Input inputMode="tel" autoComplete="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="6 70 00 00 00" />
              {operator && <span className="shrink-0 text-[13px] font-bold">{operator}</span>}
            </div>
          </label>
          {error && <p className="text-[14px] text-pin">{error}</p>}
          <PinLabel className="w-full" disabled={busy || phone.replace(/\D/g, "").length < 9} onClick={pay}>
            {busy ? "Envoi…" : `Payer ${formatXaf(PLANS[plan].price)}`}
          </PinLabel>
          <p className="text-[13px] text-ink/60">30 jours à partir du paiement, sans renouvellement automatique : tu repaies seulement si tu veux continuer.</p>
        </>
      )}

      {phase === "pending" && (
        <div className="rounded-md bg-hi/25 p-5 text-center">
          <Icon name="smartphone" size={44} stroke={1.5} className="mx-auto animate-pulse text-board" />
          {link ? (
            <p className="mt-3">Paie <b>{formatXaf(PLANS[plan].price)}</b> sur la page Fapshi : <a href={link} target="_blank" rel="noopener" className="font-bold text-pen underline">ouvrir la page de paiement</a>. Ce compte se met à jour tout seul.</p>
          ) : (
            <p className="mt-3">Une demande de <b>{formatXaf(PLANS[plan].price)}</b> a été envoyée au {phone}. Valide-la avec ton code secret.</p>
          )}
        </div>
      )}
      {phase === "paid" && <p className="rounded-md bg-board/10 p-4 font-bold text-board">C&apos;est payé : ton pass est actif. <Link href="/document" className="underline">Mettre un document en forme</Link></p>}
      {phase === "failed" && (
        <p className="rounded-md bg-pin/10 p-4">Le paiement n&apos;a pas abouti. <button type="button" className="font-bold underline" onClick={() => setPhase("idle")}>Réessayer</button> ou <Link href="/aide" className="font-bold underline">écris-nous</Link>.</p>
      )}

      <h2>Mes messages</h2>
      {tickets.length === 0 ? (
        <p className="text-[15px]">Un problème ? <Link href="/aide" className="font-semibold underline">Écris-nous</Link>, on te répond ici.</p>
      ) : (
        <ul className="!list-none space-y-2 !pl-0">
          {tickets.map((t) => (
            <li key={t.id} className="!ml-0 !list-none">
              <Link href={`/aide/?t=${t.id}`} className="block rounded-md p-3 ring-1 ring-black/10 hover:bg-ink/[0.03]">
                <span className={`text-[13px] font-bold ${t.status === "ANSWERED" ? "text-pen" : "text-ink/55"}`}>{TICKET_LABEL[t.status]}</span>
                <span className="block truncate text-[15px]">{t.last}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <button type="button" onClick={signOut} className="text-[15px] font-semibold text-ink/60 underline">Se déconnecter sur cet appareil</button>
    </>
  );
}
