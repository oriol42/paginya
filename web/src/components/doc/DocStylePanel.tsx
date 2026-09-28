"use client";

import { PALETTES } from "@/lib/cover/palettes";
import { KINDS, THEMES, type DocOptions, type DocStyle, type Letterhead } from "@/lib/documents";
import { LetterheadPanel } from "./LetterheadPanel";
import { Icon } from "../Icon";
import { Segmented, Select, Toggle } from "../ui";

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
                className={`rounded-md px-3 py-2 text-left transition ${active ? "bg-brand-500 text-white" : "bg-paper ring-1 ring-black/10 hover:ring-brand-300"}`}
              >
                <span className="block text-[13px] font-bold">{k.label}</span>
                <span className={`block text-[11px] leading-tight ${active ? "text-white/85" : "text-ink/60"}`}>{k.hint}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="border-t border-ink/10 pt-5">
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
        <div className="border-t border-ink/10 pt-5"><LetterheadPanel enabled={!!options.letterhead} value={letterhead} onChange={(value, on) => onLetterhead(value, { ...options, letterhead: on })} /></div>
      )}

      <div className="grid grid-cols-2 gap-x-3 gap-y-4 border-t border-ink/10 pt-5 sm:grid-cols-3 lg:grid-cols-2">
        {THEMES.map((t) => {
          const active = style.theme === t.id;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => set({ theme: t.id, font: null, size: null, line: null, justify: null })}
              className="group press text-left"
              aria-pressed={active}
            >
              <div className={`aspect-[3/4] overflow-hidden rounded-[2px] bg-paper shadow-[0_6px_14px_-8px_rgba(0,0,0,0.5)] transition ${active ? "ring-[3px] ring-board" : "ring-1 ring-black/10 group-hover:ring-ink/30"}`}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={`/themes/${t.id}.png`} alt="" className="w-full object-cover object-top transition group-hover:scale-105" />
              </div>
              <span className="mt-1.5 flex items-center gap-1 font-display text-[13px] font-bold text-ink">{active && <Icon name="circle-check" size={14} className="text-board" />}{t.name}</span>
              <span className="block text-[11px] text-ink/60">{t.hint}</span>
            </button>
          );
        })}
      </div>

      {COLORED.has(style.theme) && (
        <section>
          <h3 className="mb-2.5 text-xs font-bold tracking-wider text-ink/60 uppercase">Couleur</h3>
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

      <details className="group border-y border-ink/10">
        <summary className="flex cursor-pointer list-none items-center justify-between py-4 font-display text-sm font-bold text-ink">
          Réglages du texte (police, interligne, marges)
          <Icon name="plus" size={18} className="text-board transition group-open:rotate-45" />
        </summary>
        <div className="space-y-4 pb-4">
          <Segmented
            value={style.font ?? ""}
            onChange={(font) => set({ font: font || null })}
            options={[{ value: "", label: "Auto" }, { value: "Times New Roman", label: "Times" }, { value: "Arial", label: "Arial" }, { value: "Calibri", label: "Calibri" }]}
          />
          <div>
            <p className="mb-1.5 text-xs font-semibold text-ink/60">Interligne</p>
            <Segmented value={style.line ?? 0} onChange={(line) => set({ line: line || null })} options={[{ value: 0, label: "Auto" }, { value: 1.15, label: "1,15" }, { value: 1.5, label: "1,5" }, { value: 2, label: "2" }]} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="mb-1.5 text-xs font-semibold text-ink/60">Taille</p>
              <Segmented value={style.size ?? 0} onChange={(size) => set({ size: size || null })} options={[{ value: 0, label: "Auto" }, { value: 11, label: "11" }, { value: 12, label: "12" }]} />
            </div>
            <div>
              <p className="mb-1.5 text-xs font-semibold text-ink/60">Marges</p>
              <Select
                value={marginKey}
                onChange={(e) => set({ margins: MARGINS.find((m) => m.label === e.target.value)!.value })}
                aria-label="Marges"
              >
                {MARGINS.map((m) => <option key={m.label}>{m.label}</option>)}
              </Select>
            </div>
          </div>
          <Toggle label="Texte justifié" checked={style.justify ?? style.theme !== "simple"} onChange={(justify) => set({ justify })} />
        </div>
      </details>

    </div>
  );
}
