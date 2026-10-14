import type { Palette, RenderOptions } from "./types";

export const PALETTES: Palette[] = [
  { id: "emeraude", name: "Émeraude", primary: "#0E9F6E", secondary: "#065F46", accent: "#F59E0B", light: "#ECFDF5" },
  { id: "bleu", name: "Bleu académique", primary: "#1E3A8A", secondary: "#0F172A", accent: "#FACC15", light: "#EFF6FF" },
  { id: "bordeaux", name: "Bordeaux", primary: "#9F1239", secondary: "#4C0519", accent: "#D4AF37", light: "#FFF1F2" },
  { id: "terracotta", name: "Terracotta", primary: "#C2410C", secondary: "#431407", accent: "#0D9488", light: "#FFF7ED" },
  { id: "graphite", name: "Graphite", primary: "#334155", secondary: "#0F172A", accent: "#38BDF8", light: "#F1F5F9" },
  { id: "cameroun", name: "Vert-rouge-jaune", primary: "#007A3D", secondary: "#CE1126", accent: "#FCD116", light: "#F0FAF4" },
  { id: "violet", name: "Violet", primary: "#6D28D9", secondary: "#2E1065", accent: "#F472B6", light: "#F5F3FF" },
  { id: "or", name: "Noir et or", primary: "#1C1917", secondary: "#0C0A09", accent: "#C9A227", light: "#FAF7EF" },
  { id: "ocean", name: "Océan", primary: "#0E7490", secondary: "#083344", accent: "#F97316", light: "#ECFEFF" },
  { id: "marine", name: "Bleu marine", primary: "#0B2545", secondary: "#061A33", accent: "#E0A526", light: "#EEF3FA" },
  { id: "foret", name: "Vert forêt", primary: "#14532D", secondary: "#052E16", accent: "#EAB308", light: "#F0FDF4" },
  { id: "rouge", name: "Rouge", primary: "#B91C1C", secondary: "#450A0A", accent: "#1F2937", light: "#FEF2F2" },
  { id: "ciel", name: "Bleu ciel", primary: "#0369A1", secondary: "#0C4A6E", accent: "#F43F5E", light: "#F0F9FF" },
  { id: "chocolat", name: "Chocolat", primary: "#6B3410", secondary: "#3B1D09", accent: "#D97706", light: "#FBF5EE" },
  { id: "rose", name: "Rose", primary: "#BE185D", secondary: "#500724", accent: "#0EA5E9", light: "#FDF2F8" },
  { id: "turquoise", name: "Turquoise", primary: "#0F766E", secondary: "#134E4A", accent: "#FB923C", light: "#F0FDFA" },
  { id: "prune", name: "Prune", primary: "#581C87", secondary: "#3B0764", accent: "#FBBF24", light: "#FAF5FF" },
];

const hex = (n: number) => Math.round(Math.max(0, Math.min(255, n))).toString(16).padStart(2, "0");
const mix = (a: number[], b: number[], t: number) => `#${a.map((v, i) => hex(v + (b[i] - v) * t)).join("")}`;

/** A whole palette from one colour picked by the user (their school's colour, for instance). */
export function customPalette(color: string): Palette {
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(color.trim());
  const rgb = m ? [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)] : [14, 159, 110];
  const luminance = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255;
  const primary = luminance > 0.62 ? mix(rgb, [0, 0, 0], 0.35) : mix(rgb, rgb, 0); // a pale colour is darkened: text must stay readable
  const warm = rgb[0] > rgb[2];
  return { id: "custom", name: "Ma couleur", primary, secondary: mix(rgb, [0, 0, 0], 0.55), accent: warm ? "#0D9488" : "#F59E0B", light: mix(rgb, [255, 255, 255], 0.92) };
}

/** The palette of a saved cover: one of the list, or the user's own colour. */
export function paletteOf(id: string, custom?: string): Palette {
  return id === "custom" && custom ? customPalette(custom) : PALETTES.find((p) => p.id === id) ?? PALETTES[0];
}

const MONO: Palette = {
  id: "mono", name: "Noir & blanc", primary: "#1F1F1F", secondary: "#000000", accent: "#6B6B6B", light: "#EFEFEF",
};

/** Colors actually used for drawing (black & white mode for cheap printing). */
export function inks(o: RenderOptions): Palette {
  return o.mono ? MONO : o.palette;
}
