"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import type { OrderStatus } from "@/lib/api";
import { forget, remember } from "@/lib/recents";
import { KIND_LABEL, docs, type Block, type DocOptions, type DocStyle, type DocView, type Letterhead } from "@/lib/documents";
import { saveExamDraft } from "@/lib/examDraft";
import { Icon, type IconName } from "../Icon";
import { Logo } from "../Logo";
import { PaySheet } from "../PaySheet";
import type { StudioState } from "../studio/state";
import { Segmented } from "../ui";
import { CoverView } from "../CoverView";
import { CoverEditor, coverIncomplete, coverSvgPreview, prepareCover } from "./CoverEditor";
import { DocStylePanel } from "./DocStylePanel";
import { ImportScreen } from "./ImportScreen";
import { PlanPanel } from "./PlanPanel";
import { Working } from "./Working";

type Panel = "style" | "cover" | "plan";
type View = "after" | "before" | "side";
type Patch = Partial<{ blocks: Block[]; style: DocStyle; options: DocOptions; kind: string; letterhead: Letterhead; cover_svg: string; remove_cover: boolean }>;

const PANELS: { id: Panel; icon: IconName; label: string; title: string }[] = [
  { id: "style", icon: "palette", label: "Style", title: "Style et type" },
  { id: "cover", icon: "landmark", label: "Garde", title: "Page de garde" },
  { id: "plan", icon: "list-tree", label: "Plan", title: "Plan du document" },
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
  const [liveCover, setLiveCover] = useState(""); // page 1 drawn in the browser while the cover is edited
  const [zoom, setZoom] = useState(false);
  const pending = useRef<Patch>({});
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const chain = useRef<Promise<unknown>>(Promise.resolve());

  const openDoc = useCallback(async (view: DocView, fromStudio = false) => {
    setDoc(view);
    router.replace(`/document?doc=${view.id}`, { scroll: false });
    let current = view;
    const needsCover = view.options.cover && (!view.has_cover || fromStudio);
    if (needsCover) {
      if (fromStudio) {
        try { localStorage.removeItem(`propre:doc:cover:${view.id}`); } catch { /* ignore */ }
      }
      current = await docs.update(view.id, { cover_svg: await coverSvgPreview(await prepareCover(view.id, view.meta)) });
    }
    if (!current.render || needsCover) {
      setRendering(true);
      current = await docs.render(view.id);
      setRendering(false);
    }
    setCover(await prepareCover(view.id, view.meta));
    remember({ id: current.id, title: current.meta.cover?.title || current.meta.title || "", kind: current.meta.kind, pages: current.render?.pages ?? 0 });
    setDoc(current);
    setPhase("editor");
  }, [router]);

  useEffect(() => {
    // Only a link opens a document: coming back to /document starts a new one (older ones are in "Reprendre").
    const id = params.get("doc");
    const fromStudio = params.get("cover") === "1";
    if (!id) return;
    let cancelled = false;
    docs.get(id)
      .then((v) => { if (!cancelled) { setPhase("working"); return openDoc(v, fromStudio); } })
      .catch(() => {
        forget(id);
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
        const saved = await docs.update(id, patch);
        if (Object.keys(pending.current).length) return; // a newer edit will render
        // Only the cover changed: page 1 is already drawn here, the full layout waits for the download.
        const coverOnly = Object.keys(patch).every((k) => k === "cover_svg");
        setDoc(coverOnly && saved.render ? saved : await docs.render(id));
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setRendering(false);
      }
    });
  }

  /** "Épreuve" in the type list: the text goes to the exam form, which lays it out the Cameroonian way. */
  async function openAsExam() {
    if (!doc) return;
    setError("");
    try {
      const exam = await docs.toExam(doc.id);
      if (saveExamDraft(exam.fields, exam.content)) router.push("/epreuve");
      else setError("Impossible d'ouvrir l'épreuve : ton navigateur bloque le stockage local (navigation privée ?).");
    } catch (e) {
      setError((e as Error).message);
    }
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
    router.replace("/document");
    setDoc(null);
    setBeforePages(null);
    setView("after");
    setPhase("import");
  }

  async function remove() {
    if (!doc) return;
    await docs.remove(doc.id).catch(() => null);
    forget(doc.id);
    reset();
  }

  if (phase === "import" || !doc) {
    return (
      <Shell>
        {phase === "working" ? <Working meta={null} rendering={false} /> : (
          <ImportScreen error={error} onText={(t) => start(() => docs.fromText(t))} onFile={(f) => start(() => docs.fromFile(f))} onOpen={(id) => start(() => docs.get(id))} />
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
      {panel === "style" && <DocStylePanel style={doc.style} options={doc.options} kind={doc.meta.kind} onStyle={(style) => change({ style })} onOptions={(options) => change({ options })} onKind={(kind) => { if (kind === "epreuve") { openAsExam(); return; } setDoc((d) => (d ? { ...d, meta: { ...d.meta, kind } } : d)); change({ kind }); }} letterhead={doc.letterhead ?? null} hasCover={doc.has_cover} onLetterhead={(letterhead, options) => change({ letterhead, options })} />}
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
          onPreview={setLiveCover}
          onState={setCover}
        />
      )}
      {panel === "plan" && <PlanPanel docId={doc.id} blocks={doc.blocks} onChange={(blocks) => change({ blocks })} />}
    </>
  );

  const title = `${KIND_LABEL[doc.meta.kind] ?? "Document"} · ${pages} page${pages > 1 ? "s" : ""}`;
  const views = [
    { value: "after" as View, label: "Après" },
    { value: "before" as View, label: "Avant" },
    ...(typeof window !== "undefined" && window.innerWidth >= 1024 ? [{ value: "side" as View, label: "Côte à côte" }] : []),
  ];
  const download = (
    <button
      type="button"
      onClick={() => setPayOpen(true)}
      disabled={rendering}
      className="press inline-flex shrink-0 items-center justify-center gap-2 rounded-md bg-hi px-4 py-2.5 font-display text-[20px] leading-none font-black tracking-wide text-ink uppercase shadow-[0_2px_0_0_var(--color-hi-deep)] hover:bg-[#ffe04a] disabled:opacity-60"
    >
      <Icon name="download" size={18} stroke={2.5} />
      {paid ? "Retélécharger" : "Télécharger"}
    </button>
  );

  return (
    <div className="board flex h-dvh flex-col">
      {/* Top bar: back · title · status stamp · corrections · view · download */}
      <header className="z-30 shrink-0 border-b border-black/25 bg-board/95 pt-[env(safe-area-inset-top)]">
        <div className="flex h-14 items-center gap-2 px-2 sm:px-4">
          <Link href="/" className="press grid h-10 w-10 shrink-0 place-items-center rounded-md text-white/80 hover:bg-white/10 hover:text-white" aria-label="Accueil">
            <Icon name="arrow-left" />
          </Link>
          <div className="hidden sm:block"><Logo tone="board" /></div>
          <span className="ml-1 min-w-0 truncate text-[15px] font-semibold text-white/80 sm:ml-4">{title}</span>
          <div className="ml-auto flex items-center gap-2">
            {rendering && <span className="stamp stamp-in hidden bg-paper/90 text-[15px] sm:inline-flex">En cours</span>}
            <ChangesPill doc={doc} />
            <button type="button" onClick={() => setZoom(!zoom)} aria-pressed={zoom} className="press hidden h-10 items-center gap-1.5 rounded-md px-3 text-[14px] font-bold text-white/80 ring-1 ring-white/20 hover:bg-white/10 hover:text-white lg:inline-flex" title="Agrandir les pages pour mieux lire">
              <Icon name={zoom ? "zoom-out" : "zoom-in"} size={18} />{zoom ? "Réduire" : "Agrandir"}
            </button>
            <div className="hidden w-[300px] lg:block"><BoardSegmented value={view} onChange={showView} options={views} /></div>
            <div className="hidden lg:block">{download}</div>
          </div>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* Desktop: tool rail + its panel, on a sheet of paper */}
        <nav className="hidden w-[78px] shrink-0 flex-col items-center gap-1 border-r border-black/10 bg-paper py-3 text-ink lg:flex">
          {PANELS.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setPanel(p.id)}
              className={`press flex w-[64px] flex-col items-center gap-1 rounded-md py-2.5 text-[12px] font-bold transition-colors ${panel === p.id ? "bg-board text-white" : "text-ink/60 hover:bg-ink/5 hover:text-ink"}`}
            >
              <Icon name={p.icon} size={21} />
              {p.label}
            </button>
          ))}
          <div className="mt-auto w-full px-2"><MoreMenu onNew={reset} onDelete={remove} /></div>
        </nav>
        <aside className="hidden w-[350px] shrink-0 flex-col border-r border-black/10 bg-paper text-ink lg:flex">
          <p className="px-5 pt-6 font-display text-[26px] leading-none font-black uppercase">{PANELS.find((p) => p.id === panel)?.title}</p>
          <div key={panel} className="panel-in min-h-0 flex-1 overflow-y-auto px-5 pt-4 pb-6">{panelBody}</div>
        </aside>

        {/* The document, pinned on the board */}
        <main className={`min-w-0 flex-1 overflow-y-auto ${drawer ? "pb-[50dvh]" : "pb-28"} lg:pb-12`}>
          <div className="sticky top-0 z-20 bg-board/90 px-3 pt-3 pb-2 backdrop-blur lg:hidden">
            <BoardSegmented value={view} onChange={showView} options={views} />
          </div>
          {error && <p className="mx-auto mt-3 flex max-w-[720px] gap-2 rounded-md bg-paper px-4 py-3 text-[15px] text-pin"><Icon name="triangle-alert" size={18} className="mt-0.5" />{error}</p>}
          <div className="px-4 pt-3 sm:px-8 lg:pt-10">
            <Pages doc={doc} view={view} beforePages={beforePages} dim={rendering} cover={doc.has_cover && doc.options.cover ? liveCover : ""} zoom={zoom} />
          </div>
        </main>
      </div>

      {/* Mobile: one bottom row (tools + download) and a half-height drawer that leaves the page visible */}
      <div className="fixed inset-x-0 bottom-0 z-40 lg:hidden">
        {drawer && (
          <div className="sheet-in paper relative flex h-[48dvh] flex-col rounded-t-xl">
            <span className="pin top-2 left-1/2 -translate-x-1/2" aria-hidden />
            <div className="flex items-center justify-between px-4 pt-6 pb-2">
              <Tabs panel={panel} onPanel={setPanel} compact />
              <button type="button" onClick={() => setDrawer(false)} className="press ml-2 grid h-10 w-10 shrink-0 place-items-center rounded-md text-ink/60 ring-1 ring-black/10" aria-label="Fermer">
                <Icon name="x" size={18} />
              </button>
            </div>
            <div key={panel} className="panel-in flex-1 overflow-y-auto px-4 pb-4">{panelBody}</div>
          </div>
        )}
        <div className="flex items-center gap-1.5 border-t border-black/10 bg-paper px-2 pt-2 text-ink pb-[max(.6rem,env(safe-area-inset-bottom))]">
          {PANELS.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => { setPanel(p.id); setDrawer(!(drawer && panel === p.id)); }}
              className={`press flex w-[62px] shrink-0 flex-col items-center gap-0.5 rounded-md py-1.5 text-[12px] font-bold ${drawer && panel === p.id ? "bg-board text-white" : "text-ink/70"}`}
            >
              <Icon name={p.icon} size={20} />
              {p.label}
            </button>
          ))}
          <div className="ml-auto flex-1 [&>button]:w-full [&>button]:py-3.5">{download}</div>
        </div>
      </div>

      {payOpen && (
        <PaySheet
          orderId={doc.id}
          amount={doc.amount}
          status={doc.status}
          heading="Ton document est prêt"
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

/** Before / after switch drawn for the board (light chips on green). */
function BoardSegmented<T extends string>({ value, options, onChange }: { value: T; options: { value: T; label: string }[]; onChange: (v: T) => void }) {
  return (
    <div className="grid rounded-md bg-black/25 p-1" style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={`press rounded px-2 py-2 text-[14px] font-bold transition-colors ${value === o.value ? "bg-paper text-ink" : "text-white/70 hover:text-white"}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function Tabs({ panel, onPanel, compact = false }: { panel: Panel; onPanel: (p: Panel) => void; compact?: boolean }) {
  return (
    <div className={compact ? "flex-1" : "w-full"}>
      <Segmented value={panel} onChange={onPanel} options={PANELS.map((p) => ({ value: p.id, label: compact ? p.label : p.title }))} />
    </div>
  );
}

function Pages({ doc, view, beforePages, dim, cover, zoom }: { doc: DocView; view: View; beforePages: number | null; dim: boolean; cover: string; zoom: boolean }) {
  const pages = doc.render?.pages ?? 0;
  const sheet = (img: React.ReactNode, i: number, faded = false) => (
    <div className={`paper pin-in relative rounded-[2px] p-0 ${faded ? "opacity-95" : ""}`} style={{ animationDelay: `${Math.min(i, 4) * 70}ms` }}>
      <span className="pin top-2 left-1/2 z-10 -translate-x-1/2" aria-hidden />
      {img}
    </div>
  );
  const after = (i: number) =>
    sheet(
      i === 0 && cover ? (
        <CoverView svg={cover} watermark={doc.status !== "PAID"} />
      ) : (
        <PageImage key={`${doc.render!.version}-${i}`} src={docs.pageUrl(doc.id, i + 1, doc.render!.version)} alt={`Page ${i + 1}`} eager={i < 3} />
      ),
      i,
    );
  const before = (i: number) =>
    sheet(
      // eslint-disable-next-line @next/next/no-img-element
      <img src={docs.beforeUrl(doc.id, i + 1)} alt={`Original page ${i + 1}`} loading="lazy" className="w-full bg-white grayscale-[35%]" />,
      i,
      true,
    );
  const loadingBefore = view !== "after" && (beforePages === null || beforePages === 0);
  if (loadingBefore) return <p className="mt-10 flex items-center justify-center gap-2 text-[15px] text-white/70"><Icon name="loader-circle" size={18} className="animate-spin" />Préparation de l&apos;original…</p>;
  if (view !== "after" && beforePages === -1) return <p className="mt-10 text-center text-[15px] text-white/70">L&apos;original n&apos;est pas disponible pour ce document.</p>;

  if (view === "side") {
    const n = Math.max(pages, beforePages ?? 0);
    return (
      <div className={`mt-2 grid grid-cols-2 gap-6 transition-opacity ${dim ? "opacity-60" : ""}`}>
        <p className="text-center text-[13px] font-bold tracking-widest text-white/55 uppercase">Ton original</p>
        <p className="text-center text-[13px] font-bold tracking-widest text-hi uppercase">Avec Paginya</p>
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
    <div className={`mx-auto mt-2 grid gap-8 transition-[opacity,max-width] duration-300 ${zoom ? "max-w-[1100px]" : "max-w-[760px]"} ${dim ? "opacity-60" : ""}`}>
      {view === "before" && (
        <p className="rounded-md bg-hi/90 px-4 py-2.5 text-center text-[15px] font-semibold text-ink">Voici ton document tel que tu l&apos;as envoyé.</p>
      )}
      {Array.from({ length: n }, (_, i) => (
        <figure key={i}>
          {view === "after" ? after(i) : before(i)}
          <figcaption className="mt-2 text-center text-[13px] font-semibold text-white/55 tabular">{i + 1} / {n}</figcaption>
        </figure>
      ))}
    </div>
  );
}

/** A page fades in when its (new) image has arrived, instead of popping in half-drawn. */
function PageImage({ src, alt, eager }: { src: string; alt: string; eager: boolean }) {
  const [loaded, setLoaded] = useState(false);
  return (
    <div className="relative aspect-[210/297] w-full overflow-hidden bg-white">
      {!loaded && <div className="absolute inset-0 animate-pulse bg-[repeating-linear-gradient(180deg,#fff_0_22px,#f1f2ee_22px_30px)] [background-position:0_60px] opacity-60" />}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={alt} loading={eager ? "eager" : "lazy"} onLoad={() => setLoaded(true)} className={`page-img h-full w-full ${loaded ? "is-loaded" : ""}`} />
    </div>
  );
}

/** "12 corrections": small in the top bar, the full list on tap. */
function ChangesPill({ doc }: { doc: DocView }) {
  const [open, setOpen] = useState(false);
  const changes = doc.meta.changes ?? [];
  if (!changes.length) return null;
  return (
    <div className="relative">
      <button type="button" onClick={() => setOpen(!open)} className="press inline-flex items-center gap-1.5 rounded-md bg-white/10 px-3 py-2 text-[14px] font-bold text-white ring-1 ring-white/20 hover:bg-white/15">
        <Icon name="check" size={16} stroke={2.6} className="text-hi" />
        <span className="tabular">{changes.length}</span> correction{changes.length > 1 ? "s" : ""}
      </button>
      {open && (
        <>
          <button type="button" aria-label="Fermer" className="fixed inset-0 z-40 cursor-default" onClick={() => setOpen(false)} />
          <div className="rise paper fixed inset-x-3 top-16 z-50 max-h-[70dvh] overflow-y-auto rounded-[2px] p-5 sm:absolute sm:inset-x-auto sm:top-12 sm:right-0 sm:w-[390px]">
            <p className="font-display text-[24px] leading-none font-black uppercase">Ce que Paginya a rangé</p>
            <ul className="mt-4 space-y-2.5">
              {changes.map((c) => (
                <li key={c} className="flex gap-2.5 text-[15px] leading-snug">
                  <Icon name="check" size={18} stroke={2.6} className="mt-0.5 text-board" />
                  {c}
                </li>
              ))}
            </ul>
            <p className="mt-4 text-[13px] text-ink/55">Compare avec « Avant » pour voir ton document d&apos;origine.</p>
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
      <button type="button" onClick={() => setOpen(!open)} className="press grid w-full place-items-center rounded-md py-2.5 text-ink/55 hover:bg-ink/5" aria-label="Plus d'actions">
        <Icon name="ellipsis" size={22} />
      </button>
      {open && (
        <div className="paper absolute bottom-12 left-0 z-50 w-60 rounded-[2px] p-2 text-[15px]">
          <button type="button" onClick={onNew} className="flex w-full items-center gap-2 rounded px-3 py-2.5 text-left font-semibold hover:bg-ink/5">
            <Icon name="rotate-ccw" size={17} /> Nouveau document
          </button>
          {confirm ? (
            <button type="button" onClick={onDelete} className="w-full rounded bg-pin px-3 py-2.5 text-left font-bold text-white">Oui, supprimer définitivement</button>
          ) : (
            <button type="button" onClick={() => setConfirm(true)} className="flex w-full items-center gap-2 rounded px-3 py-2.5 text-left font-semibold text-pin hover:bg-pin/10">
              <Icon name="trash-2" size={17} /> Supprimer ce document
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function Shell({ children, right }: { children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="board sticky top-0 z-30 border-b border-black/25 pt-[env(safe-area-inset-top)]">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-3">
          <div className="flex items-center gap-1">
            <Link href="/" className="press grid h-10 w-10 place-items-center rounded-md text-white/80 hover:bg-white/10 hover:text-white" aria-label="Accueil">
              <Icon name="arrow-left" />
            </Link>
            <Logo tone="board" />
          </div>
          {right}
        </div>
      </header>
      {children}
    </div>
  );
}
