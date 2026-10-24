"use client";

import { useEffect, useRef, useState } from "react";
import { ADMIN_KEY, api, formatXaf, operatorOf, type OrderStatus } from "@/lib/api";
import { track } from "@/lib/track";
import { canUnlock, hasPass, keepAccount, refreshAccount, savedAccount, type Account } from "@/lib/account";
import { PLANS, type Plan } from "@/lib/plans";
import { GoogleButton } from "./GoogleButton";
import { Icon } from "./Icon";
import { PinLabel } from "./ui";

export const PHONE_KEY = "propre:phone";
type Phase = "summary" | "pending" | "paid" | "failed";
const PENDING_TIMEOUT_MS = 10 * 60 * 1000; // the Fapshi payment page can take a few minutes
type Format = "pdf" | "docx" | "png";

type Props = {
  orderId: string;
  amount: number;
  status: OrderStatus;
  heading: string;
  bullets: string[];
  formats: Format[];
  sharePath: string;
  missing?: string[];
  onStatus: (s: OrderStatus) => void;
  onClose: () => void;
};

const FORMAT_LABEL: Record<Format, string> = { pdf: "PDF", docx: "Word", png: "Image" };

export function PaySheet({ orderId, amount, status, heading, bullets, formats, sharePath, missing = [], onStatus, onClose }: Props) {
  const [phase, setPhase] = useState<Phase>(status === "PAID" ? "paid" : status === "PENDING" ? "pending" : "summary");
  const [phone, setPhone] = useState(() => {
    try { return localStorage.getItem(PHONE_KEY) ?? ""; } catch { return ""; }
  });
  const [adminPass] = useState(() => {
    try { return localStorage.getItem(ADMIN_KEY) ?? ""; } catch { return ""; }
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [link, setLink] = useState<string | null>(null);
  const startedAt = useRef(0);
  // The 30-day pass lives on a Google account (never lost with the phone); a team account never pays.
  const [account, setAccount] = useState<Account | null>(() => savedAccount());
  const [accountsOn, setAccountsOn] = useState(false);
  // The Essentiel pass is offered first: most customers come back for another document.
  const [choice, setChoice] = useState<Plan | "doc">(() => (hasPass(savedAccount()) ? "doc" : "essentiel"));
  const [showSignIn, setShowSignIn] = useState(false);
  // What is being paid right now: this document, or a pass order (the document is unlocked right after).
  const [paying, setPaying] = useState<{ id: string; amount: number }>({ id: orderId, amount });
  const paidByPhone = useRef(false); // a team or pass unlock is not a sale

  useEffect(() => {
    if (status !== "PAID") track("pay_open");
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- once, when the sheet opens

  useEffect(() => {
    if (phase === "paid" && paidByPhone.current) {
      paidByPhone.current = false;
      track("paid", paying.amount);
    }
  }, [phase, paying.amount]);

  useEffect(() => {
    refreshAccount().then(setAccount);
    api.accountConfig().then(({ client_id }) => setAccountsOn(!!client_id)).catch(() => {});
  }, []);

  async function signIn(credential: string) {
    setError("");
    try {
      const a = await api.accountGoogle(credential);
      keepAccount(a);
      setAccount(a);
      if (choice === "doc" && !canUnlock(a) && !hasPass(a)) setError("Pas de pass actif sur ce compte. Prends-en un ou paie ce document.");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  /** Active pass or team account: the document is unlocked on the server, no payment. */
  async function unlockWithAccount() {
    if (!account) return;
    setError("");
    setBusy(true);
    try {
      const o = await api.unlock(orderId, account.token);
      onStatus(o.status);
      setPhase("paid");
    } catch (e) {
      setError((e as Error).message);
      refreshAccount().then(setAccount);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (phase !== "pending") return;
    startedAt.current = Date.now();
    const t = setInterval(async () => {
      try {
        const o = await api.getOrder(paying.id);
        if (paying.id === orderId) onStatus(o.status);
        if (o.status === "PAID" && paying.id !== orderId) {
          // the pass is paid: it now unlocks this document
          clearInterval(t);
          const a = await refreshAccount();
          setAccount(a);
          try {
            const d = await api.unlock(orderId, a!.token);
            onStatus(d.status);
            setPhase("paid");
          } catch {
            setPhase("summary"); // the pass is on the account: "Télécharger sans payer" is shown there
          }
        } else if (o.status === "PAID") setPhase("paid");
        else if (o.status === "FAILED" || o.status === "EXPIRED") setPhase("failed");
        else if (Date.now() - startedAt.current > PENDING_TIMEOUT_MS) setPhase("failed");
      } catch { /* keep polling on flaky networks */ }
    }, 3000);
    return () => clearInterval(t);
  }, [phase, orderId, paying.id, onStatus]);

  const operator = operatorOf(phone);
  const options: [Plan | "doc", string, number, string][] = [
    ["essentiel", `Pass ${PLANS.essentiel.name} · 30 jours`, PLANS.essentiel.price, `${PLANS.essentiel.perDay} documents par jour · moins de 100 F par jour`],
    ["pro", `Pass ${PLANS.pro.name} · 30 jours`, PLANS.pro.price, `${PLANS.pro.perDay} documents par jour · ${PLANS.pro.who.toLowerCase()}`],
    ["doc", "Ce document seulement", amount, "Sans compte, n'importe quel document"],
  ].filter(([id]) => !(hasPass(account) && id === account!.plan)) as [Plan | "doc", string, number, string][]; // the current pass: renewed from the account page

  async function pay() {
    setError("");
    setBusy(true);
    try {
      try { localStorage.setItem(PHONE_KEY, phone); } catch { /* ignore */ }
      let target = { id: orderId, amount };
      if (choice !== "doc" && account) {
        const p = await api.buyPass(account.token, choice);
        target = { id: p.id, amount: p.amount };
      }
      setPaying(target);
      const o = await api.pay(target.id, phone);
      paidByPhone.current = true;
      track("pay_start");
      // Normally the customer confirms on their phone (direct pay). Fapshi's payment page is only a fallback.
      if (o.pay_link) setLink(o.pay_link);
      if (target.id === orderId) onStatus(o.status);
      setPhase(o.status === "PAID" && target.id === orderId ? "paid" : "pending");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function unlock() {
    setError("");
    setBusy(true);
    try {
      const o = await api.adminUnlock(orderId, adminPass);
      onStatus(o.status);
      setPhase("paid");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function retry() {
    const o = await api.retry(paying.id).catch(() => null);
    if (o && paying.id === orderId) onStatus(o.status);
    setPhase("summary");
  }

  const shareUrl = typeof window !== "undefined" ? `${window.location.origin}${sharePath}` : "";

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-board/75 sm:items-center"
      onClick={phase === "pending" ? undefined : onClose}
    >
      <div
        className="sheet-in paper relative w-full max-w-md rounded-t-xl px-6 pt-9 pb-[max(1.5rem,env(safe-area-inset-bottom))] sm:rounded-[2px]"
        onClick={(e) => e.stopPropagation()}
      >
        <span className="pin top-3 left-1/2 -translate-x-1/2" aria-hidden />

        {phase === "summary" && (
          <>
            <p className="text-[15px] font-semibold text-ink/60">{heading}</p>
            <h2 className="mt-1 font-display text-[34px] leading-[0.95] font-black uppercase">C&apos;est propre.</h2>
            <ul className="mt-4 space-y-2.5 text-[16px]">
              {bullets.map((b) => (
                <li key={b} className="flex gap-2.5">
                  <Icon name="check" size={18} stroke={2.6} className="mt-0.5 text-board" />
                  {b}
                </li>
              ))}
            </ul>

            {missing.length > 0 && (
              <p className="mt-4 flex gap-2 rounded-md bg-hi/40 px-3.5 py-3 text-[14px]">
                <Icon name="info" size={18} className="mt-0.5" />
                Il manque encore {missing.join(", ")}. Tu pourras compléter après (7 jours gratuits).
              </p>
            )}

            {canUnlock(account) ? (
              <>
                <p className="mt-5 flex items-center gap-2 border-t border-dashed border-ink/25 pt-4 text-[16px] font-bold text-board">
                  <Icon name="badge-check" size={20} />
                  {account!.team ? "Accès illimité" : `Pass ${PLANS[account!.plan as Plan]?.name ?? ""} · encore ${account!.pass_days} jour${account!.pass_days > 1 ? "s" : ""}`}
                </p>
                {!account!.team && (
                  <p className="mt-1 text-[14px] text-ink/65">{account!.used_today} / {account!.per_day} documents utilisés aujourd&apos;hui</p>
                )}
                {error && <p className="mt-2 flex gap-1.5 text-[14px] text-pin"><Icon name="triangle-alert" size={16} className="mt-0.5" />{error}</p>}
                <PinLabel className="mt-4 w-full" disabled={busy} onClick={unlockWithAccount}>{busy ? "…" : "Télécharger sans payer"}</PinLabel>
              </>
            ) : (
            <>
            {hasPass(account) && (
              <p className="mt-4 flex gap-2 rounded-md bg-hi/40 px-3.5 py-3 text-[14px]">
                <Icon name="info" size={18} className="mt-0.5" />
                Tu as utilisé tes {account!.per_day} documents du jour. Ça repart à minuit, ou paie celui-ci à part.
              </p>
            )}
            {accountsOn ? (
              <div className="mt-5 space-y-2 border-t border-dashed border-ink/25 pt-4">
                {options.map(([id, label, price, note]) => (
                  <button key={id} type="button" onClick={() => setChoice(id)} className={`relative flex w-full items-center justify-between gap-3 rounded-md px-3.5 py-3 text-left ring-1 ${choice === id ? "bg-hi/30 ring-2 ring-ink" : "ring-black/10"}`}>
                    {id === "essentiel" && <span className="absolute -top-2.5 right-3 rounded bg-board px-2 py-0.5 text-[11px] font-bold tracking-wide text-white uppercase">Conseillé</span>}
                    <span>
                      <span className="block text-[16px] font-bold">{label}</span>
                      <span className="text-[13px] text-ink/65">{note}</span>
                    </span>
                    <span className="shrink-0 font-display text-[26px] leading-none font-black tabular">{formatXaf(price)}</span>
                  </button>
                ))}
              </div>
            ) : (
              <div className="mt-5 flex items-end justify-between border-t border-dashed border-ink/25 pt-4">
                <span className="text-[15px] font-semibold text-ink/60">À payer</span>
                <span className="font-display text-[40px] leading-none font-black tabular">{formatXaf(amount)}</span>
              </div>
            )}

            {accountsOn && !account && (choice !== "doc" || showSignIn) ? (
              <div className="mt-4 rounded-md bg-hi/25 p-3.5">
                <p className="text-[14px] font-semibold">
                  {choice !== "doc" ? "Ton pass est gardé sur ton compte Google : tu le retrouves même si tu changes de téléphone." : "Connecte le compte Google de ton pass."}
                </p>
                <div className="mt-3"><GoogleButton onCredential={signIn} /></div>
                {error && <p className="mt-2 flex gap-1.5 text-[14px] text-pin"><Icon name="triangle-alert" size={16} className="mt-0.5" />{error}</p>}
              </div>
            ) : (
            <>

            <label className="mt-4 block">
              <span className="mb-1.5 block text-[13px] font-bold text-ink/80">Ton numéro Mobile Money</span>
              <div className="flex items-center rounded-md bg-paper shadow-[inset_0_-2px_0_0_rgba(22,24,26,0.18)] ring-1 ring-black/10 focus-within:shadow-[inset_0_-3px_0_0_var(--color-hi-deep)]">
                <span className="pl-3.5 text-[16px] font-bold text-ink/55">+237</span>
                <input
                  inputMode="tel"
                  autoComplete="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="6 70 00 00 00"
                  className="w-full border-0 bg-transparent px-2 py-3.5 text-[19px] tracking-wide tabular focus:outline-none"
                />
                {operator && (
                  <span className={`mr-2 shrink-0 rounded px-2 py-1 text-[12px] font-bold ${operator === "MTN MoMo" ? "bg-[#ffcc00] text-ink" : "bg-[#ff7900] text-white"}`}>
                    {operator}
                  </span>
                )}
              </div>
            </label>
            {error && <p className="mt-2 flex gap-1.5 text-[14px] text-pin"><Icon name="triangle-alert" size={16} className="mt-0.5" />{error}</p>}

            <PinLabel className="mt-5 w-full" disabled={busy || phone.replace(/\D/g, "").length < 9} onClick={pay}>
              {busy ? "Envoi…" : `Payer ${formatXaf(choice === "doc" ? amount : PLANS[choice].price)}`}
            </PinLabel>
            <p className="mt-3 flex items-center justify-center gap-1.5 text-center text-[13px] text-ink/55">
              <Icon name="shield-check" size={15} /> MTN MoMo ou Orange Money · paiement sécurisé Fapshi
            </p>
            </>
            )}
            {accountsOn && !account && choice === "doc" && !showSignIn && (
              <button type="button" onClick={() => setShowSignIn(true)} className="mt-2 w-full text-[14px] font-semibold text-ink/65 underline">J&apos;ai déjà un pass</button>
            )}
            {choice !== "doc" && (
              <p className="mt-2 text-center text-[12px] text-ink/55">Pas de renouvellement automatique : tu repaies seulement si tu veux continuer.</p>
            )}
            </>
            )}
            <a href={`/aide/?commande=${orderId}`} className="mt-3 block text-center text-[13px] font-semibold text-ink/55 underline">Un souci ? Écris-nous</a>
            {adminPass && !canUnlock(account) && (
              <button type="button" disabled={busy} onClick={unlock} className="mt-3 w-full text-[15px] font-bold text-board underline">
                Équipe Paginya : débloquer sans payer
              </button>
            )}
          </>
        )}

        {phase === "pending" && (
          <div className="py-2 text-center">
            <Icon name="smartphone" size={56} stroke={1.5} className="mx-auto animate-pulse text-board" />
            <h2 className="mt-4 font-display text-[30px] leading-[0.95] font-black uppercase">{link ? "Paie sur la page Fapshi" : "Confirme sur ton téléphone"}</h2>
            {link ? (
              <p className="mx-auto mt-3 max-w-xs text-[16px] text-ink/75">
                Choisis MTN MoMo ou Orange Money et paie <b>{formatXaf(paying.amount)}</b>. Cette page se débloque toute seule dès que c&apos;est payé.{" "}
                <a href={link} target="_blank" rel="noopener" className="font-bold text-pen underline">Ouvrir la page de paiement</a>
              </p>
            ) : (
              <p className="mx-auto mt-3 max-w-xs text-[16px] text-ink/75">
                Une demande de <b>{formatXaf(paying.amount)}</b> a été envoyée au {phone}. Valide-la avec ton code secret.
              </p>
            )}
            <p className="mt-5 flex items-center justify-center gap-2 text-[14px] text-ink/55"><Icon name="loader-circle" size={16} className="animate-spin" />On attend la confirmation…</p>
          </div>
        )}

        {phase === "paid" && (
          <div className="relative text-center">
            <span className="stamp stamp-in mx-auto text-[44px]">Payé</span>
            <h2 className="mt-6 font-display text-[30px] leading-[0.95] font-black uppercase">Ton document est à toi</h2>
            <div className={`mt-5 grid gap-2 ${formats.length === 3 ? "grid-cols-3" : "grid-cols-2"}`}>
              {formats.map((fmt) => (
                <a
                  key={fmt}
                  href={api.fileUrl(orderId, fmt)}
                  className="press inline-flex items-center justify-center gap-2 rounded-md bg-hi py-3.5 font-display text-[20px] leading-none font-black text-ink uppercase shadow-[0_2px_0_0_var(--color-hi-deep)]"
                >
                  <Icon name="download" size={18} stroke={2.5} />
                  {FORMAT_LABEL[fmt]}
                </a>
              ))}
            </div>
            <a
              href={`https://wa.me/?text=${encodeURIComponent(`Mon document Paginya (modifiable 7 jours) : ${shareUrl}`)}`}
              target="_blank"
              rel="noreferrer"
              className="press mt-3 flex items-center justify-center gap-2 rounded-md bg-[#1FAF55] py-3.5 text-[16px] font-bold text-white"
            >
              Garder le lien sur WhatsApp
            </a>
            <p className="mt-3 text-[13px] text-ink/55">Modifications et téléchargements gratuits pendant 7 jours avec ce lien.</p>
            <button type="button" onClick={onClose} className="mt-3 text-[15px] font-semibold text-ink/60 underline">Fermer</button>
          </div>
        )}

        {phase === "failed" && (
          <div className="py-2 text-center">
            <Icon name="triangle-alert" size={48} stroke={1.5} className="mx-auto text-pin" />
            <h2 className="mt-4 font-display text-[30px] leading-[0.95] font-black uppercase">Le paiement n&apos;a pas abouti</h2>
            <p className="mt-2 text-[16px] text-ink/70">Rien n&apos;a été débité. Vérifie ton solde ou essaie un autre numéro.</p>
            <PinLabel className="mt-5 w-full" onClick={retry}>Réessayer</PinLabel>
            <button type="button" onClick={onClose} className="mt-3 text-[15px] font-semibold text-ink/60 underline">Plus tard</button>
            <a href={`/aide/?commande=${paying.id}`} className="mt-3 block text-[14px] font-semibold text-ink/60 underline">On t&apos;a débité ? Écris-nous, on règle ça</a>
          </div>
        )}
      </div>
    </div>
  );
}
