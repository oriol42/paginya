"use client";

import { FONTS } from "@/lib/cover";
import type { FontId } from "@/lib/cover/types";
import { Icon } from "@/components/Icon";

type Props = {
  fontId: FontId;
  customColor?: string;
  customActive: boolean;
  onFont: (id: FontId) => void;
  onCustom: (color: string) => void;
};

/** "Ma couleur" (any colour, the school's for instance): goes at the end of the row of palettes. */
export function CustomColor({ customColor, customActive, onCustom }: Pick<Props, "customColor" | "customActive" | "onCustom">) {
  const color = customColor ?? "#0E9F6E";
  return (
    <label
      title="Choisir ma propre couleur"
      className={`press relative flex h-10 cursor-pointer items-center gap-2 rounded-full bg-paper pr-3.5 pl-1.5 text-[13px] font-bold text-ink/80 ${customActive ? "ring-2 ring-ink ring-offset-2" : "ring-1 ring-black/10"}`}
    >
      <span className="grid h-7 w-7 place-items-center rounded-full" style={{ background: customActive ? color : "conic-gradient(#ef4444,#f59e0b,#22c55e,#06b6d4,#6366f1,#ec4899,#ef4444)" }}>
        {customActive && <Icon name="check" size={13} stroke={3} className="text-white" />}
      </span>
      Ma couleur
      <input type="color" value={color} onChange={(e) => onCustom(e.target.value)} onClick={() => onCustom(color)} className="absolute inset-0 h-full w-full cursor-pointer opacity-0" aria-label="Choisir ma propre couleur" />
    </label>
  );
}

const SAMPLE: Record<FontId, string> = { auto: "inherit", tinos: "Tinos", poppins: "Poppins", playfair: "Playfair Display", inter: "Inter" };

/** One typeface for the whole cover, or the fonts the design was drawn with. */
export function FontPicker({ fontId, onFont }: Pick<Props, "fontId" | "onFont">) {
  return (
    <div className="flex flex-wrap gap-2">
      {FONTS.map((f) => {
        const active = fontId === f.id;
        return (
          <button
            key={f.id}
            type="button"
            aria-pressed={active}
            onClick={() => onFont(f.id)}
            className={`press rounded-md px-3 py-2 text-[14px] ${active ? "bg-ink font-bold text-white" : "bg-paper text-ink/85 ring-1 ring-black/10 hover:ring-ink/30"}`}
            style={{ fontFamily: SAMPLE[f.id] }}
          >
            {f.name}
          </button>
        );
      })}
    </div>
  );
}
