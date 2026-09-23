"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import type { OrderStatus } from "@/lib/api";
import { KIND_LABEL, docs, type Block, type DocOptions, type DocStyle, type DocView } from "@/lib/documents";
import { Logo } from "../Logo";
import { PaySheet } from "../PaySheet";
import type { StudioState } from "../studio/state";
import { Segmented } from "../ui";
import { CoverEditor, coverIncomplete, coverSvgPreview, initialCover } from "./CoverEditor";
import { DocStylePanel } from "./DocStylePanel";
import { ImportScreen } from "./ImportScreen";
import { PlanPanel } from "./PlanPanel";
import { Working } from "./Working";

const LAST_DOC = "propre:doc:last";
type Panel = "style" | "cover" | "plan";
type View = "after" | "before" | "side";
type Patch = Partial<{ blocks: Block[]; style: DocStyle; options: DocOptions; cover_svg: string; remove_cover: boolean }>;

const PANELS: { id: Panel; icon: string; label: string }[] = [
  { id: "style", icon: "🎨", label: "Style" },
  { id: "cover", icon: "🏛️", label: "Garde" },
  { id: "plan", icon: "📑", label: "Plan" },
];

export function DocumentApp() {
  const params = useSearchParams();
  const router = useRouter();
  const [doc, setDoc] = useState<DocView | null>(null);
  const [phase, setPhase] = useState<"import" | "working" | "editor">("import");
  const [rendering, setRendering] = useState(false);
  const [error, setError] = useState("");
  const [panel, setPanel] = useState<Panel>("style");
  const [drawer, setDrawer] = useState(false); // mobile only
  const [view, setView] = useState<View>("after");
  const [beforePages, setBeforePages] = useState<number | null>(null);
  const [payOpen, setPayOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [cover, setCover] = useState<StudioState | null>(null);
  const pending = useRef<Patch>({});
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const chain = useRef<Promise<unknown>>(Promise.resolve());

  const openDoc = useCallback(async (view: DocView, fromStudio = false) => {
    setDoc(view);
    try { localStorage.setItem(LAST_DOC, view.id); } catch { /* ignore */ }
    router.replace(`/document?doc=${view.id}`, { scroll: false });
    let current = view;
    const needsCover = view.options.cover && (!view.has_cover || fromStudio);
    if (needsCover) {
      if (fromStudio) {
        try { localStorage.removeItem(`propre:doc:cover:${view.id}`); } catch { /* ignore */ }
      }
      current = await docs.update(view.id, { cover_svg: await coverSvgPreview(initialCover(view.id, view.meta)) });
    }
    if (!current.render || needsCover) {
      setRendering(true);
      current = await docs.render(view.id);
      setRendering(false);
    }
    setCover(initialCover(view.id, view.meta));
    setDoc(current);
    setPhase("editor");
  }, [router]);

  useEffect(() => {
    const id = params.get("doc") ?? (() => { try { return localStorage.getItem(LAST_DOC); } catch { return null; } })();
    const fromStudio = params.get("cover") === "1";
    if (!id) return;
    let cancelled = false;
    docs.get(id)
      .then((v) => { if (!cancelled) { setPhase("working"); return openDoc(v, fromStudio); } })
      .catch(() => {
        try { localStorage.removeItem(LAST_DOC); } catch { /* ignore */ }
        if (!cancelled) setPhase("import");
      });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function start(create: () => Promise<DocView>) {
    setError("");
    setPhase("working");
    try {
      const v = await create();
      setDoc(v);
      await openDoc(v);
    } catch (e) {
      setError((e as Error).message);
      setPhase("import");
      setRendering(false);
    }
  }

  /** Local change now, saved + re-rendered shortly after the last edit. */
  function change(patch: Patch) {
    setDoc((d) => (d ? { ...d, ...(patch as Partial<DocView>) } : d));
    pending.current = { ...pending.current, ...patch };
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(flush, 700);
  }

  function flush() {
    const id = doc?.id;
    if (!id) return;
    chain.current = chain.current.then(async () => {
      const patch = pending.current;
      pending.current = {};
      if (!Object.keys(patch).length) return;
      setRendering(true);
      setError("");
      try {
        await docs.update(id, patch);
        if (Object.keys(pending.current).length) return; // a newer edit will render
        setDoc(await docs.render(id));
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setRendering(false);
      }
    });
  }

  async function showView(v: View) {
    setView(v);
    if (v !== "after" && beforePages === null && doc) {
      setBeforePages(0);
      try { setBeforePages((await docs.before(doc.id)).pages); } catch { setBeforePages(-1); }
    }
  }

  const onStatus = useCallback(async (status: OrderStatus) => {
    setDoc((d) => (d ? { ...d, status } : d));
    if (status === "PAID" && doc) setDoc(await docs.render(doc.id)); // clean previews
  }, [doc]);

  function reset() {
    try { localStorage.removeItem(LAST_DOC); } catch { /* ignore */ }
    router.replace("/document");
    setDoc(null);
    setBeforePages(null);
    setView("after");
    setPhase("import");
  }

  async function remove() {
    if (!doc) return;
    await docs.remove(doc.id).catch(() => null);
    reset();
  }

  if (phase === "import" || !doc) {
    return (
      <Shell>
        {phase === "working" ? <Working meta={null} rendering={false} /> : (
          <ImportScreen error={error} onText={(t) => start(() => docs.fromText(t))} onFile={(f) => start(() => docs.fromFile(f))} />
        )}
      </Shell>
    );
  }
  if (phase === "working") return <Shell><Working meta={doc.meta} rendering={rendering} /></Shell>;

  const pages = doc.render?.pages ?? 0;
  const paid = doc.status === "PAID" && doc.editable;
  const missing = doc.has_cover && cover ? coverIncomplete(cover) : [];

  const panelBody = (
    <>
      {panel === "style" && <DocStylePanel style={doc.style} options={doc.options} onStyle={(style) => change({ style })} onOptions={(options) => change({ options })} />}
      {panel === "cover" && (
        <CoverEditor
          docId={doc.id}
          meta={doc.meta}
          enabled={doc.options.cover && doc.has_cover}
          onEnabled={(on) => {
            if (on) {
              change({ options: { ...doc.options, cover: true } });
              if (cover) coverSvgPreview(cover).then((svg) => change({ cover_svg: svg }));
              setDoc((d) => (d ? { ...d, has_cover: true } : d));
            } else {
              change({ options: { ...doc.options, cover: false }, remove_cover: true });
              setDoc((d) => (d ? { ...d, has_cover: false } : d));
            }
          }}
          onSvg={(svg) => change({ cover_svg: svg })}
          onState={setCover}
        />
      )}
      {panel === "plan" && <PlanPanel docId={doc.id} blocks={doc.blocks} onChange={(blocks) => change({ blocks })} />}
    </>
  );

  const downloadButton = (
    <button
      type="button"
      onClick={() => setPayOpen(true)}
      disabled={rendering}
      className="w-full rounded-2xl bg-brand-500 px-5 py-3.5 text-white shadow-lg shadow-brand-500/25 transition hover:bg-brand-600 active:scale-[.98] disabled:opacity-60"
    >
      <span className="block font-display text-lg leading-tight font-bold">{paid ? "Télécharger à nouveau" : "Télécharger mon document"}</span>
      <span className="block text-xs text-white/80">Word + PDF · sans filigrane</span>
    </button>
  );

  return (
    <Shell right={<span className="hidden text-sm font-semibold text-slate-500 sm:inline">{KIND_LABEL[doc.meta.kind] ?? "Document"} · {pages} pages</span>}>
      <div className="mx-auto grid w-full max-w-7xl flex-1 grid-cols-[minmax(0,1fr)] lg:grid-cols-[400px_minmax(0,1fr)] lg:gap-8 lg:px-5">
        {/* Desktop sidebar: panels stay beside the document, never on top of it */}
        <aside className="hidden lg:block">
          <div className="sticky top-14 flex h-[calc(100dvh-3.5rem)] flex-col pt-5">
            <Tabs panel={panel} onPanel={setPanel} />
            <div className="mt-4 flex-1 overflow-y-auto pr-1 pb-4">{panelBody}</div>
            <div className="space-y-2 border-t border-slate-100 pt-3 pb-4">
              {downloadButton}
              <DangerRow confirm={confirmDelete} onAsk={() => setConfirmDelete(true)} onCancel={() => setConfirmDelete(false)} onDelete={remove} onNew={reset} />
            </div>
          </div>
        </aside>

        {/* Pages */}
        <section className={`relative min-w-0 px-4 pt-4 lg:px-0 lg:pt-5 ${drawer ? "pb-[50dvh]" : "pb-44"} lg:pb-16`}>
          <ChangesCard doc={doc} />
          <div className="sticky top-14 z-20 -mx-4 mt-4 bg-[#f7faf9]/95 px-4 py-2 backdrop-blur lg:mx-0 lg:px-0">
            <div className="mx-auto flex max-w-[620px] items-center gap-3">
              <div className="flex-1">
                <Segmented
                  value={view}
                  onChange={showView}
                  options={[
                    { value: "after", label: "✨ Après" },
                    { value: "before", label: "Avant" },
                    ...(typeof window !== "undefined" && window.innerWidth >= 1024 ? [{ value: "side" as View, label: "Côte à côte" }] : []),
                  ]}
                />
              </div>
              <span className={`shrink-0 rounded-full bg-ink px-3 py-1.5 text-xs font-bold text-white transition ${rendering ? "opacity-100" : "opacity-0"}`}>⏳ Mise à jour…</span>
            </div>
          </div>
          {error && <p className="mx-auto mt-3 max-w-[620px] rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
          <Pages doc={doc} view={view} beforePages={beforePages} dim={rendering} />
        </section>
      </div>

      {/* Mobile: toolbar + half-height drawer (no dark overlay: the document stays visible) */}
      <div className="fixed inset-x-0 bottom-0 z-40 lg:hidden">
        {drawer && (
          <div className="sheet-in flex h-[46dvh] flex-col rounded-t-[28px] border-t border-slate-200 bg-[#f7faf9] shadow-[0_-12px_40px_-12px_rgba(15,23,42,.25)]">
            <div className="flex items-center justify-between px-4 pt-3 pb-2">
              <Tabs panel={panel} onPanel={setPanel} compact />
              <button type="button" onClick={() => setDrawer(false)} className="ml-2 grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white text-slate-500 ring-1 ring-slate-200" aria-label="Fermer">✕</button>
            </div>
            <div className="flex-1 overflow-y-auto px-4 pb-4">{panelBody}</div>
          </div>
        )}
        <div className="border-t border-slate-100 bg-white/95 px-3 pt-2.5 pb-[max(.75rem,env(safe-area-inset-bottom))] backdrop-blur">
          {!drawer && (
            <div className="mb-2.5 grid grid-cols-3 gap-2">
              {PANELS.map((p) => (
                <button key={p.id} type="button" onClick={() => { setPanel(p.id); setDrawer(true); }} className="flex items-center justify-center gap-1.5 rounded-2xl bg-slate-100 py-2.5 text-sm font-bold text-slate-700 active:scale-[.97]">
                  {p.icon} {p.label}
                </button>
              ))}
            </div>
          )}
          {downloadButton}
        </div>
      </div>

      {payOpen && (
        <PaySheet
          orderId={doc.id}
          amount={doc.amount}
          status={doc.status}
          heading="Ton document est prêt ✨"
          bullets={[
            `${pages} pages mises en forme`,
            [doc.has_cover && "page de garde", doc.options.toc && "sommaire", doc.options.toc_end && "table des matières", doc.options.page_numbers && "pagination"].filter(Boolean).join(" · ") || "mise en page complète",
            "Word modifiable + PDF prêt à imprimer",
            "Modifications gratuites pendant 7 jours",
          ]}
          formats={["pdf", "docx"]}
          sharePath={`/document?doc=${doc.id}`}
          missing={missing}
          onStatus={onStatus}
          onClose={() => setPayOpen(false)}
        />
      )}
    </Shell>
  );
}

function Tabs({ panel, onPanel, compact = false }: { panel: Panel; onPanel: (p: Panel) => void; compact?: boolean }) {
  return (
    <div className={`grid shrink-0 grid-cols-3 rounded-2xl bg-slate-200/70 p-1 ${compact ? "flex-1" : "w-full"}`}>
      {PANELS.map((p) => (
        <button
          key={p.id}
          type="button"
          onClick={() => onPanel(p.id)}
          className={`rounded-xl py-2 text-sm font-bold transition ${panel === p.id ? "bg-white text-ink shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
        >
          {p.icon} {p.id === "cover" && !compact ? "Page de garde" : p.label}
        </button>
      ))}
    </div>
  );
}

function Pages({ doc, view, beforePages, dim }: { doc: DocView; view: View; beforePages: number | null; dim: boolean }) {
  const pages = doc.render?.pages ?? 0;
  const after = (i: number) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={docs.pageUrl(doc.id, i + 1, doc.render!.version)} alt={`Page ${i + 1}`} loading={i < 3 ? "eager" : "lazy"} className="aspect-[210/297] w-full rounded-[4px] bg-white shadow-[0_1px_2px_rgba(15,23,42,.06),0_12px_32px_-12px_rgba(15,23,42,.25)]" />
  );
  const before = (i: number) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={docs.beforeUrl(doc.id, i + 1)} alt={`Original page ${i + 1}`} loading="lazy" className="w-full rounded-[4px] bg-white opacity-95 shadow-[0_1px_2px_rgba(15,23,42,.06),0_12px_32px_-12px_rgba(15,23,42,.2)] grayscale-[35%]" />
  );
  const loadingBefore = view !== "after" && (beforePages === null || beforePages === 0);
  if (loadingBefore) return <p className="mt-10 text-center text-sm text-slate-500">Préparation de l&apos;original…</p>;
  if (view !== "after" && beforePages === -1) return <p className="mt-10 text-center text-sm text-slate-500">L&apos;original n&apos;est pas disponible pour ce document.</p>;

  if (view === "side") {
    const n = Math.max(pages, beforePages ?? 0);
    return (
      <div className={`mt-2 grid grid-cols-2 gap-5 transition ${dim ? "opacity-60" : ""}`}>
        <p className="text-center text-xs font-bold tracking-wide text-slate-400 uppercase">Ton original</p>
        <p className="text-center text-xs font-bold tracking-wide text-brand-600 uppercase">Avec Paginya ✨</p>
        {Array.from({ length: n }, (_, i) => (
          <div key={i} className="contents">
            <div>{i < (beforePages ?? 0) && before(i)}</div>
            <div>{i < pages && after(i)}</div>
          </div>
        ))}
      </div>
    );
  }
  const n = view === "after" ? pages : beforePages ?? 0;
  return (
    <div className={`mx-auto mt-2 grid max-w-[620px] gap-5 transition ${dim ? "opacity-60" : ""}`}>
      {view === "before" && (
        <p className="rounded-2xl bg-amber-50 px-4 py-2.5 text-center text-sm text-amber-800 ring-1 ring-amber-100">Voici ton document tel que tu l&apos;as envoyé.</p>
      )}
      {Array.from({ length: n }, (_, i) => (
        <figure key={i}>
          {view === "after" ? after(i) : before(i)}
          <figcaption className="mt-1.5 text-center text-xs text-slate-400">{i + 1} / {n}</figcaption>
        </figure>
      ))}
    </div>
  );
}

function ChangesCard({ doc }: { doc: DocView }) {
  const [open, setOpen] = useState(false);
  const changes = [
    ...(doc.meta.changes ?? []),
    doc.has_cover && "Page de garde ajoutée avec en-tête bilingue",
    doc.options.toc && "Sommaire automatique avec numéros de page",
    doc.options.page_numbers && "Pagination i, ii… puis 1, 2, 3",
  ].filter(Boolean) as string[];
  const shown = open ? changes : changes.slice(0, 3);
  return (
    <div className="mx-auto max-w-[620px] rounded-3xl bg-gradient-to-br from-brand-500 to-emerald-600 p-4 text-white shadow-lg shadow-brand-500/20">
      <p className="text-xs font-bold tracking-wide text-white/75 uppercase">{KIND_LABEL[doc.meta.kind] ?? "Document"} · {doc.render?.pages ?? "…"} pages</p>
      <p className="mt-0.5 font-display text-lg font-bold">Ce que Paginya a fait ✨</p>
      <ul className="mt-2.5 space-y-1.5">
        {shown.map((c) => (
          <li key={c} className="flex gap-2 text-[14px] leading-snug">
            <span className="mt-0.5 grid h-4.5 w-4.5 shrink-0 place-items-center rounded-full bg-white/25 text-[10px] font-bold">✓</span>
            {c}
          </li>
        ))}
      </ul>
      {changes.length > 3 && (
        <button type="button" onClick={() => setOpen(!open)} className="mt-2 text-sm font-bold text-white/90 underline underline-offset-2">
          {open ? "Voir moins" : `+ ${changes.length - 3} autres améliorations`}
        </button>
      )}
    </div>
  );
}

function DangerRow({ confirm, onAsk, onCancel, onDelete, onNew }: { confirm: boolean; onAsk: () => void; onCancel: () => void; onDelete: () => void; onNew: () => void }) {
  if (confirm) {
    return (
      <div className="flex items-center justify-between gap-2 rounded-2xl bg-red-50 px-3 py-2 text-sm">
        <span className="text-red-700">Supprimer définitivement ?</span>
        <span className="flex gap-2">
          <button type="button" onClick={onCancel} className="font-semibold text-slate-600">Non</button>
          <button type="button" onClick={onDelete} className="rounded-lg bg-red-600 px-3 py-1 font-bold text-white">Oui, supprimer</button>
        </span>
      </div>
    );
  }
  return (
    <div className="flex justify-between text-sm font-semibold text-slate-500">
      <button type="button" onClick={onNew} className="hover:text-slate-700">↺ Nouveau document</button>
      <button type="button" onClick={onAsk} className="hover:text-red-600">🗑 Supprimer</button>
    </div>
  );
}

function Shell({ children, right }: { children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-30 border-b border-slate-100 bg-white/85 pt-[env(safe-area-inset-top)] backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <Link href="/" className="grid h-9 w-9 place-items-center rounded-full text-xl text-slate-600 hover:bg-slate-100" aria-label="Accueil">←</Link>
            <Logo />
          </div>
          {right}
        </div>
      </header>
      {children}
    </div>
  );
}
