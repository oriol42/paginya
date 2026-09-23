import { MINISTRY_EN, MINISTRY_FR, REPUBLIC_EN, REPUBLIC_FR, institution } from "../institutions";
import type { CoverForm, CoverModel, DocKind, StyleId } from "./types";

export type FieldKey =
  | "title" | "structure" | "period" | "degree" | "specialty"
  | "authors" | "supervisors" | "jury" | "place" | "year" | "date";

type KindDef = {
  label: string;
  emoji: string;
  docLabel: string;
  defaultStyle: StyleId;
  academic: boolean; // shows the institution picker + bilingual header
  fields: FieldKey[];
  labels: Partial<Record<FieldKey, string>>;
  placeholders: Partial<Record<FieldKey, string>>;
  authorsLabel: string;
  supervisorRoles: string[];
};

export const KINDS: Record<DocKind, KindDef> = {
  rapport_stage: {
    label: "Rapport de stage", emoji: "💼", docLabel: "RAPPORT DE STAGE", defaultStyle: "officiel", academic: true,
    fields: ["title", "structure", "period", "degree", "specialty", "authors", "supervisors", "year", "date"],
    labels: { title: "Thème du rapport", structure: "Structure d'accueil", period: "Période du stage", degree: "Diplôme préparé", specialty: "Filière / option / niveau" },
    placeholders: {
      title: "Ex. : Gestion informatisée des archives de l'entreprise",
      structure: "Ex. : ADVANS Cameroun, agence de Messassi",
      period: "Ex. : du 4 juillet au 4 octobre 2026",
      degree: "Ex. : Licence en Sciences de l'Information et de la Communication",
      specialty: "Ex. : Option Journalisme · Niveau III",
    },
    authorsLabel: "Présenté par :",
    supervisorRoles: ["Encadreur académique", "Encadreur professionnel"],
  },
  memoire: {
    label: "Mémoire", emoji: "🎓", docLabel: "MÉMOIRE", defaultStyle: "officiel", academic: true,
    fields: ["title", "degree", "specialty", "authors", "supervisors", "jury", "year", "date"],
    labels: { title: "Titre du mémoire", degree: "Diplôme", specialty: "Spécialité / option", jury: "Jury (facultatif)" },
    placeholders: {
      title: "Ex. : Intégration didactique des TIC et efficacité pédagogique",
      degree: "Ex. : Master en Sciences de l'Éducation",
      specialty: "Ex. : Spécialité Didactique de l'histoire",
      jury: "Président : …\nRapporteur : …\nExaminateur : …",
    },
    authorsLabel: "Présenté et soutenu par :",
    supervisorRoles: ["Sous la direction de", "Co-directeur"],
  },
  expose: {
    label: "Exposé / devoir", emoji: "📚", docLabel: "EXPOSÉ", defaultStyle: "moderne", academic: true,
    fields: ["title", "specialty", "authors", "supervisors", "date"],
    labels: { title: "Sujet", specialty: "Matière / UE · classe", authors: "Membres du groupe" },
    placeholders: { title: "Ex. : Les énergies renouvelables au Cameroun", specialty: "Ex. : Géographie · Terminale C" },
    authorsLabel: "Présenté par :",
    supervisorRoles: ["Enseignant"],
  },
  rapport_projet: {
    label: "Rapport de projet", emoji: "🛠️", docLabel: "RAPPORT DE PROJET", defaultStyle: "moderne", academic: true,
    fields: ["title", "degree", "specialty", "authors", "supervisors", "year", "date"],
    labels: { title: "Titre du projet", degree: "Cadre (cours, diplôme…)", specialty: "Filière / niveau" },
    placeholders: { title: "Ex. : Application mobile de suivi des cotisations", degree: "Ex. : Projet tutoré de fin de cycle" },
    authorsLabel: "Réalisé par :",
    supervisorRoles: ["Encadreur"],
  },
  rapport_pro: {
    label: "Rapport pro / proposition", emoji: "🏢", docLabel: "RAPPORT D'ACTIVITÉ", defaultStyle: "corporate", academic: false,
    fields: ["title", "structure", "authors", "place", "date"],
    labels: { title: "Titre", structure: "Destinataire / client (facultatif)", authors: "Préparé par", place: "Lieu" },
    placeholders: { title: "Ex. : Bilan des activités 2026", structure: "Ex. : Conseil d'administration", place: "Ex. : Douala" },
    authorsLabel: "Préparé par :",
    supervisorRoles: [],
  },
  autre: {
    label: "Autre document", emoji: "📄", docLabel: "DOCUMENT", defaultStyle: "minimal", academic: false,
    fields: ["title", "authors", "place", "date"],
    labels: { title: "Titre" },
    placeholders: { title: "Ex. : Dossier de candidature" },
    authorsLabel: "Par :",
    supervisorRoles: [],
  },
};

export const DEFAULT_LABELS: Record<FieldKey, string> = {
  title: "Titre", structure: "Structure", period: "Période", degree: "Diplôme", specialty: "Filière",
  authors: "Auteur(s)", supervisors: "Encadreur(s)", jury: "Jury", place: "Lieu",
  year: "Année académique", date: "Date",
};

function groups(lines: string): string[][] {
  // Blank lines split groups (drawn with a separator between them).
  return lines
    .split(/\n\s*\n/)
    .map((g) => g.split("\n").map((l) => l.trim()).filter(Boolean))
    .filter((g) => g.length);
}

export function compose(form: CoverForm): CoverModel {
  const def = KINDS[form.kind];
  const inst = institution(form.institutionId);
  const headerFr: string[][] = [];
  const headerEn: string[][] = [];
  if (def.academic && form.showRepublic) {
    headerFr.push(REPUBLIC_FR);
    headerEn.push(REPUBLIC_EN);
  }
  if (def.academic && form.showMinistry) {
    headerFr.push(MINISTRY_FR);
    headerEn.push(MINISTRY_EN);
  }
  const fr = groups(form.headerFr);
  const en = groups(form.headerEn);
  // Each institution level on its own group so separators appear between levels.
  headerFr.push(...fr.flatMap((g) => g.map((l) => [l])));
  headerEn.push(...en.flatMap((g) => g.map((l) => [l])));

  const mention: string[] = [];
  if (form.kind === "rapport_stage") {
    if (form.structure || form.period)
      mention.push(`Stage effectué ${form.structure ? `à ${form.structure}` : ""} ${form.period}`.replace(/\s+/g, " ").trim());
    if (form.degree) mention.push(`Présenté en vue de l'obtention du diplôme de ${form.degree}`);
  } else if (form.kind === "memoire") {
    if (form.degree) mention.push(`Mémoire présenté et soutenu en vue de l'obtention du diplôme de ${form.degree}`);
  } else if (form.kind === "rapport_pro") {
    if (form.structure) mention.push(`À l'attention de : ${form.structure}`);
  } else if (form.degree) {
    mention.push(form.degree);
  }

  const orgLine = def.academic
    ? (fr[fr.length - 1]?.[fr[fr.length - 1].length - 1] ?? inst.fr[inst.fr.length - 1])
    : (fr.flat()[0] ?? "");

  const yearText = form.year ? `Année académique ${form.year}` : "";
  const dateText = [form.place, form.date].filter(Boolean).join(", ");

  return {
    headerFr,
    headerEn,
    headerMissing: def.academic && !form.headerFr.trim(),
    logo: form.logo,
    org: orgLine,
    docLabel: form.docLabel || def.docLabel,
    title: form.title.trim(),
    mention,
    specialty: form.specialty,
    authorsLabel: def.authorsLabel,
    authors: form.authors.filter((a) => a.name.trim()),
    supervisors: form.supervisors.filter((s) => s.name.trim()),
    jury: form.jury.split("\n").map((l) => l.trim()).filter(Boolean),
    footerLeft: yearText || dateText,
    footerRight: yearText ? dateText : "",
    sample: {
      mention: SAMPLE_MENTION[form.kind],
      supervisors: def.supervisorRoles.map((role) => ({ role, name: "Nom de l'encadreur", info: "Grade / fonction" })),
    },
  };
}

const SAMPLE_MENTION: Record<DocKind, string[]> = {
  rapport_stage: ["Stage effectué à [structure d'accueil] du [date] au [date]", "Présenté en vue de l'obtention du diplôme de [diplôme]"],
  memoire: ["Mémoire présenté et soutenu en vue de l'obtention du diplôme de [Master en …]"],
  expose: ["[Matière] · [Classe]"],
  rapport_projet: ["[Cadre du projet]"],
  rapport_pro: [],
  autre: [],
};

export function emptyForm(kind: DocKind = "rapport_stage"): CoverForm {
  const def = KINDS[kind];
  const inst = institution(def.academic ? "uy1-fs" : "autre");
  return {
    kind,
    institutionId: inst.id,
    headerFr: inst.fr.join("\n"),
    headerEn: inst.en.join("\n"),
    showRepublic: true,
    showMinistry: true,
    docLabel: def.docLabel,
    title: "",
    structure: "",
    period: "",
    degree: "",
    specialty: "",
    authors: [{ name: "", info: "" }],
    supervisors: def.supervisorRoles.map((role) => ({ name: "", role, info: "" })),
    jury: "",
    place: "",
    year: "2025-2026",
    date: "",
  };
}
