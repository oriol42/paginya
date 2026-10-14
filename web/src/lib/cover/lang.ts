import type { CoverLang, DocKind } from "./types";

/** English wording of a cover, for English-speaking schools (Buea, Bamenda, anglophone sections). */
const DOC_LABELS: Record<string, string> = {
  "RAPPORT DE STAGE": "INTERNSHIP REPORT", "MÉMOIRE": "DISSERTATION", "EXPOSÉ": "PRESENTATION", "RAPPORT DE PROJET": "PROJECT REPORT",
  "RAPPORT D'ACTIVITÉ": "ACTIVITY REPORT", "DOCUMENT": "DOCUMENT",
};
const AUTHORS: Record<string, string> = {
  "Présenté par :": "Presented by:", "Présenté et soutenu par :": "Presented and defended by:", "Réalisé par :": "Done by:",
  "Préparé par :": "Prepared by:", "Par :": "By:",
};
const ROLES: Record<string, string> = {
  "Encadreur académique": "Academic supervisor", "Encadreur professionnel": "Professional supervisor", "Sous la direction de": "Supervised by",
  "Co-directeur": "Co-supervisor", "Enseignant": "Lecturer", "Encadreur": "Supervisor",
};

export const coverWords = (lang: CoverLang) => ({
  docLabel: (fr: string) => (lang === "en" ? DOC_LABELS[fr] ?? fr : fr),
  authors: (fr: string) => (lang === "en" ? AUTHORS[fr] ?? fr : fr),
  role: (fr: string) => (lang === "en" ? ROLES[fr] ?? fr : fr),
  year: (y: string) => (lang === "en" ? `Academic year ${y}` : `Année académique ${y}`),
  jury: lang === "en" ? "Members of the jury" : "Membres du jury",
  supervisor: lang === "en" ? "Supervisor" : "Encadreur",
  mention(kind: DocKind, f: { structure: string; period: string; degree: string }): string[] {
    const out: string[] = [];
    if (lang === "fr") return out;
    if (kind === "rapport_stage") {
      if (f.structure || f.period) out.push(`Internship carried out ${f.structure ? `at ${f.structure}` : ""} ${f.period}`.replace(/\s+/g, " ").trim());
      if (f.degree) out.push(`Submitted in partial fulfilment of the requirements for the award of ${f.degree}`);
    } else if (kind === "memoire") {
      if (f.degree) out.push(`A dissertation submitted in partial fulfilment of the requirements for the award of ${f.degree}`);
    } else if (kind === "rapport_pro") {
      if (f.structure) out.push(`For the attention of: ${f.structure}`);
    } else if (f.degree) out.push(f.degree);
    return out;
  },
});
