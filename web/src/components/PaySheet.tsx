"use client";

import { useEffect, useRef, useState } from "react";
import { api, formatXaf, operatorOf, type OrderStatus } from "@/lib/api";

export const PHONE_KEY = "propre:phone";
type Phase = "summary" | "pending" | "paid" | "failed";
const PENDING_TIMEOUT_MS = 3 * 60 * 1000;
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
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
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
      onStatus(o.status);
      setPhase(o.status === "PAID" ? "paid" : "pending");
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
      className="fixed inset-0 z-50 flex items-end justify-center bg-ink/50 backdrop-blur-sm sm:items-center"
      onClick={phase === "pending" ? undefined : onClose}
    >
      <div
        className="sheet-in w-full max-w-md rounded-t-[28px] bg-white p-6 pb-[max(1.5rem,env(safe-area-inset-bottom))] shadow-2xl sm:rounded-[28px]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mx-auto mb-5 h-1.5 w-10 rounded-full bg-slate-200 sm:hidden" />

        {phase === "summary" && (
          <>
            <p className="text-sm font-semibold text-brand-600">{heading}</p>
            <h2 className="mt-1 font-display text-[26px] leading-tight font-extrabold text-ink">C&apos;est propre !</h2>
            <ul className="mt-4 space-y-2.5 text-[15px] text-slate-700">
              {bullets.map((b) => (
                <li key={b} className="flex gap-2.5">
                  <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-brand-100 text-[11px] font-bold text-brand-700">✓</span>
                  {b}
                </li>
              ))}
            </ul>

            {missing.length > 0 && (
              <p className="mt-4 rounded-2xl bg-amber-50 px-3.5 py-3 text-sm text-amber-800 ring-1 ring-amber-200">
                Il manque encore {missing.join(", ")}. Tu pourras compléter après (7 jours gratuits).
              </p>
            )}

            <label className="mt-5 block">
              <span className="mb-1.5 block text-[13px] font-semibold text-slate-700">Ton numéro Mobile Money</span>
              <div className="flex items-center rounded-2xl bg-slate-50 ring-1 ring-slate-200 focus-within:bg-white focus-within:ring-2 focus-within:ring-brand-500">
                <span className="pl-4 text-[15px] font-semibold text-slate-500">+237</span>
                <input
                  inputMode="tel"
                  autoComplete="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="6 70 00 00 00"
                  className="w-full border-0 bg-transparent px-2 py-3.5 text-lg tracking-wide focus:outline-none"
                />
                {operator && (
                  <span className={`mr-2 shrink-0 rounded-lg px-2 py-1 text-xs font-bold ${operator === "MTN MoMo" ? "bg-yellow-300 text-ink" : "bg-orange-500 text-white"}`}>
                    {operator}
                  </span>
                )}
              </div>
            </label>
            {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

            <button
              type="button"
              disabled={busy || phone.replace(/\D/g, "").length < 9}
              onClick={pay}
              className="mt-5 w-full rounded-2xl bg-brand-500 py-4 font-display text-lg font-bold text-white shadow-lg shadow-brand-500/25 transition hover:bg-brand-600 active:scale-[.98] disabled:opacity-50"
            >
              {busy ? "Envoi…" : `Payer ${formatXaf(amount)}`}
            </button>
            <p className="mt-3 text-center text-xs text-slate-500">
              Tu recevras une demande de confirmation sur ton téléphone · Paiement sécurisé Fapshi
            </p>
          </>
        )}

        {phase === "pending" && (
          <div className="py-4 text-center">
            <div className="relative mx-auto h-20 w-20">
              <div className="absolute inset-0 animate-ping rounded-full bg-brand-200/60" />
              <div className="relative grid h-20 w-20 place-items-center rounded-full bg-brand-500 text-3xl">📱</div>
            </div>
            <h2 className="mt-6 font-display text-xl font-bold text-ink">Confirme sur ton téléphone</h2>
            <p className="mx-auto mt-2 max-w-xs text-[15px] text-slate-600">
              Une demande de <b>{formatXaf(amount)}</b> a été envoyée au {phone}. Valide-la avec ton code secret.
            </p>
            <p className="mt-5 text-xs text-slate-400">Ne ferme pas cette page…</p>
          </div>
        )}

        {phase === "paid" && (
          <div className="text-center">
            <div className="pop mx-auto grid h-20 w-20 place-items-center rounded-full bg-brand-500 text-4xl text-white shadow-lg shadow-brand-500/30">✓</div>
            <h2 className="mt-5 font-display text-2xl font-extrabold text-ink">C&apos;est propre ! 🎉</h2>
            <p className="mt-1 text-[15px] text-slate-600">Télécharge ton fichier :</p>
            <div className={`mt-5 grid gap-2 ${formats.length === 3 ? "grid-cols-3" : "grid-cols-2"}`}>
              {formats.map((fmt) => (
                <a
                  key={fmt}
                  href={api.fileUrl(orderId, fmt)}
                  className="rounded-2xl bg-brand-50 py-3.5 font-display font-bold text-brand-700 ring-1 ring-brand-100 hover:bg-brand-100"
                >
                  {FORMAT_LABEL[fmt]}
                </a>
              ))}
            </div>
            <a
              href={`https://wa.me/?text=${encodeURIComponent(`Mon document Paginya (modifiable 7 jours) : ${shareUrl}`)}`}
              target="_blank"
              rel="noreferrer"
              className="mt-3 block rounded-2xl bg-[#25D366] py-3.5 font-bold text-white"
            >
              Garder le lien sur WhatsApp
            </a>
            <p className="mt-3 text-xs text-slate-500">Modifications et téléchargements gratuits pendant 7 jours avec ce lien.</p>
            <button type="button" onClick={onClose} className="mt-3 text-sm font-semibold text-slate-600">Fermer</button>
          </div>
        )}

        {phase === "failed" && (
          <div className="py-2 text-center">
            <div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-amber-100 text-3xl">⚠️</div>
            <h2 className="mt-4 font-display text-xl font-bold text-ink">Le paiement n&apos;a pas abouti</h2>
            <p className="mt-2 text-[15px] text-slate-600">Rien n&apos;a été débité. Vérifie ton solde ou essaie un autre numéro.</p>
            <button type="button" onClick={retry} className="mt-5 w-full rounded-2xl bg-brand-500 py-4 font-display text-lg font-bold text-white">
              Réessayer
            </button>
            <button type="button" onClick={onClose} className="mt-3 text-sm font-semibold text-slate-600">Plus tard</button>
          </div>
        )}
      </div>
    </div>
  );
}
