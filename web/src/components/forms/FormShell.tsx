"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import type { OrderStatus } from "@/lib/api";
import { forms, type FormKind, type FormView } from "@/lib/forms";
import { Logo } from "../Logo";
import { PaySheet } from "../PaySheet";

type Props<T> = {
  kind: FormKind;
  title: string;
  initial: T;
  missing: (data: T) => string[];
  children: (data: T, set: (patch: Partial<T>) => void, view: FormView | null) => React.ReactNode;
  heading: string;
  bullets: string[];
};

/** Form on one side, the real Word/PDF rendering on the other, re-rendered as you type. */
export function FormShell<T extends object>({ kind, title, initial, missing, children, heading, bullets }: Props<T>) {
  const params = useSearchParams();
  const storeKey = `paginya:${kind}:draft`;
  const [data, setData] = useState<T>(initial);
  const [view, setView] = useState<FormView | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"form" | "preview">("form");
  const [payOpen, setPayOpen] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latest = useRef(data);
  const viewRef = useRef<FormView | null>(null);

  // Restore: ?id=<order> (link kept on WhatsApp) or the local draft.
  useEffect(() => {
    const id = params.get("id") ?? (() => { try { return localStorage.getItem(`${storeKey}:id`); } catch { return null; } })();
    try {
      const saved = localStorage.getItem(storeKey);
      if (saved) {
        const parsed = JSON.parse(saved) as T;
        latest.current = parsed;
        queueMicrotask(() => setData(parsed));
      }
    } catch { /* ignore */ }
    if (id) {
      forms.get(id).then((v) => {
        if (v.kind !== kind) return;
        viewRef.current = v;
        latest.current = v.data as T;
        setView(v);
        setData(v.data as T);
      }).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const save = useCallback(async () => {
    setBusy(true);
    setError("");
    try {
      const current = viewRef.current;
      const v = current ? await forms.update(current.id, latest.current) : await forms.create(kind, latest.current);
      viewRef.current = v;
      setView(v);
      try { localStorage.setItem(`${storeKey}:id`, v.id); } catch { /* ignore */ }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, [kind, storeKey]);

  const set = useCallback((patch: Partial<T>) => {
    setData((d) => {
      const next = { ...d, ...patch };
      latest.current = next;
      try { localStorage.setItem(storeKey, JSON.stringify(next)); } catch { /* ignore */ }
      return next;
    });
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(save, 1100);
  }, [save, storeKey]);

  // First render of the preview as soon as the page opens.
  useEffect(() => {
    const t = setTimeout(() => { if (!viewRef.current) save(); }, 400);
    return () => clearTimeout(t);
  }, [save]);

  const onStatus = useCallback(async (status: OrderStatus) => {
    setView((v) => (v ? { ...v, status } : v));
    if (status === "PAID" && viewRef.current) setView(await forms.refresh(viewRef.current.id));
  }, []);

  const paid = view?.status === "PAID" && view.editable;
  const pages = view?.render?.pages ?? 0;

  const preview = (
    <div className={`relative space-y-4 transition ${busy ? "opacity-60" : ""}`}>
      {!view && <div className="aspect-[210/297] animate-pulse rounded bg-white shadow" />}
      {view && Array.from({ length: pages }, (_, i) => (
        // eslint-disable-next-line @next/next/no-img-element
        <img key={`${i}-${view.render!.version}`} src={forms.pageUrl(view.id, i + 1, view.render!.version)} alt={`Page ${i + 1}`} className="aspect-[210/297] w-full rounded-[4px] bg-white shadow-[0_1px_2px_rgba(15,23,42,.06),0_12px_32px_-12px_rgba(15,23,42,.25)]" />
      ))}
    </div>
  );

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-30 border-b border-slate-100 bg-white/85 pt-[env(safe-area-inset-top)] backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <Link href="/" className="grid h-9 w-9 place-items-center rounded-full text-xl text-slate-600 hover:bg-slate-100" aria-label="Accueil">←</Link>
            <Logo />
          </div>
          <span className={`rounded-full bg-ink px-3 py-1.5 text-xs font-bold text-white transition ${busy ? "opacity-100" : "opacity-0"}`}>⏳ Mise à jour…</span>
        </div>
      </header>

      {/* Mobile: form | preview switch */}
      <div className="sticky top-14 z-20 border-b border-slate-100 bg-[#f7faf9]/95 px-4 py-2 backdrop-blur lg:hidden">
        <div className="grid grid-cols-2 rounded-2xl bg-slate-200/70 p-1">
          {(["form", "preview"] as const).map((t) => (
            <button key={t} type="button" onClick={() => setTab(t)} className={`rounded-xl py-2 text-sm font-bold ${tab === t ? "bg-white text-ink shadow-sm" : "text-slate-500"}`}>
              {t === "form" ? "✏️ Remplir" : "👀 Aperçu"}
            </button>
          ))}
        </div>
      </div>

      <div className="mx-auto grid w-full max-w-6xl flex-1 grid-cols-[minmax(0,1fr)] gap-8 px-4 pt-5 pb-40 lg:grid-cols-[minmax(0,1fr)_minmax(0,520px)] lg:px-5 lg:pb-16">
        <div className={tab === "form" ? "" : "hidden lg:block"}>
          <h1 className="font-display text-[1.9rem] leading-tight font-extrabold text-ink">{title}</h1>
          {/* `set` is only called from event handlers inside the form, never while rendering. */}
          {/* eslint-disable-next-line react-hooks/refs */}
          <div className="mt-6">{children(data, set, view)}</div>
          {error && <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        </div>
        <div className={tab === "preview" ? "" : "hidden lg:block"}>
          <div className="lg:sticky lg:top-20">{preview}</div>
        </div>
      </div>

      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-100 bg-white/95 px-4 pt-3 pb-[max(.75rem,env(safe-area-inset-bottom))] backdrop-blur">
        <div className="mx-auto max-w-6xl lg:flex lg:justify-end">
          <button
            type="button"
            onClick={() => setPayOpen(true)}
            disabled={!view || busy}
            className="w-full rounded-2xl bg-brand-500 px-5 py-3.5 text-white shadow-lg shadow-brand-500/25 transition hover:bg-brand-600 active:scale-[.98] disabled:opacity-60 lg:w-[420px]"
          >
            <span className="block font-display text-lg leading-tight font-bold">{paid ? "Télécharger à nouveau" : "Télécharger"}</span>
            <span className="block text-xs text-white/80">Word + PDF · sans filigrane</span>
          </button>
        </div>
      </div>

      {payOpen && view && (
        <PaySheet
          orderId={view.id}
          amount={view.amount}
          status={view.status}
          heading={heading}
          bullets={bullets}
          formats={["pdf", "docx"]}
          sharePath={`/${kind}?id=${view.id}`}
          missing={missing(data)}
          onStatus={onStatus}
          onClose={() => setPayOpen(false)}
        />
      )}
    </div>
  );
}
