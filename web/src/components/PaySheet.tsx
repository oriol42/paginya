"use client";

import { useEffect, useRef, useState } from "react";
import { ADMIN_KEY, api, formatXaf, operatorOf, type OrderStatus } from "@/lib/api";
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

  useEffect(() => {
    if (phase !== "pending") return;
    startedAt.current = Date.now();
    const t = setInterval(async () => {
      try {
        const o = await api.getOrder(orderId);
        onStatus(o.status);
        if (o.status === "PAID") setPhase("paid");
        else if (o.status === "FAILED" || o.status === "EXPIRED") setPhase("failed");
        else if (Date.now() - startedAt.current > PENDING_TIMEOUT_MS) setPhase("failed");
      } catch { /* keep polling on flaky networks */ }
    }, 3000);
    return () => clearInterval(t);
  }, [phase, orderId, onStatus]);

  const operator = operatorOf(phone);

  async function pay() {
    setError("");
    setBusy(true);
    try {
      try { localStorage.setItem(PHONE_KEY, phone); } catch { /* ignore */ }
      const o = await api.pay(orderId, phone);
      // Normally the customer confirms on their phone (direct pay). Fapshi's payment page is only a fallback.
      if (o.pay_link) setLink(o.pay_link);
      onStatus(o.status);
      setPhase(o.status === "PAID" ? "paid" : "pending");
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
    const o = await api.retry(orderId).catch(() => null);
    if (o) onStatus(o.status);
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

            <div className="mt-5 flex items-end justify-between border-t border-dashed border-ink/25 pt-4">
              <span className="text-[15px] font-semibold text-ink/60">À payer</span>
              <span className="font-display text-[40px] leading-none font-black tabular">{formatXaf(amount)}</span>
            </div>

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
              {busy ? "Envoi…" : `Payer ${formatXaf(amount)}`}
            </PinLabel>
            <p className="mt-3 flex items-center justify-center gap-1.5 text-center text-[13px] text-ink/55">
              <Icon name="shield-check" size={15} /> MTN MoMo ou Orange Money · paiement sécurisé Fapshi
            </p>
            {adminPass && (
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
                Choisis MTN MoMo ou Orange Money et paie <b>{formatXaf(amount)}</b>. Cette page se débloque toute seule dès que c&apos;est payé.{" "}
                <a href={link} target="_blank" rel="noopener" className="font-bold text-pen underline">Ouvrir la page de paiement</a>
              </p>
            ) : (
              <p className="mx-auto mt-3 max-w-xs text-[16px] text-ink/75">
                Une demande de <b>{formatXaf(amount)}</b> a été envoyée au {phone}. Valide-la avec ton code secret.
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
          </div>
        )}
      </div>
    </div>
  );
}
