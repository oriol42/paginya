"use client";

import { PALETTES } from "@/lib/cover/palettes";
import { KINDS, THEMES, type DocOptions, type DocStyle, type Letterhead } from "@/lib/documents";
import { LetterheadPanel } from "./LetterheadPanel";
import { Segmented, Toggle } from "../ui";

const MARGINS: { label: string; value: number[] }[] = [
  { label: "Normales", value: [2.5, 2.5, 2.5, 2.5] },
  { label: "Reliure", value: [2.5, 2.5, 3.5, 2.5] },
  { label: "Étroites", value: [2, 2, 2, 2] },
];
const COLORED = new Set(["universitaire", "moderne", "elegant", "corporate"]);

type Props = {
  style: DocStyle;
  options: DocOptions;
  onStyle: (s: DocStyle) => void;
  onOptions: (o: DocOptions) => void;
  kind: string;
  onKind: (kind: string) => void;
  letterhead: Letterhead | null;
  hasCover: boolean;
  onLetterhead: (value: Letterhead, options: DocOptions) => void;
};

export function DocStylePanel({ style, options, kind, onStyle, onOptions, onKind, letterhead, hasCover, onLetterhead }: Props) {
  const set = (patch: Partial<DocStyle>) => onStyle({ ...style, ...patch });
  const marginKey = MARGINS.find((m) => JSON.stringify(m.value) === JSON.stringify(style.margins))?.label ?? "Normales";
  return (
    <div className="space-y-6">
      <div>
        <p className="mb-2 font-display text-sm font-bold text-ink">C&apos;est quoi, ce document ?</p>
        <div className="grid grid-cols-2 gap-2">
          {KINDS.map((k) => {
            const active = kind === k.id;
            return (
              <button
                key={k.id}
                type="button"
                onClick={() => !active && onKind(k.id)}
                className={`rounded-xl px-3 py-2 text-left transition ${active ? "bg-brand-500 text-white shadow-md shadow-brand-500/25" : "bg-white ring-1 ring-slate-200 hover:ring-brand-300"}`}
              >
                <span className="block text-[13px] font-bold">{k.label}</span>
                <span className={`block text-[11px] leading-tight ${active ? "text-white/85" : "text-slate-500"}`}>{k.hint}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="rounded-2xl bg-white p-4 ring-1 ring-slate-100">
        <p className="mb-2 font-display text-sm font-bold text-ink">Ce que Paginya ajoute</p>
        <div className="grid gap-2">
          <Toggle label="Sommaire au début" checked={options.toc} onChange={(toc) => onOptions({ ...options, toc })} />
          <Toggle label="Table des matières à la fin" checked={options.toc_end} onChange={(toc_end) => onOptions({ ...options, toc_end })} />
          <Toggle label="Chaque grand titre sur une nouvelle page" checked={!!options.chapter_pages} onChange={(chapter_pages) => onOptions({ ...options, chapter_pages })} />
          <Toggle label="Listes des tableaux et figures" checked={options.lists} onChange={(lists) => onOptions({ ...options, lists })} />
          <Toggle label="Numéros de page" checked={options.page_numbers} onChange={(page_numbers) => onOptions({ ...options, page_numbers })} />
        </div>
      </div>

      {!hasCover && (
        <LetterheadPanel enabled={!!options.letterhead} value={letterhead} onChange={(value, on) => onLetterhead(value, { ...options, letterhead: on })} />
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-2">
        {THEMES.map((t) => {
          const active = style.theme === t.id;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => set({ theme: t.id, font: null, size: null, line: null, justify: null })}
              className={`group rounded-2xl p-1.5 text-left transition ${active ? "bg-brand-500 shadow-lg shadow-brand-500/25" : "bg-white ring-1 ring-slate-200 hover:ring-brand-300"}`}
            >
              <div className="aspect-[3/4] overflow-hidden rounded-xl bg-white">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={`/themes/${t.id}.png`} alt="" className="w-full object-cover object-top transition group-hover:scale-105" />
              </div>
              <span className={`mt-1.5 block px-1 font-display text-[13px] font-bold ${active ? "text-white" : "text-ink"}`}>{t.name}</span>
              <span className={`block px-1 pb-0.5 text-[11px] ${active ? "text-white/80" : "text-slate-500"}`}>{t.hint}</span>
            </button>
          );
        })}
      </div>

      {COLORED.has(style.theme) && (
        <section>
          <h3 className="mb-2.5 text-xs font-bold tracking-wider text-slate-500 uppercase">Couleur</h3>
          <div className="flex gap-3">
            {PALETTES.map((p) => (
              <button
                key={p.id}
                type="button"
                aria-label={p.name}
                onClick={() => set({ color: p.primary })}
                className={`h-10 w-10 rounded-full transition ${style.color === p.primary ? "scale-110 ring-2 ring-ink ring-offset-2" : "ring-1 ring-black/5"}`}
                style={{ background: p.primary }}
              />
            ))}
          </div>
        </section>
      )}

      <details className="group rounded-2xl bg-white ring-1 ring-slate-100">
        <summary className="flex cursor-pointer list-none items-center justify-between p-4 font-display text-sm font-bold text-ink">
          Réglages du texte (police, interligne, marges)
          <span className="text-brand-500 transition group-open:rotate-45">+</span>
        </summary>
        <div className="space-y-4 px-4 pb-4">
          <Segmented
            value={style.font ?? ""}
            onChange={(font) => set({ font: font || null })}
            options={[{ value: "", label: "Auto" }, { value: "Times New Roman", label: "Times" }, { value: "Arial", label: "Arial" }, { value: "Calibri", label: "Calibri" }]}
          />
          <div>
            <p className="mb-1.5 text-xs font-semibold text-slate-500">Interligne</p>
            <Segmented value={style.line ?? 0} onChange={(line) => set({ line: line || null })} options={[{ value: 0, label: "Auto" }, { value: 1.15, label: "1,15" }, { value: 1.5, label: "1,5" }, { value: 2, label: "2" }]} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="mb-1.5 text-xs font-semibold text-slate-500">Taille</p>
              <Segmented value={style.size ?? 0} onChange={(size) => set({ size: size || null })} options={[{ value: 0, label: "Auto" }, { value: 11, label: "11" }, { value: 12, label: "12" }]} />
            </div>
            <div>
              <p className="mb-1.5 text-xs font-semibold text-slate-500">Marges</p>
              <select
                value={marginKey}
                onChange={(e) => set({ margins: MARGINS.find((m) => m.label === e.target.value)!.value })}
                className="w-full rounded-xl bg-slate-100 px-3 py-2.5 text-sm font-semibold"
              >
                {MARGINS.map((m) => <option key={m.label}>{m.label}</option>)}
              </select>
            </div>
          </div>
          <Toggle label="Texte justifié" checked={style.justify ?? style.theme !== "simple"} onChange={(justify) => set({ justify })} />
        </div>
      </details>

    </div>
  );
}
