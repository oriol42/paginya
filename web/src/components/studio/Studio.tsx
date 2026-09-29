"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, type Order } from "@/lib/api";
import { STYLES, loadCoverFonts, renderCover } from "@/lib/cover";
import { KINDS } from "@/lib/cover/kinds";
import { PALETTES } from "@/lib/cover/palettes";
import type { CoverForm, StyleId } from "@/lib/cover/types";
import { CoverView } from "../CoverView";
import { Logo } from "../Logo";
import { PaySheet } from "../PaySheet";
import { KindPicker } from "./KindPicker";
import { ORDER_KEY, STORAGE_KEY, initialState, missingFields, switchKind, type StudioState } from "./state";
import { DetailsStep, EssentialsStep } from "./Steps";
import { StyleStep } from "./StyleStep";
import { Icon } from "@/components/Icon";

const STEPS = [
  { title: "L'essentiel", hint: "3 infos et c'est presque fini." },
  { title: "Les détails", hint: "Tout est facultatif : remplis ce que tu as." },
  { title: "Le style", hint: "Choisis le look et la couleur." },
];

export function Studio() {
  const params = useSearchParams();
  const [state, setState] = useState<StudioState>(initialState);
  const [step, setStep] = useState(0); // 0 = document type, 1..3 = wizard
  const [fontsReady, setFontsReady] = useState(false);
  const [order, setOrder] = useState<Order | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [zoom, setZoom] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState<StudioState | null>(null); // last cover of this phone: offered, never forced

  // Fonts first (text measurement depends on them), then restore the draft or the ?commande=<id> link.
  useEffect(() => {
    const fromLink = params.get("commande");
    loadCoverFonts().then(() => {
      const orderId = fromLink;
      try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) setDraft({ ...initialState(), ...JSON.parse(saved) });
      } catch { /* private mode */ }
      setFontsReady(true);
      if (orderId) {
        api.getOrder(orderId).then((o) => {
          if (o.is_document) return;
          setOrder(o);
          if ((o.form as { form?: unknown }).form) {
            setState(o.form as unknown as StudioState);
            setStep(1);
          }
        }).catch(() => {});
      }
    });
  }, [params]);

  useEffect(() => {
    if (!fontsReady || step === 0) return;
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch { /* quota / private mode */ }
  }, [state, fontsReady, step]);

  const palette = PALETTES.find((p) => p.id === state.paletteId) ?? PALETTES[0];
  const opts = useMemo(() => ({ palette, mono: state.mono, frame: state.frame }), [palette, state.mono, state.frame]);
  const svg = useMemo(() => (fontsReady ? renderCover(state.form, state.style, opts) : ""), [fontsReady, state.form, state.style, opts]);
  const thumbs = useMemo(() => {
    if (!fontsReady || step !== 3) return null;
    return Object.fromEntries(STYLES.map((s) => [s.id, renderCover(state.form, s.id, opts)])) as Record<StyleId, string>;
  }, [fontsReady, step, state.form, opts]);

  const patchForm = useCallback((patch: Partial<CoverForm>) => setState((s) => ({ ...s, form: { ...s.form, ...patch } })), []);
  const onStatus = useCallback((status: Order["status"]) => setOrder((o) => (o ? { ...o, status } : o)), []);

  const paid = order?.status === "PAID" && order.editable;
  const retour = params.get("retour");
  const backToDocument = retour?.startsWith("/document") ? `${retour}${retour.includes("?") ? "&" : "?"}cover=1` : null;

  async function download() {
    if (!fontsReady) return;
    const exportSvg = renderCover(state.form, state.style, opts, false); // never the preview's example text
    setError("");
    setBusy(true);
    try {
      let o: Order;
      if (order && order.editable && order.status !== "PENDING") {
        o = await api.updateOrder(order.id, exportSvg, state).catch(() => api.createOrder(exportSvg, state));
      } else if (order?.status === "PENDING") {
        o = order;
      } else {
        o = await api.createOrder(exportSvg, state);
      }
      setOrder(o);
      try { localStorage.setItem(ORDER_KEY, o.id); } catch { /* ignore */ }
      setSheetOpen(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (step === 0) {
    return (
      <Frame>
        {draft && (
          <div className="mx-auto w-full max-w-3xl px-5 pt-6">
            <button
              type="button"
              onClick={() => {
                setState(draft);
                setStep(1);
                // its order comes back too: a cover already paid is downloaded again for free
                const saved = (() => { try { return localStorage.getItem(ORDER_KEY); } catch { return null; } })();
                if (saved) api.getOrder(saved).then((o) => { if (!o.is_document) setOrder(o); }).catch(() => {});
              }} className="paper press flex w-full items-center gap-3 rounded-[2px] px-4 py-3 text-left">
              <Icon name="rotate-ccw" size={20} className="text-board" />
              <span className="min-w-0 flex-1">
                <span className="block font-bold">Reprendre ma dernière page de garde</span>
                <span className="block truncate text-[13px] text-ink/60">{draft.form.title || KINDS[draft.form.kind].label}</span>
              </span>
              <Icon name="chevron-right" size={18} className="text-ink/40" />
            </button>
          </div>
        )}
        <KindPicker onPick={(k) => { setState((s) => ({ ...switchKind(draft ? { ...s, form: { ...s.form, title: "" } } : s, k), style: KINDS[k].defaultStyle })); setStep(1); }} />
      </Frame>
    );
  }

  const current = STEPS[step - 1];
  const last = step === 3;
  const primary = last ? (
    backToDocument ? (
      <Link href={backToDocument} className="flex flex-1 items-center justify-center gap-2 rounded-md bg-ink px-5 py-4 font-display text-lg font-bold text-white shadow-lg active:scale-[.98]">
        Utiliser dans mon document <Icon name="arrow-right" size={18} />
      </Link>
    ) : (
      <button type="button" onClick={download} disabled={busy} className="flex flex-1 items-center justify-between rounded-md bg-brand-500 px-5 py-3.5 text-white transition hover:bg-brand-600 active:scale-[.98] disabled:opacity-60">
        <span className="text-left">
          <span className="block font-display text-lg leading-tight font-bold">{busy ? "Préparation…" : paid ? "Télécharger à nouveau" : "Télécharger ma page de garde"}</span>
          <span className="block text-xs text-white/80">Word + PDF · qualité impression</span>
        </span>
        <span className="text-xl">⬇</span>
      </button>
    )
  ) : (
    <button type="button" onClick={() => setStep(step + 1)} className="flex flex-1 items-center justify-center gap-2 rounded-md bg-brand-500 px-5 py-4 font-display text-lg font-bold text-white transition hover:bg-brand-600 active:scale-[.98]">
      {step === 2 ? "Voir les styles" : "Continuer"} <Icon name="arrow-right" size={18} />
    </button>
  );

  return (
    <Frame kind={KINDS[state.form.kind].label} onKind={() => setStep(0)}>
      <div className="mx-auto grid w-full max-w-6xl flex-1 grid-cols-[minmax(0,1fr)] lg:grid-cols-[minmax(0,480px)_minmax(0,1fr)] lg:gap-10 lg:px-5">
        <div className="px-5 pt-5 pb-40 lg:px-0 lg:pt-8 lg:pb-16">
          {/* Progress */}
          <div className="grid grid-cols-3 gap-1.5">
            {STEPS.map((s, i) => (
              <button key={s.title} type="button" onClick={() => setStep(i + 1)} className="group text-left" aria-label={s.title}>
                <span className={`block h-1.5 rounded-full transition ${i + 1 <= step ? "bg-brand-500" : "bg-ink/10 group-hover:bg-slate-300"}`} />
                <span className={`mt-1.5 block text-[11px] font-bold ${i + 1 === step ? "text-brand-700" : "text-ink/45"}`}>{s.title}</span>
              </button>
            ))}
          </div>

          <div className="mt-5 flex items-start gap-4">
            <div className="flex-1">
              <h1 className="font-display text-[1.7rem] leading-tight font-extrabold text-ink">{current.title}</h1>
              <p className="mt-1 text-[15px] text-ink/60">{current.hint}</p>
            </div>
            {/* Mobile live preview (desktop has the big one) */}
            {!last && (
              <button type="button" onClick={() => setZoom(true)} className="relative w-[92px] shrink-0 lg:hidden" aria-label="Agrandir l'aperçu">
                {svg ? <CoverView svg={svg} watermark={!paid} /> : <div className="aspect-[595/842] rounded bg-paper shadow" />}
                <span className="absolute -right-1.5 -bottom-1.5 grid h-7 w-7 place-items-center rounded-full bg-ink text-xs text-white shadow">⤢</span>
              </button>
            )}
          </div>

          <div className="mt-6">
            {step === 1 && <EssentialsStep form={state.form} onChange={patchForm} />}
            {step === 2 && <DetailsStep form={state.form} onChange={patchForm} />}
            {step === 3 && (
              <StyleStep
                style={state.style}
                paletteId={state.paletteId}
                mono={state.mono}
                frame={state.frame}
                thumbs={thumbs}
                onStyle={(style) => setState((s) => ({ ...s, style, styleTouched: true }))}
                onPalette={(paletteId) => setState((s) => ({ ...s, paletteId }))}
                onMono={(mono) => setState((s) => ({ ...s, mono }))}
                onFrame={(frame) => setState((s) => ({ ...s, frame }))}
              />
            )}
          </div>

          {error && <p className="mt-4 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

          {/* Desktop actions */}
          <div className="mt-8 hidden gap-3 lg:flex">
            <button type="button" onClick={() => setStep(step - 1)} className="rounded-md bg-paper px-5 font-bold text-ink/70 ring-1 ring-black/10" aria-label="Retour"><Icon name="arrow-left" /></button>
            {primary}
          </div>
          {step === 2 && (
            <button type="button" onClick={() => setStep(3)} className="mt-4 hidden w-full text-center text-sm font-semibold text-ink/60 lg:block">Passer cette étape</button>
          )}
        </div>

        {/* Desktop preview */}
        <div className="hidden lg:block">
          <div className="sticky top-20 pt-8">
            <div className="rounded-md bg-[radial-gradient(circle_at_50%_20%,#d1fae5,transparent_70%)] p-8">
              <div className="mx-auto w-full max-w-[440px]">
                {svg ? <CoverView svg={svg} watermark={!paid} /> : <div className="aspect-[595/842] animate-pulse rounded bg-paper shadow" />}
              </div>
            </div>
            <p className="mt-3 text-center text-xs text-ink/60">
              {paid ? "Payé · modifications gratuites 7 jours" : "Aperçu en direct · les textes d'exemple ne seront pas imprimés"}
            </p>
          </div>
        </div>
      </div>

      {/* Mobile action bar */}
      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-black/10 bg-paper/95 px-4 pt-3 pb-[max(.75rem,env(safe-area-inset-bottom))] backdrop-blur lg:hidden">
        {step === 2 && (
          <button type="button" onClick={() => setStep(3)} className="mb-2 w-full text-center text-sm font-semibold text-ink/60">Passer cette étape</button>
        )}
        <div className="flex gap-2.5">
          <button type="button" onClick={() => setStep(step - 1)} className="grid w-14 shrink-0 place-items-center rounded-md bg-ink/5 text-lg font-bold text-ink/70" aria-label="Retour"><Icon name="arrow-left" /></button>
          {primary}
        </div>
      </div>

      {zoom && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/80 p-6 backdrop-blur-sm" onClick={() => setZoom(false)}>
          <div className="pop w-full max-w-[min(92vw,62vh)]">
            <CoverView svg={svg} watermark={!paid} />
            <p className="mt-3 text-center text-sm text-white/80">Touche pour fermer</p>
          </div>
        </div>
      )}

      {sheetOpen && order && (
        <PaySheet
          orderId={order.id}
          amount={order.amount}
          status={order.status}
          heading="Ta page de garde est prête"
          bullets={["Word + PDF + image, sans filigrane", "Qualité impression (300 dpi)", "Modifications gratuites pendant 7 jours"]}
          formats={["pdf", "docx", "png"]}
          sharePath={`/garde?commande=${order.id}`}
          missing={missingFields(state)}
          onStatus={onStatus}
          onClose={() => setSheetOpen(false)}
        />
      )}
    </Frame>
  );
}

function Frame({ children, kind, onKind }: { children: React.ReactNode; kind?: string; onKind?: () => void }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="board sticky top-0 z-30 border-b border-black/25 pt-[env(safe-area-inset-top)]">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <Link href="/" className="press grid h-10 w-10 place-items-center rounded-md text-white/80 hover:bg-paper/10 hover:text-white" aria-label="Accueil"><Icon name="arrow-left" /></Link>
            <Logo tone="board" />
          </div>
          {kind && onKind && (
            <button type="button" onClick={onKind} className="rounded-full bg-ink/5 px-3 py-1.5 text-xs font-bold text-ink/70 hover:bg-ink/10">
              {kind} ▾
            </button>
          )}
        </div>
      </header>
      {children}
    </div>
  );
}
