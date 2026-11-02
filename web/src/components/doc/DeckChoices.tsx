"use client";

import { useState } from "react";
import type { DeckInfo, DeckItem, DeckPatch, DeckSlide } from "@/lib/documents";

/** Same colours as the themes of api/app/doc/slides.py. */
const THEMES = [
  { id: "halo", label: "Halo", bg: "linear-gradient(180deg,#BBD5A6,#FFFFFF 38%)", accent: "#2F6B1F", second: "#8BBF5A" },
  { id: "iris", label: "Iris", bg: "linear-gradient(180deg,#C6BBE9,#FFFFFF 38%)", accent: "#4C2AB0", second: "#E0245E" },
  { id: "brume", label: "Brume", bg: "linear-gradient(180deg,#B3D6E0,#FFFFFF 38%)", accent: "#12708C", second: "#F08A5D" },
  { id: "prairie", label: "Prairie", bg: "linear-gradient(100deg,#2F5D14,#4E8A1F 62%,#8CC63F 63%,#8CC63F 67%,#FFFFFF 68%)", accent: "#FFFFFF", second: "#8CC63F" },
  { id: "horizon", label: "Horizon", bg: "linear-gradient(172deg,#FFFFFF 66%,#7CB518 67%,#7CB518 71%,#1B6F6A 72%)", accent: "#1B6F6A", second: "#7CB518" },
  { id: "azur", label: "Azur", bg: "linear-gradient(35deg,#173B75,#2A5CAA 48%,#F7F8FA 49%)", accent: "#16263F", second: "#7FA8D9" },
  { id: "graphite", label: "Graphite", bg: "linear-gradient(100deg,#24272C,#3C4047 62%,#9AA0A8 63%,#9AA0A8 67%,#FFFFFF 68%)", accent: "#FFFFFF", second: "#9AA0A8" },
  { id: "ambre", label: "Ambre", bg: "linear-gradient(176deg,#FFFBF2 12%,#F2B71F 13%,#F2B71F 18%,#5A1A0E 19%,#3C0F07 80%,#F2B71F 81%,#F2B71F 86%,#FFFBF2 87%)", accent: "#FFFFFF", second: "#F2B71F" },
  { id: "citron", label: "Citron", bg: "linear-gradient(145deg,#2B7004,#3F9A0A 42%,#B6E34A 43%,#B6E34A 47%,#FFFFFF 48%)", accent: "#FFFFFF", second: "#B6E34A" },
  { id: "aurora", label: "Aurora", bg: "linear-gradient(135deg,#12102B,#3B1E8F 55%,#0E7490)", accent: "#A78BFA", second: "#22D3EE" },
  { id: "braise", label: "Braise", bg: "linear-gradient(135deg,#1A0B0B,#9A2A12 55%,#D9480F)", accent: "#FF7A3D", second: "#FFC24B" },
  { id: "lagon", label: "Lagon", bg: "linear-gradient(135deg,#04232B,#0F766E 55%,#0369A1)", accent: "#2DD4BF", second: "#FDE68A" },
  { id: "minuit", label: "Minuit", bg: "linear-gradient(135deg,#0B1220,#1E3A5F 60%,#3A2E12)", accent: "#E9C46A", second: "#60A5FA" },
  { id: "perle", label: "Perle", bg: "linear-gradient(135deg,#F4F1FF,#D9CCFF 50%,#FFD6E8)", accent: "#6D3BEA", second: "#EC4899" },
  { id: "menthe", label: "Menthe", bg: "linear-gradient(135deg,#EFFBF5,#BFF0DD 50%,#FDE9B8)", accent: "#0E8F6E", second: "#F59E0B" },
  { id: "academique", label: "Académique", bg: "#FFFFFF", accent: "#1F3A5F", second: "#C9A227" },
  { id: "sorbonne", label: "Sorbonne", bg: "#FBF8F3", accent: "#7A1F2E", second: "#C49A3A" },
  { id: "contraste", label: "Contraste", bg: "#FFFFFF", accent: "#111111", second: "#FF6A00" },
  { id: "vitamine", label: "Vitamine", bg: "#FFFFFF", accent: "#F4600C", second: "#FFB000" },
  { id: "foret", label: "Forêt", bg: "#FFFFFF", accent: "#00843D", second: "#F7C800" },
  { id: "terre", label: "Terre", bg: "#FFFCF8", accent: "#8A5A3C", second: "#C9A27E" },
  { id: "campus", label: "Campus", bg: "#FFFFFF", accent: "#0E7C5A", second: "#F2B632" },
  { id: "savane", label: "Savane", bg: "#FDF9F0", accent: "#B4581F", second: "#3F7D4E" },
  { id: "ocean", label: "Océan", bg: "#FFFFFF", accent: "#0B7A8C", second: "#F97352" },
  { id: "medical", label: "Médical", bg: "#F7FBFC", accent: "#0F8B8D", second: "#3B82C4" },
  { id: "royal", label: "Royal", bg: "#FFFFFF", accent: "#4338CA", second: "#EC4899" },
  { id: "corail", label: "Corail", bg: "#FFF8F1", accent: "#E4572E", second: "#F3A712" },
  { id: "soleil", label: "Soleil", bg: "#FFFDF5", accent: "#26221A", second: "#F5B800" },
  { id: "ardoise", label: "Ardoise", bg: "#F4F4F2", accent: "#2B2D33", second: "#D97706" },
  { id: "nuit", label: "Nuit", bg: "#0F172A", accent: "#22D3EE", second: "#A78BFA" },
  { id: "neon", label: "Néon", bg: "#14101F", accent: "#E879F9", second: "#22D3EE" },
];

/** School work: opens and closes like the report. Plain presentation: no establishment. */
export function PurposePick({ school, disabled, onChange }: { school: boolean; disabled?: boolean; onChange: (school: boolean) => void }) {
  return (
    <div>
      <p className="text-[14px] font-bold">C&apos;est pour quoi ?</p>
      <div role="radiogroup" aria-label="Type de présentation" className="mt-2 grid grid-cols-2 gap-2">
        {[{ on: true, label: "Pour l'école", hint: "Page de garde et de fin avec logos" }, { on: false, label: "Présentation simple", hint: "Sans établissement" }].map((c) => (
          <button key={c.label} type="button" role="radio" aria-checked={school === c.on} disabled={disabled} onClick={() => onChange(c.on)}
            className={`press rounded-md p-2.5 text-left ring-1 ${school === c.on ? "ring-2 ring-board" : "ring-black/15"}`}>
            <span className="block text-[14px] font-bold">{c.label}</span>
            <span className="mt-0.5 block text-[12px] leading-snug text-ink/60">{c.hint}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function SlideCount({ value, max, disabled, onChange }: { value: number; max: number; disabled?: boolean; onChange: (n: number) => void }) {
  return (
    <label className="block">
      <span className="flex items-baseline justify-between text-[14px] font-bold">
        Nombre de diapos
        <span className="font-display text-[26px] leading-none font-black text-board">{value}</span>
      </span>
      <input type="range" min={5} max={max} value={value} disabled={disabled} onChange={(e) => onChange(Number(e.target.value))} className="mt-2 w-full accent-[var(--color-board)]" />
      <span className="text-[13px] text-ink/60">Pour une soutenance de 15 minutes, compte 10 à 15 diapos.</span>
    </label>
  );
}

export function ThemePick({ value, disabled, onChange, auto }: { value: string; disabled?: boolean; onChange: (id: string) => void; auto?: boolean }) {
  return (
    <div>
      <p className="text-[14px] font-bold">Style</p>
      <div role="radiogroup" aria-label="Style de la présentation" className="mt-2 grid grid-cols-3 gap-2">
        {auto && (
          <button type="button" role="radio" aria-checked={value === "auto"} disabled={disabled} onClick={() => onChange("auto")}
            className={`press min-w-0 rounded-md p-1.5 text-[12px] font-bold ring-1 ${value === "auto" ? "ring-2 ring-board" : "ring-black/15"}`}>
            <span className="relative grid aspect-video place-items-center overflow-hidden rounded-[3px] bg-board text-center text-[11px] leading-tight text-white">Selon ton sujet</span>
            <span className="mt-1 block">Automatique</span>
          </button>
        )}
        {THEMES.map((t) => (
          <button
            key={t.id}
            type="button"
            role="radio"
            aria-checked={value === t.id}
            disabled={disabled}
            onClick={() => onChange(t.id)}
            className={`press min-w-0 rounded-md p-1.5 text-[12px] font-bold ring-1 ${value === t.id ? "ring-2 ring-board" : "ring-black/15"}`}
          >
            <span className="relative block aspect-video overflow-hidden rounded-[3px] ring-1 ring-black/10" style={{ background: t.bg }}>
              <span className="absolute top-[22%] left-[12%] h-[10%] w-1/2 rounded-sm" style={{ background: t.accent }} />
              <span className="absolute top-[42%] left-[12%] h-[6%] w-1/4" style={{ background: t.second }} />
              <span className="absolute -right-[12%] -bottom-[25%] aspect-square w-1/2 rounded-full" style={{ background: t.accent }} />
            </span>
            <span className="mt-1 block">{t.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

const PALETTES = [
  ["1F3A5F", "C9A227"], ["7A1F2E", "C49A3A"], ["0E7C5A", "F2B632"], ["0B7A8C", "F97352"], ["4338CA", "EC4899"], ["E4572E", "F3A712"],
  ["111111", "FF6A00"], ["6D28D9", "22D3EE"], ["BE123C", "FBBF24"], ["0F766E", "A3E635"], ["1D4ED8", "F43F5E"], ["854D0E", "65A30D"],
  ["DB2777", "7C3AED"], ["0369A1", "FACC15"], ["15803D", "EA580C"], ["374151", "10B981"],
];
const SIMPLE = ["liste", "grille", "schema", "panneau", "chronologie", "etapes"];
const LAYOUTS: Record<string, string> = { liste: "Liste", grille: "Cartes", schema: "Schéma", panneau: "Bloc de couleur", chronologie: "Chronologie", etapes: "Étapes" };
const MOTIONS = [["fondu", "Fondu"], ["monter", "Monter"], ["glisser", "Glisser"], ["zoom", "Zoom"], ["balayer", "Balayer"]];
const field = "w-full rounded-md bg-white px-2.5 py-2 text-[14px] ring-1 ring-black/15 focus:outline-none focus:ring-2 focus:ring-board";

/** The colours of the slides: ready-made pairs, or any colour the user wants. */
function ColorPick({ colors, disabled, onChange }: { colors: { accent?: string; second?: string }; disabled: boolean; onChange: (colors: { accent?: string; second?: string }) => void }) {
  const hex = (v: string | undefined, fallback: string) => `#${v || fallback}`;
  return (
    <div>
      <p className="text-[14px] font-bold">Couleurs</p>
      <div className="mt-2 grid grid-cols-8 gap-1.5">
        {PALETTES.map(([accent, second]) => (
          <button key={accent + second} type="button" disabled={disabled} aria-label={`Couleurs ${accent} et ${second}`} onClick={() => onChange({ accent, second })}
            className={`press aspect-square overflow-hidden rounded-full ring-1 ${colors.accent === accent && colors.second === second ? "ring-2 ring-ink" : "ring-black/15"}`}
            style={{ background: `linear-gradient(135deg, #${accent} 50%, #${second} 50%)` }} />
        ))}
      </div>
      <div className="mt-2.5 flex items-center gap-3 text-[13px] font-semibold">
        <label className="flex items-center gap-1.5">Principale<input type="color" disabled={disabled} value={hex(colors.accent, "1F3A5F")} onChange={(e) => onChange({ ...colors, accent: e.target.value.slice(1).toUpperCase() })} className="h-8 w-9 cursor-pointer rounded border-0 bg-transparent" /></label>
        <label className="flex items-center gap-1.5">Secondaire<input type="color" disabled={disabled} value={hex(colors.second, "C9A227")} onChange={(e) => onChange({ ...colors, second: e.target.value.slice(1).toUpperCase() })} className="h-8 w-9 cursor-pointer rounded border-0 bg-transparent" /></label>
        {(colors.accent || colors.second) && <button type="button" disabled={disabled} onClick={() => onChange({})} className="text-ink/60 underline">Annuler</button>}
      </div>
    </div>
  );
}

/** Every slide can be changed: words, layout, order, or removed. */
function SlideEditor({ slides, busy, onSave }: { slides: DeckSlide[]; busy: boolean; onSave: (edited: DeckSlide[]) => void }) {
  const [draft, setDraft] = useState(slides);
  const [open, setOpen] = useState(-1);
  const change = (i: number, patch: Partial<DeckSlide>) => setDraft(draft.map((s, k) => (k === i ? { ...s, ...patch } : s)));
  const move = (i: number, by: number) => {
    const next = [...draft];
    const [slide] = next.splice(i, 1);
    next.splice(i + by, 0, slide);
    setDraft(next);
    setOpen(-1);
  };
  const dirty = JSON.stringify(draft) !== JSON.stringify(slides);
  return (
    <div>
      <p className="text-[14px] font-bold">Modifier les diapos</p>
      <ul className="mt-2 space-y-1.5">
        {draft.map((s, i) => (
          <li key={i} className="rounded-md ring-1 ring-black/10">
            <div className="flex items-center gap-1 px-2 py-1.5">
              <button type="button" onClick={() => setOpen(open === i ? -1 : i)} className="min-w-0 flex-1 truncate text-left text-[13px] font-semibold">{i + 3}. {s.title}</button>
              <button type="button" disabled={i === 0} onClick={() => move(i, -1)} aria-label="Monter" className="px-1 text-ink/60 disabled:opacity-30">↑</button>
              <button type="button" disabled={i === draft.length - 1} onClick={() => move(i, 1)} aria-label="Descendre" className="px-1 text-ink/60 disabled:opacity-30">↓</button>
              <button type="button" disabled={draft.length < 2} onClick={() => { setDraft(draft.filter((_, k) => k !== i)); setOpen(-1); }} aria-label="Supprimer" className="px-1 text-pin">✕</button>
            </div>
            {open === i && (
              <div className="space-y-2 border-t border-black/10 p-2">
                <input aria-label="Titre" value={s.title} onChange={(e) => change(i, { title: e.target.value })} className={field} />
                {SIMPLE.includes(s.type) && (
                  <select aria-label="Mise en page" value={s.type} onChange={(e) => change(i, { type: e.target.value })} className={field}>
                    {SIMPLE.map((k) => <option key={k} value={k}>{LAYOUTS[k]}</option>)}
                  </select>
                )}
                {s.type === "grand" && <input aria-label="Grand mot ou chiffre" value={s.value ?? ""} onChange={(e) => change(i, { value: e.target.value })} className={field} />}
                {(s.type === "grand" || s.type === "encadre") && <textarea aria-label="Texte" rows={3} value={s.text ?? ""} onChange={(e) => change(i, { text: e.target.value })} className={field} />}
                {s.type === "schema" && <input aria-label="Mot au centre" placeholder="Mot au centre (facultatif)" value={s.key ?? ""} onChange={(e) => change(i, { key: e.target.value })} className={field} />}
                {s.type === "panneau" && <textarea aria-label="Message du bloc" rows={2} value={s.key ?? ""} onChange={(e) => change(i, { key: e.target.value })} className={field} />}
                {s.items?.map((item: DeckItem, k: number) => (
                  <div key={k} className="space-y-1 rounded bg-ink/5 p-1.5">
                    <input aria-label="Titre de l'élément" value={item.head} onChange={(e) => change(i, { items: s.items!.map((x, j) => (j === k ? { ...x, head: e.target.value } : x)) })} className={field} />
                    <textarea aria-label="Texte de l'élément" rows={2} value={item.text} onChange={(e) => change(i, { items: s.items!.map((x, j) => (j === k ? { ...x, text: e.target.value } : x)) })} className={field} />
                  </div>
                ))}
                <select aria-label="Animation de cette diapo" value={s.motion ?? ""} onChange={(e) => change(i, { motion: e.target.value })} className={field}>
                  <option value="">Animation : comme les autres diapos</option>
                  {MOTIONS.map(([id, label]) => <option key={id} value={id}>Animation : {label}</option>)}
                  <option value="aucune">Animation : aucune</option>
                </select>
                <input aria-label="À retenir" placeholder="Phrase à retenir (facultatif)" value={s.takeaway ?? ""} onChange={(e) => change(i, { takeaway: e.target.value })} className={field} />
              </div>
            )}
          </li>
        ))}
      </ul>
      {dirty && (
        <button type="button" disabled={busy} onClick={() => onSave(draft)} className="press mt-2 w-full rounded-md bg-board px-3 py-3 text-[14px] font-bold text-white">
          {busy ? "Mise à jour…" : "Appliquer mes changements"}
        </button>
      )}
    </div>
  );
}

/** How things appear, for the whole talk: one tap. A slide can have its own in « Modifier les diapos ». */
function MotionPick({ deck, busy, onChange }: { deck: DeckInfo; busy: boolean; onChange: (patch: DeckPatch) => void }) {
  const off = deck.moving === false;
  const chosen = off ? "" : deck.motion ?? "monter";
  const pill = (on: boolean) => `press rounded-md px-1 py-2 text-[12px] font-bold ring-1 ${on ? "ring-2 ring-board" : "ring-black/15"}`;
  return (
    <div>
      <p className="text-[14px] font-bold">Animations</p>
      <div role="radiogroup" aria-label="Animations" className="mt-2 grid grid-cols-3 gap-1.5">
        {MOTIONS.map(([id, label]) => (
          <button key={id} type="button" role="radio" aria-checked={chosen === id} disabled={busy} onClick={() => chosen !== id && onChange({ moving: true, motion: id })} className={pill(chosen === id)}>{label}</button>
        ))}
        <button type="button" role="radio" aria-checked={off} disabled={busy} onClick={() => !off && onChange({ moving: false })} className={pill(off)}>Aucune</button>
      </div>
      {!off && (
        <div className="mt-2 grid grid-cols-2 gap-1.5">
          {[{ click: false, label: "Toute seule" }, { click: true, label: "À chaque clic" }].map((c) => (
            <button key={c.label} type="button" disabled={busy} aria-pressed={(deck.click === true) === c.click} onClick={() => (deck.click === true) !== c.click && onChange({ click: c.click })} className={pill((deck.click === true) === c.click)}>{c.label}</button>
          ))}
        </div>
      )}
      <p className="mt-1.5 text-[12px] text-ink/60">Pour voir l&apos;effet : lance le diaporama. Une diapo peut avoir la sienne dans « Modifier les diapos ».</p>
    </div>
  );
}

/** In the editor: the look changes at once; a new number of slides is written again by the AI, on request. */
export function DeckPanel({ deck, busy, onChange }: { deck: DeckInfo; busy: boolean; onChange: (patch: DeckPatch) => void }) {
  const [count, setCount] = useState(deck.slides);
  return (
    <div className="space-y-4">
      {deck.file && <p className="truncate rounded-md bg-ink/5 px-3 py-2 text-[13px] font-semibold text-ink/70" title={deck.file}>Fichier : {deck.file}</p>}
      <PurposePick school={deck.school !== false} disabled={busy} onChange={(school) => school !== (deck.school !== false) && onChange({ school })} />
      <ThemePick value={deck.theme} disabled={busy} onChange={(theme) => theme !== deck.theme && onChange({ theme })} />
      <ColorPick colors={deck.colors ?? {}} disabled={busy} onChange={(colors) => onChange({ colors })} />
      <div>
        <p className="text-[14px] font-bold">Police des titres</p>
        <div className="mt-2 grid grid-cols-4 gap-1.5">
          {[["", "Du style"], ["Calibri", "Moderne"], ["Cambria", "Classique"], ["Arial", "Forte"]].map(([font, label]) => (
            <button key={font} type="button" disabled={busy} onClick={() => onChange({ font })} className={`press rounded-md px-1 py-2 text-[12px] font-bold ring-1 ${(deck.font ?? "") === font ? "ring-2 ring-board" : "ring-black/15"}`}>{label}</button>
          ))}
        </div>
      </div>
      {deck.content && <SlideEditor key={JSON.stringify(deck.content)} slides={deck.content} busy={busy} onSave={(edited) => onChange({ edited })} />}
      <SlideCount value={Math.min(count, deck.max)} max={deck.max} disabled={busy} onChange={setCount} />
      {count !== deck.slides && (
        <button type="button" disabled={busy} onClick={() => onChange({ slides: count })} className="press w-full rounded-md bg-board px-3 py-3 text-[14px] font-bold text-white">
          {busy ? "L'IA refait tes diapos…" : `Refaire en ${count} diapos`}
        </button>
      )}
      <MotionPick deck={deck} busy={busy} onChange={onChange} />
      <label className={`press block cursor-pointer rounded-md px-3 py-3 text-center text-[14px] font-bold ring-1 ring-black/15 hover:bg-ink/5 ${busy ? "pointer-events-none opacity-50" : ""}`}>
        Ajouter le logo de ton école
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = "";
            if (!file) return;
            const reader = new FileReader();
            reader.onload = () => onChange({ logo: String(reader.result) });
            reader.readAsDataURL(file);
          }}
        />
      </label>
    </div>
  );
}
