"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import type { OrderStatus } from "@/lib/api";
import { KIND_LABEL, docs, type Block, type DocOptions, type DocStyle, type DocView, type Letterhead } from "@/lib/documents";
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
type Patch = Partial<{ blocks: Block[]; style: DocStyle; options: DocOptions; kind: string; letterhead: Letterhead; cover_svg: string; remove_cover: boolean }>;

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
      {panel === "style" && <DocStylePanel style={doc.style} options={doc.options} kind={doc.meta.kind} onStyle={(style) => change({ style })} onOptions={(options) => change({ options })} onKind={(kind) => { setDoc((d) => (d ? { ...d, meta: { ...d.meta, kind } } : d)); change({ kind }); }} letterhead={doc.letterhead ?? null} hasCover={doc.has_cover} onLetterhead={(letterhead, options) => change({ letterhead, options })} />}
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

  const title = `${KIND_LABEL[doc.meta.kind] ?? "Document"} · ${pages} page${pages > 1 ? "s" : ""}`;
  const views = [
    { value: "after" as View, label: "✨ Après" },
    { value: "before" as View, label: "Avant" },
    ...(typeof window !== "undefined" && window.innerWidth >= 1024 ? [{ value: "side" as View, label: "Côte à côte" }] : []),
  ];
  const download = (
    <button
      type="button"
      onClick={() => setPayOpen(true)}
      disabled={rendering}
      className="shrink-0 rounded-xl bg-brand-500 px-4 py-2.5 font-display text-[15px] font-bold text-white shadow-md shadow-brand-500/25 transition hover:bg-brand-600 active:scale-[.98] disabled:opacity-60"
    >
      ⬇ {paid ? "Retélécharger" : "Télécharger"}
    </button>
  );

  return (
    <div className="flex h-dvh flex-col bg-[#eef1f4]">
      {/* Top bar (Google Docs / Canva): title · before/after · corrections · download */}
      <header className="z-30 shrink-0 border-b border-slate-200/80 bg-white pt-[env(safe-area-inset-top)]">
        <div className="flex h-14 items-center gap-2 px-2 sm:px-4">
          <Link href="/" className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-xl text-slate-600 hover:bg-slate-100" aria-label="Accueil">←</Link>
          <div className="hidden sm:block"><Logo /></div>
          <span className="ml-1 min-w-0 truncate text-sm font-semibold text-slate-600 sm:ml-3">{title}</span>
          <div className="ml-auto flex items-center gap-2">
            <span className={`hidden rounded-full bg-slate-100 px-3 py-1.5 text-xs font-bold text-slate-600 transition sm:inline ${rendering ? "opacity-100" : "opacity-0"}`}>⏳ Mise à jour…</span>
            <ChangesPill doc={doc} />
            <div className="hidden w-[300px] lg:block"><Segmented value={view} onChange={showView} options={views} /></div>
            <div className="hidden lg:block">{download}</div>
          </div>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* Desktop: tool rail + its panel */}
        <nav className="hidden w-[76px] shrink-0 flex-col items-center gap-1 border-r border-slate-200/80 bg-white py-3 lg:flex">
          {PANELS.map((p) => (
            <button key={p.id} type="button" onClick={() => setPanel(p.id)} className={`flex w-[64px] flex-col items-center gap-1 rounded-2xl py-2.5 text-[11px] font-bold transition ${panel === p.id ? "bg-brand-500/10 text-brand-700" : "text-slate-500 hover:bg-slate-50"}`}>
              <span className="text-xl leading-none">{p.icon}</span>
              {p.id === "cover" ? "Garde" : p.label}
            </button>
          ))}
          <div className="mt-auto w-full px-2"><MoreMenu onNew={reset} onDelete={remove} /></div>
        </nav>
        <aside className="hidden w-[340px] shrink-0 flex-col border-r border-slate-200/80 bg-white lg:flex">
          <p className="px-5 pt-5 font-display text-lg font-bold text-ink">{PANELS.find((p) => p.id === panel)?.icon} {panel === "cover" ? "Page de garde" : PANELS.find((p) => p.id === panel)?.label}</p>
          <div className="min-h-0 flex-1 overflow-y-auto px-5 pt-3 pb-6">{panelBody}</div>
        </aside>

        {/* The document, on its grey desk */}
        <main className={`min-w-0 flex-1 overflow-y-auto ${drawer ? "pb-[50dvh]" : "pb-28"} lg:pb-12`}>
          <div className="sticky top-0 z-20 bg-[#eef1f4]/90 px-3 pt-3 pb-2 backdrop-blur lg:hidden">
            <Segmented value={view} onChange={showView} options={views} />
          </div>
          {error && <p className="mx-auto mt-3 max-w-[720px] rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
          <div className="px-3 pt-2 sm:px-6 lg:pt-8">
            <Pages doc={doc} view={view} beforePages={beforePages} dim={rendering} />
          </div>
        </main>
      </div>

      {/* Mobile: one bottom row (tools + download) and a half-height drawer that leaves the page visible */}
      <div className="fixed inset-x-0 bottom-0 z-40 lg:hidden">
        {drawer && (
          <div className="sheet-in flex h-[46dvh] flex-col rounded-t-[28px] border-t border-slate-200 bg-white shadow-[0_-12px_40px_-12px_rgba(15,23,42,.25)]">
            <div className="flex items-center justify-between px-4 pt-3 pb-2">
              <Tabs panel={panel} onPanel={setPanel} compact />
              <button type="button" onClick={() => setDrawer(false)} className="ml-2 grid h-9 w-9 shrink-0 place-items-center rounded-full bg-slate-100 text-slate-500" aria-label="Fermer">✕</button>
            </div>
            <div className="flex-1 overflow-y-auto px-4 pb-4">{panelBody}</div>
          </div>
        )}
        <div className="flex items-center gap-1.5 border-t border-slate-200 bg-white px-2 pt-2 pb-[max(.6rem,env(safe-area-inset-bottom))]">
          {PANELS.map((p) => (
            <button key={p.id} type="button" onClick={() => { setPanel(p.id); setDrawer(!(drawer && panel === p.id)); }} className={`flex w-[62px] shrink-0 flex-col items-center rounded-xl py-1.5 text-[11px] font-bold ${drawer && panel === p.id ? "bg-brand-500/10 text-brand-700" : "text-slate-600"}`}>
              <span className="text-lg leading-6">{p.icon}</span>{p.label}
            </button>
          ))}
          <div className="ml-auto flex-1 [&>button]:w-full [&>button]:py-3">{download}</div>
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
    </div>
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
    <div className={`mx-auto mt-2 grid max-w-[760px] gap-6 transition ${dim ? "opacity-60" : ""}`}>
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

/** "✨ 13 corrections" (Grammarly-style): small in the top bar, the full list on tap. */
function ChangesPill({ doc }: { doc: DocView }) {
  const [open, setOpen] = useState(false);
  const changes = doc.meta.changes ?? [];
  if (!changes.length) return null;
  return (
    <div className="relative">
      <button type="button" onClick={() => setOpen(!open)} className="rounded-full bg-brand-500/10 px-3 py-2 text-xs font-bold text-brand-700 hover:bg-brand-500/15 sm:text-sm">
        ✨ {changes.length} correction{changes.length > 1 ? "s" : ""}
      </button>
      {open && (
        <>
          <button type="button" aria-label="Fermer" className="fixed inset-0 z-40 cursor-default" onClick={() => setOpen(false)} />
          <div className="rise fixed inset-x-3 top-16 z-50 max-h-[70dvh] overflow-y-auto rounded-3xl bg-white p-5 shadow-2xl ring-1 ring-slate-100 sm:absolute sm:inset-x-auto sm:top-12 sm:right-0 sm:w-[380px]">
            <p className="font-display text-lg font-bold text-ink">Ce que Paginya a corrigé ✨</p>
            <ul className="mt-3 space-y-2">
              {changes.map((c) => (
                <li key={c} className="flex gap-2.5 text-[14px] leading-snug text-slate-700">
                  <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-brand-500 text-[11px] font-bold text-white">✓</span>
                  {c}
                </li>
              ))}
            </ul>
            <p className="mt-4 text-xs text-slate-500">Compare avec « Avant » pour voir ton document d&apos;origine.</p>
          </div>
        </>
      )}
    </div>
  );
}

function MoreMenu({ onNew, onDelete }: { onNew: () => void; onDelete: () => void }) {
  const [open, setOpen] = useState(false);
  const [confirm, setConfirm] = useState(false);
  return (
    <div className="relative">
      <button type="button" onClick={() => setOpen(!open)} className="w-full rounded-2xl py-2.5 text-center text-lg text-slate-500 hover:bg-slate-50" aria-label="Plus">⋯</button>
      {open && (
        <div className="absolute bottom-12 left-0 z-50 w-56 rounded-2xl bg-white p-2 text-sm shadow-xl ring-1 ring-slate-100">
          <button type="button" onClick={onNew} className="block w-full rounded-xl px-3 py-2 text-left font-semibold text-slate-700 hover:bg-slate-50">↺ Nouveau document</button>
          {confirm ? (
            <button type="button" onClick={onDelete} className="block w-full rounded-xl bg-red-600 px-3 py-2 text-left font-bold text-white">Oui, supprimer définitivement</button>
          ) : (
            <button type="button" onClick={() => setConfirm(true)} className="block w-full rounded-xl px-3 py-2 text-left font-semibold text-red-600 hover:bg-red-50">🗑 Supprimer ce document</button>
          )}
        </div>
      )}
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
