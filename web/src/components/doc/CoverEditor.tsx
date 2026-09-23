"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { STYLES, loadCoverFonts, renderCover } from "@/lib/cover";
import { KINDS } from "@/lib/cover/kinds";
import { PALETTES } from "@/lib/cover/palettes";
import type { CoverForm, DocKind } from "@/lib/cover/types";
import type { DocMeta } from "@/lib/documents";
import { CoverView } from "../CoverView";
import { STORAGE_KEY as STUDIO_KEY, initialState, switchKind, type StudioState } from "../studio/state";
import { EssentialsStep } from "../studio/Steps";
import { Toggle } from "../ui";

const KIND_FROM_META: Record<string, DocKind> = {
  rapport_stage: "rapport_stage",
  memoire: "memoire",
  rapport: "rapport_projet",
  document: "expose",
};

const coverKey = (docId: string) => `propre:doc:cover:${docId}`;

/** Cover state for a document: its own saved state, else the studio draft, else built from the document. */
export function initialCover(docId: string, meta: DocMeta): StudioState {
  try {
    const own = localStorage.getItem(coverKey(docId));
    if (own) return JSON.parse(own) as StudioState;
    const studio = localStorage.getItem(STUDIO_KEY);
    if (studio) {
      const s = JSON.parse(studio) as StudioState;
      return { ...s, form: { ...s.form, title: s.form.title || meta.title || "" } };
    }
  } catch { /* ignore */ }
  const kind = KIND_FROM_META[meta.kind] ?? "autre";
  const base = switchKind(initialState(kind), kind);
  // Official bilingual header shown straight away; the school name is filled in the panel.
  return {
    ...base,
    style: KINDS[kind].defaultStyle,
    form: {
      ...base.form,
      institutionId: "autre",
      headerFr: "",
      headerEn: "",
      title: meta.title ?? "",
    },
  };
}

export async function coverSvg(state: StudioState): Promise<string> {
  await loadCoverFonts();
  const palette = PALETTES.find((p) => p.id === state.paletteId) ?? PALETTES[0];
  return renderCover(state.form, state.style, { palette, mono: state.mono, frame: state.frame }, false);
}

/** First attach: show the example header so the page looks finished (the user completes it in the panel). */
export async function coverSvgPreview(state: StudioState): Promise<string> {
  await loadCoverFonts();
  const palette = PALETTES.find((p) => p.id === state.paletteId) ?? PALETTES[0];
  return renderCover(state.form, state.style, { palette, mono: state.mono, frame: state.frame }, true);
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
  onSvg: (svg: string) => void;
  onState: (s: StudioState) => void;
};

/** Edits the cover next to the document: every change is applied automatically. */
export function CoverEditor({ docId, meta, enabled, onEnabled, onSvg, onState }: Props) {
  const [state, setState] = useState<StudioState>(() => initialCover(docId, meta));
  const [preview, setPreview] = useState("");
  const first = useRef(true);
  const palette = PALETTES.find((p) => p.id === state.paletteId) ?? PALETTES[0];
  const opts = useMemo(() => ({ palette, mono: state.mono, frame: state.frame }), [palette, state.mono, state.frame]);

  useEffect(() => {
    let alive = true;
    loadCoverFonts().then(() => { if (alive) setPreview(renderCover(state.form, state.style, opts)); });
    try { localStorage.setItem(coverKey(docId), JSON.stringify(state)); } catch { /* ignore */ }
    onState(state);
    if (first.current) { first.current = false; return () => { alive = false; }; }
    // What you see is what you get: examples stay visible until the cover is complete.
    const t = setTimeout(() => (coverIncomplete(state).length ? coverSvgPreview(state) : coverSvg(state)).then(onSvg), 900);
    return () => { alive = false; clearTimeout(t); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state, opts, docId]);

  const patch = (p: Partial<CoverForm>) => setState((s) => ({ ...s, form: { ...s.form, ...p } }));

  return (
    <div className="space-y-5">
      <Toggle label="Inclure une page de garde" checked={enabled} onChange={onEnabled} />
      {enabled && (
        <>
          <div className="flex items-start gap-4">
            <div className="w-28 shrink-0">{preview && <CoverView svg={preview} />}</div>
            <div className="flex-1 space-y-2">
              <p className="text-sm text-slate-600">Tes changements s&apos;appliquent automatiquement à la première page.</p>
              <div className="flex flex-wrap gap-1.5">
                {STYLES.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => setState((x) => ({ ...x, style: s.id, styleTouched: true }))}
                    className={`rounded-full px-3 py-1.5 text-xs font-bold ${state.style === s.id ? "bg-ink text-white" : "bg-white text-slate-600 ring-1 ring-slate-200"}`}
                  >
                    {s.name}
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                {PALETTES.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    aria-label={p.name}
                    onClick={() => setState((x) => ({ ...x, paletteId: p.id, mono: false }))}
                    className={`h-7 w-7 rounded-full ${!state.mono && state.paletteId === p.id ? "ring-2 ring-ink ring-offset-2" : ""}`}
                    style={{ background: p.primary }}
                  />
                ))}
              </div>
            </div>
          </div>
          <EssentialsStep form={state.form} onChange={patch} />
        </>
      )}
    </div>
  );
}
