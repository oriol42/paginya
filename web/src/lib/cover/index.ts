import { compose } from "./kinds";
import { withPlaceholders } from "./templates/common";
import { corporate } from "./templates/corporate";
import { bandeau, cadre, lateral, vague } from "./templates/extra";
import { minimal } from "./templates/minimal";
import { moderne } from "./templates/moderne";
import { officiel } from "./templates/officiel";
import type { CoverForm, RenderOptions, StyleId } from "./types";

export const STYLES: { id: StyleId; name: string; hint: string }[] = [
  { id: "officiel", name: "Officiel Cameroun", hint: "Universités, mémoires" },
  { id: "moderne", name: "Moderne", hint: "Exposés, projets" },
  { id: "corporate", name: "Corporate", hint: "Entreprises, PME" },
  { id: "minimal", name: "Élégant", hint: "Sobre, raffiné" },
  { id: "bandeau", name: "Bandeau", hint: "En-tête officiel en couleur" },
  { id: "cadre", name: "Cadre d'honneur", hint: "Bordure classique, mémoires" },
  { id: "lateral", name: "Latéral", hint: "Bande de couleur à gauche" },
  { id: "vague", name: "Vagues", hint: "Moderne et doux" },
];

const RENDERERS = { officiel, moderne, corporate, minimal, bandeau, cadre, lateral, vague };

/** preview=true fills empty fields with examples; downloads use preview=false. */
export function renderCover(form: CoverForm, style: StyleId, opts: RenderOptions, preview = true): string {
  const model = compose(form);
  return RENDERERS[style](preview ? withPlaceholders(model) : model, opts);
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
