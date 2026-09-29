export type DocKind =
  | "rapport_stage"
  | "memoire"
  | "expose"
  | "rapport_projet"
  | "rapport_pro"
  | "autre";

export type StyleId = "officiel" | "moderne" | "corporate" | "minimal" | "bandeau" | "cadre" | "lateral" | "vague";

/** Author (info = matricule) or supervisor (role + info = grade/fonction). */
export type Person = { name: string; role?: string; info?: string };

/** Everything the user typed in the studio form. */
export type CoverForm = {
  kind: DocKind;
  institutionId: string;
  headerFr: string; // one line per level, "" line = separator group break
  headerEn: string;
  showRepublic: boolean;
  showMinistry: boolean;
  logo?: string; // data: URL (university, or the only logo)
  logo2?: string; // second logo: faculty / school, drawn on the other side
  docLabel: string;
  title: string;
  structure: string; // host company (internship) or client (pro)
  period: string;
  degree: string;
  specialty: string;
  authors: Person[];
  supervisors: Person[];
  jury: string;
  place: string;
  year: string;
  date: string;
};

export type Palette = {
  id: string;
  name: string;
  primary: string;
  secondary: string;
  accent: string;
  light: string;
};

/** Normalized content every template knows how to draw. */
export type CoverModel = {
  headerFr: string[][]; // groups of lines, separated by decorative stars
  headerEn: string[][];
  logo?: string;
  logo2?: string;
  org: string; // single-line institution/company name for modern styles
  docLabel: string;
  title: string;
  mention: string[];
  specialty: string;
  authorsLabel: string;
  authors: Person[];
  supervisors: Person[];
  jury: string[];
  footerLeft: string;
  footerRight: string;
  /** True when an academic cover has no institution yet (preview shows an example). */
  headerMissing?: boolean;
  /** Example content shown in the live preview only (never exported). */
  sample: { mention: string[]; supervisors: Person[] };
};

export type RenderOptions = {
  palette: Palette;
  mono: boolean;
  frame: boolean;
};

export const PAGE_W = 595.28;
export const PAGE_H = 841.89;
