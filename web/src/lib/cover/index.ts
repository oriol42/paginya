import { compose } from "./kinds";
import { withPlaceholders } from "./templates/common";
import { corporate } from "./templates/corporate";
import { bandeau, cadre, lateral, vague } from "./templates/extra";
import { minimal } from "./templates/minimal";
import { moderne } from "./templates/moderne";
import { bloc, classique, duo, ruban } from "./templates/more";
import { officiel } from "./templates/officiel";
import { setCoverFont } from "./text";
import type { CoverForm, FontId, RenderOptions, StyleId } from "./types";

export const STYLES: { id: StyleId; name: string; hint: string }[] = [
  { id: "officiel", name: "Officiel Cameroun", hint: "Universités, mémoires" },
  { id: "moderne", name: "Moderne", hint: "Exposés, projets" },
  { id: "corporate", name: "Corporate", hint: "Entreprises, PME" },
  { id: "minimal", name: "Élégant", hint: "Sobre, raffiné" },
  { id: "bandeau", name: "Bandeau", hint: "En-tête officiel en couleur" },
  { id: "cadre", name: "Cadre d'honneur", hint: "Bordure classique, mémoires" },
  { id: "lateral", name: "Latéral", hint: "Bande de couleur à gauche" },
  { id: "vague", name: "Vagues", hint: "Moderne et doux" },
  { id: "classique", name: "Classique", hint: "Sobre, tout centré, sans couleur vive" },
  { id: "bloc", name: "Bloc couleur", hint: "Titre sur un grand aplat" },
  { id: "ruban", name: "Rubans", hint: "Coins en couleur, dynamique" },
  { id: "duo", name: "Deux tons", hint: "En-tête clair, pied foncé" },
];

export const FONTS: { id: FontId; name: string; family: string | null }[] = [
  { id: "auto", name: "Celle du modèle", family: null },
  { id: "tinos", name: "Times (classique)", family: "Tinos" },
  { id: "poppins", name: "Poppins (moderne)", family: "Poppins" },
  { id: "playfair", name: "Playfair (élégante)", family: "Playfair Display" },
  { id: "inter", name: "Inter (nette)", family: "Inter" },
];

const RENDERERS = { officiel, moderne, corporate, minimal, bandeau, cadre, lateral, vague, bloc, ruban, classique, duo };

/** preview=true fills empty fields with examples; downloads use preview=false. */
export function renderCover(form: CoverForm, style: StyleId, opts: RenderOptions, preview = true): string {
  const model = compose(form);
  setCoverFont(FONTS.find((f) => f.id === opts.font)?.family ?? null);
  try {
    return RENDERERS[style](preview ? withPlaceholders(model) : model, opts);
  } finally {
    setCoverFont(null);
  }
}

export const FONT_FACES = [
  "400 16px Poppins", "600 16px Poppins", "800 16px Poppins",
  "400 16px Tinos", "700 16px Tinos", "italic 400 16px Tinos",
  "400 16px \"Playfair Display\"", "700 16px \"Playfair Display\"", "italic 400 16px \"Playfair Display\"",
  "400 16px Inter", "600 16px Inter",
];

/** Measurements are only right once the cover fonts are loaded. */
export async function loadCoverFonts(): Promise<void> {
  if (typeof document === "undefined") return;
  await Promise.all(FONT_FACES.map((f) => document.fonts.load(f)));
}
