import { KINDS, emptyForm } from "@/lib/cover/kinds";
import type { CoverForm, DocKind, StyleId } from "@/lib/cover/types";

export type StudioState = {
  form: CoverForm;
  style: StyleId;
  paletteId: string;
  mono: boolean;
  frame: boolean;
  styleTouched: boolean;
};

export const STORAGE_KEY = "propre:garde:v1";
export const ORDER_KEY = "propre:garde:order";

export function initialState(kind: DocKind = "rapport_stage"): StudioState {
  return {
    form: emptyForm(kind),
    style: KINDS[kind].defaultStyle,
    paletteId: "emeraude",
    mono: false,
    frame: true,
    styleTouched: false,
  };
}

/** Switching document type keeps what the user already typed. */
export function switchKind(s: StudioState, kind: DocKind): StudioState {
  const fresh = emptyForm(kind);
  const def = KINDS[kind];
  const wasAcademic = KINDS[s.form.kind].academic;
  return {
    ...s,
    style: s.styleTouched ? s.style : def.defaultStyle,
    form: {
      ...fresh,
      title: s.form.title,
      authors: s.form.authors,
      year: s.form.year,
      date: s.form.date,
      place: s.form.place,
      logo: s.form.logo,
      structure: s.form.structure,
      degree: s.form.degree,
      specialty: s.form.specialty,
      ...(wasAcademic === def.academic
        ? { institutionId: s.form.institutionId, headerFr: s.form.headerFr, headerEn: s.form.headerEn }
        : {}),
      supervisors: def.supervisorRoles.map((role, i) => ({
        name: s.form.supervisors[i]?.name ?? "",
        info: s.form.supervisors[i]?.info ?? "",
        role,
      })),
    },
  };
}

export function missingFields(s: StudioState): string[] {
  const missing: string[] = [];
  if (!s.form.title.trim()) missing.push("le titre");
  if (!s.form.authors.some((a) => a.name.trim())) missing.push("ton nom");
  if (KINDS[s.form.kind].academic && !s.form.headerFr.trim()) missing.push("l'établissement");
  return missing;
}
