"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { STYLES, loadCoverFonts, renderCover } from "@/lib/cover";
import { KINDS, emptyForm } from "@/lib/cover/kinds";
import { PALETTES } from "@/lib/cover/palettes";
import type { CoverForm, DocKind, Person, StyleId } from "@/lib/cover/types";
import type { DocCoverInfo, DocMeta } from "@/lib/documents";
import { INSTITUTIONS, institution, logoData } from "@/lib/institutions";
import { CoverView } from "../CoverView";
import { Icon } from "../Icon";
import { STORAGE_KEY as STUDIO_KEY, initialState, switchKind, type StudioState } from "../studio/state";
import { DetailsStep, EssentialsStep } from "../studio/Steps";
import { Select, Toggle } from "../ui";

const KIND_FROM_META: Record<string, DocKind> = {
  rapport_stage: "rapport_stage",
  memoire: "memoire",
  rapport: "rapport_projet",
  document: "expose",
};

const coverKey = (docId: string) => `propre:doc:cover:${docId}`;

const plain = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();

function kindOf(meta: DocMeta): DocKind {
  const label = plain(meta.cover?.doc_label ?? "");
  if (label.includes("stage")) return "rapport_stage";
  if (label.includes("memoire") || label.includes("these")) return "memoire";
  if (label.includes("expose")) return "expose";
  if (label.includes("projet")) return "rapport_projet";
  return KIND_FROM_META[meta.kind] ?? "autre";
}

/** The school named on the student's own cover: every line of one of our institutions found in its header. */
function matchInstitution(header: string[]): string | null {
  const text = plain(header.join(" "));
  let best: { id: string; lines: number } | null = null;
  for (const inst of INSTITUTIONS) {
    if (inst.id === "autre" || inst.id === "lycee") continue;
    // "(ESSTIC)", "– SOA": optional on real covers
    const all = inst.fr.every((l) => text.includes(plain(l.replace(/\([^)]*\)/g, "")).replace(/ soa$/, "")));
    if (all && (!best || inst.fr.length > best.lines)) best = { id: inst.id, lines: inst.fr.length };
  }
  return best?.id ?? null;
}

const OFFICIAL = /republique|paix|ministere|republic|peace|ministry/;

/** Cover fields read from the document's own cover page (server side, meta.cover). */
function fromDocument(meta: DocMeta, info: DocCoverInfo): StudioState {
  const kind = kindOf(meta);
  const base = switchKind(initialState(kind), kind);
  const def = KINDS[kind];
  const form: CoverForm = { ...emptyForm(kind), ...base.form };
  const instId = matchInstitution(info.header_fr ?? []);
  if (instId) {
    const inst = institution(instId);
    // the faculty / department read on the old cover stays in the header (our list may stop at the university)
    const known = new Set(inst.fr.map((l) => plain(l)));
    const extra = (lines?: string[]) => (lines ?? []).filter((l) => /^(facult|[ée]cole|school|institut|d[ée]partement|department|fili[èe]re|option)/i.test(l) && !known.has(plain(l)));
    Object.assign(form, {
      institutionId: inst.id,
      headerFr: [...inst.fr, ...extra(info.header_fr)].join("\n"),
      headerEn: [...inst.en, ...extra(info.header_en)].join("\n"),
    });
  } else if (info.header_fr?.length) {
    const own = (lines?: string[]) => (lines ?? []).filter((l) => !OFFICIAL.test(plain(l))).join("\n");
    Object.assign(form, { institutionId: "autre", headerFr: own(info.header_fr), headerEn: own(info.header_en) });
  }
  form.title = info.title || meta.title || "";
  if (info.authors?.length) form.authors = info.authors.map((a, i): Person => ({ name: a.name, info: a.info ?? (i === 0 ? info.matricule ?? "" : "") }));
  if (info.supervisors?.length) {
    form.supervisors = info.supervisors.map((s, i): Person => ({
      name: s.name,
      role: s.role && !/^sous la/i.test(s.role) ? s.role : def.supervisorRoles[i] ?? s.role ?? "Encadreur",
      info: s.info ?? "",
    }));
  }
  for (const k of ["year", "degree", "specialty", "structure", "period"] as const) if (info[k]) form[k] = info[k]!;
  // an official bilingual header on the old cover: keep that look (header, logos in the middle)
  return { ...base, style: info.header_fr?.length && def.academic ? "officiel" : def.defaultStyle, form };
}

/** Cover state for a document: its own saved state, else what its old cover says, else the studio draft. */
export function initialCover(docId: string, meta: DocMeta): StudioState {
  try {
    const own = localStorage.getItem(coverKey(docId));
    if (own) return JSON.parse(own) as StudioState;
  } catch { /* ignore */ }
  if (meta.cover) return fromDocument(meta, meta.cover);
  try {
    const studio = localStorage.getItem(STUDIO_KEY);
    if (studio) {
      const s = JSON.parse(studio) as StudioState;
      return { ...s, form: { ...s.form, title: s.form.title || meta.title || "" } };
    }
  } catch { /* ignore */ }
  const kind = KIND_FROM_META[meta.kind] ?? "autre";
  const base = switchKind(initialState(kind), kind);
  return { ...base, style: KINDS[kind].defaultStyle, form: { ...base.form, institutionId: "autre", headerFr: "", headerEn: "", title: meta.title ?? "" } };
}

/** initialCover + the school's logos (fetched once; the user can change or remove them). */
export async function prepareCover(docId: string, meta: DocMeta): Promise<StudioState> {
  const s = initialCover(docId, meta);
  if (s.form.logo || s.form.logo2 || s.form.institutionId === "autre") return s;
  const inst = institution(s.form.institutionId);
  const [logo, logo2] = await Promise.all([inst.logo ? logoData(inst.logo) : undefined, inst.logo2 ? logoData(inst.logo2) : undefined]);
  return { ...s, form: { ...s.form, logo, logo2 } };
}

const optsOf = (s: StudioState) => ({ palette: PALETTES.find((p) => p.id === s.paletteId) ?? PALETTES[0], mono: s.mono, frame: s.frame });

export async function coverSvg(state: StudioState): Promise<string> {
  await loadCoverFonts();
  return renderCover(state.form, state.style, optsOf(state), false);
}

/** First attach: show the example header so the page looks finished (the user completes it in the panel). */
export async function coverSvgPreview(state: StudioState): Promise<string> {
  await loadCoverFonts();
  return renderCover(state.form, state.style, optsOf(state), true);
}

export function coverIncomplete(state: StudioState): string[] {
  const missing: string[] = [];
  if (!state.form.headerFr.trim()) missing.push("le nom de ton école (page de garde)");
  if (!state.form.title.trim()) missing.push("le titre (page de garde)");
  if (!state.form.authors.some((a) => a.name.trim())) missing.push("ton nom (page de garde)");
  return missing;
}

type Props = {
  docId: string;
  meta: DocMeta;
  enabled: boolean;
  onEnabled: (v: boolean) => void;
  /** Saved to the document (debounced). */
  onSvg: (svg: string) => void;
  /** Instant: page 1 of the preview follows every keystroke. */
  onPreview: (svg: string) => void;
  onState: (s: StudioState) => void;
};

/** The full cover studio, next to the document: every change shows at once on page 1. */
export function CoverEditor({ docId, meta, enabled, onEnabled, onSvg, onPreview, onState }: Props) {
  const [state, setState] = useState<StudioState>(() => initialCover(docId, meta));
  const [fontsReady, setFontsReady] = useState(false);
  const first = useRef(true);
  const opts = useMemo(() => optsOf(state), [state]);
  const fromDoc = !!meta.cover;

  useEffect(() => {
    let alive = true;
    loadCoverFonts().then(() => alive && setFontsReady(true));
    prepareCover(docId, meta).then((s) => { if (alive && (s.form.logo !== state.form.logo || s.form.logo2 !== state.form.logo2)) setState((x) => ({ ...x, form: { ...x.form, logo: x.form.logo ?? s.form.logo, logo2: x.form.logo2 ?? s.form.logo2 } })); });
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docId]);

  useEffect(() => {
    try { localStorage.setItem(coverKey(docId), JSON.stringify(state)); } catch { /* ignore */ }
    onState(state);
    if (!fontsReady) return;
    const incomplete = coverIncomplete(state).length > 0;
    onPreview(renderCover(state.form, state.style, opts, incomplete));
    if (first.current) { first.current = false; return; }
    // What you see is what you get: examples stay visible until the cover is complete.
    const t = setTimeout(() => (incomplete ? coverSvgPreview(state) : coverSvg(state)).then(onSvg), 900);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state, opts, docId, fontsReady]);

  const thumbs = useMemo(
    () => (fontsReady && enabled ? (Object.fromEntries(STYLES.map((s) => [s.id, renderCover(state.form, s.id, opts)])) as Record<StyleId, string>) : null),
    [fontsReady, enabled, state.form, opts],
  );
  const patch = (p: Partial<CoverForm>) => setState((s) => ({ ...s, form: { ...s.form, ...p } }));

  return (
    <div className="space-y-6">
      <Toggle label="Inclure une page de garde" checked={enabled} onChange={onEnabled} />
      {enabled && (
        <>
          {fromDoc && (
            <p className="rise flex gap-2 text-[14px] leading-snug text-ink/75">
              <Icon name="scan-text" size={18} className="mt-0.5 shrink-0 text-board" />
              Remplie avec ta page de garde d&apos;origine : vérifie les noms et le titre.
            </p>
          )}

          <section className="space-y-3">
            <h3 className="font-display text-[19px] leading-none font-black uppercase">Type</h3>
            <Select value={state.form.kind} onChange={(e) => { const k = e.target.value as DocKind; setState((s) => ({ ...switchKind(s, k), style: s.styleTouched ? s.style : KINDS[k].defaultStyle })); }} aria-label="Type de document">
              {(Object.keys(KINDS) as DocKind[]).map((k) => <option key={k} value={k}>{KINDS[k].label}</option>)}
            </Select>
          </section>

          <section className="space-y-3">
            <h3 className="font-display text-[19px] leading-none font-black uppercase">Modèle</h3>
            <div className="grid grid-cols-2 gap-x-3 gap-y-4">
              {STYLES.map((s) => {
                const active = state.style === s.id;
                return (
                  <button key={s.id} type="button" onClick={() => setState((x) => ({ ...x, style: s.id, styleTouched: true }))} className="group press text-left" aria-pressed={active}>
                    <div className={`overflow-hidden rounded-[2px] shadow-[0_6px_14px_-8px_rgba(0,0,0,0.5)] transition ${active ? "ring-[3px] ring-board" : "ring-1 ring-black/10 group-hover:ring-ink/30"}`}>
                      {thumbs ? <CoverView svg={thumbs[s.id]} /> : <div className="aspect-[595/842] animate-pulse bg-ink/5" />}
                    </div>
                    <span className="mt-1.5 flex items-center gap-1 text-[13px] font-bold">{active && <Icon name="circle-check" size={14} className="text-board" />}{s.name}</span>
                    <span className="block text-[11px] text-ink/60">{s.hint}</span>
                  </button>
                );
              })}
            </div>
          </section>

          <section className="space-y-3">
            <h3 className="font-display text-[19px] leading-none font-black uppercase">Couleur</h3>
            <div className="flex flex-wrap items-center gap-2.5">
              {PALETTES.map((p) => {
                const active = !state.mono && state.paletteId === p.id;
                return (
                  <button
                    key={p.id}
                    type="button"
                    aria-label={p.name}
                    title={p.name}
                    onClick={() => setState((x) => ({ ...x, paletteId: p.id, mono: false }))}
                    className={`press grid h-9 w-9 place-items-center rounded-full ${active ? "ring-2 ring-ink ring-offset-2" : "ring-1 ring-black/10"}`}
                    style={{ background: `linear-gradient(135deg, ${p.primary} 55%, ${p.accent} 55%)` }}
                  >
                    {active && <Icon name="check" size={14} stroke={3} className="text-white" />}
                  </button>
                );
              })}
              <button type="button" onClick={() => setState((x) => ({ ...x, mono: !x.mono }))} aria-pressed={state.mono} className={`press h-9 rounded-full px-3.5 text-[13px] font-bold ${state.mono ? "bg-ink text-white" : "bg-paper text-ink/75 ring-1 ring-black/10"}`}>
                Noir et blanc
              </button>
            </div>
            {state.style === "officiel" && <Toggle label="Cadre autour de la page" checked={state.frame} onChange={(frame) => setState((x) => ({ ...x, frame }))} />}
          </section>

          <section className="space-y-3 border-t border-ink/10 pt-5">
            <h3 className="font-display text-[19px] leading-none font-black uppercase">L&apos;essentiel</h3>
            <EssentialsStep form={state.form} onChange={patch} />
          </section>

          <details className="group border-y border-ink/10" open={fromDoc}>
            <summary className="flex cursor-pointer list-none items-center justify-between py-4 font-display text-[19px] leading-none font-black uppercase">
              Encadreurs, date, logos
              <Icon name="plus" size={18} className="text-board transition group-open:rotate-45" />
            </summary>
            <div className="pb-5"><DetailsStep form={state.form} onChange={patch} /></div>
          </details>
        </>
      )}
    </div>
  );
}
