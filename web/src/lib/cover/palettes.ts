import type { Palette, RenderOptions } from "./types";

export const PALETTES: Palette[] = [
  { id: "emeraude", name: "Émeraude", primary: "#0E9F6E", secondary: "#065F46", accent: "#F59E0B", light: "#ECFDF5" },
  { id: "bleu", name: "Bleu académique", primary: "#1E3A8A", secondary: "#0F172A", accent: "#FACC15", light: "#EFF6FF" },
  { id: "bordeaux", name: "Bordeaux", primary: "#9F1239", secondary: "#4C0519", accent: "#D4AF37", light: "#FFF1F2" },
  { id: "terracotta", name: "Terracotta", primary: "#C2410C", secondary: "#431407", accent: "#0D9488", light: "#FFF7ED" },
  { id: "graphite", name: "Graphite", primary: "#334155", secondary: "#0F172A", accent: "#38BDF8", light: "#F1F5F9" },
];

const MONO: Palette = {
  id: "mono", name: "Noir & blanc", primary: "#1F1F1F", secondary: "#000000", accent: "#6B6B6B", light: "#EFEFEF",
};

/** Colors actually used for drawing (black & white mode for cheap printing). */
export function inks(o: RenderOptions): Palette {
  return o.mono ? MONO : o.palette;
}
