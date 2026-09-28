"use client";

import { STYLES } from "@/lib/cover";
import { PALETTES } from "@/lib/cover/palettes";
import type { StyleId } from "@/lib/cover/types";
import { CoverView } from "../CoverView";
import { Toggle } from "../ui";
import { Icon } from "@/components/Icon";

type Props = {
  style: StyleId;
  paletteId: string;
  mono: boolean;
  frame: boolean;
  thumbs: Record<StyleId, string> | null;
  onStyle: (s: StyleId) => void;
  onPalette: (id: string) => void;
  onMono: (v: boolean) => void;
  onFrame: (v: boolean) => void;
};

export function StyleStep(p: Props) {
  return (
    <div className="space-y-6">
      <div className="no-scrollbar -mx-5 flex snap-x snap-mandatory gap-3 overflow-x-auto px-5 pb-2 lg:mx-0 lg:grid lg:grid-cols-2 lg:overflow-visible lg:px-0">
        {STYLES.map((s) => {
          const active = p.style === s.id;
          return (
            <button
              key={s.id}
              type="button"
              onClick={() => p.onStyle(s.id)}
              className={`w-[46%] shrink-0 snap-start rounded-md p-2 text-left transition lg:w-auto ${
                active ? "bg-brand-500" : "bg-paper ring-1 ring-black/10 hover:ring-brand-300"
              }`}
            >
              {p.thumbs ? <CoverView svg={p.thumbs[s.id]} /> : <div className="aspect-[595/842] rounded bg-ink/5" />}
              <span className={`mt-2 block px-1.5 font-display text-sm font-bold ${active ? "text-white" : "text-ink"}`}>{s.name}</span>
              <span className={`block px-1.5 pb-1 text-xs ${active ? "text-white/80" : "text-ink/60"}`}>{s.hint}</span>
            </button>
          );
        })}
      </div>

      <section>
        <h3 className="mb-3 text-xs font-bold tracking-wider text-ink/60 uppercase">Couleur</h3>
        <div className="flex flex-wrap items-center gap-3">
          {PALETTES.map((pal) => {
            const active = !p.mono && p.paletteId === pal.id;
            return (
              <button
                key={pal.id}
                type="button"
                onClick={() => { p.onPalette(pal.id); p.onMono(false); }}
                aria-label={pal.name}
                title={pal.name}
                className={`relative grid h-12 w-12 place-items-center rounded-full transition ${active ? "scale-110 ring-2 ring-ink ring-offset-2" : "ring-1 ring-black/5"}`}
                style={{ background: `linear-gradient(135deg, ${pal.primary} 55%, ${pal.accent} 55%)` }}
              >
                {active && <Icon name="check" size={16} stroke={3} className="text-white" />}
              </button>
            );
          })}
          <button
            type="button"
            onClick={() => p.onMono(!p.mono)}
            className={`h-12 rounded-full px-4 text-sm font-bold transition ${p.mono ? "bg-ink text-white" : "bg-paper text-ink/80 ring-1 ring-black/10"}`}
          >
            ◐ Noir & blanc
          </button>
        </div>
      </section>

      {p.style === "officiel" && <Toggle label="Cadre autour de la page" checked={p.frame} onChange={p.onFrame} />}
    </div>
  );
}
