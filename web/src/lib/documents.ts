import { API_URL } from "./api";

export type BlockType = "heading" | "paragraph" | "list" | "table" | "figure" | "caption" | "source" | "quote" | "code" | "title";

export type Block = {
  id: number;
  type: BlockType;
  text?: string;
  level?: number;
  ordered?: boolean;
  rows?: string[][];
  image?: string;
  of?: "table" | "figure";
  special?: string;
  role?: string;
  term?: string;
  definition?: string;
  part?: boolean;
  sub?: boolean;
  hidden?: boolean;
};

export type ThemeId = "academique" | "universitaire" | "moderne" | "elegant" | "corporate" | "simple";

export type DocStyle = {
  theme: ThemeId;
  font?: string | null;
  size?: number | null;
  line?: number | null;
  justify?: boolean | null;
  margins?: number[];
  color?: string;
};

export type DocOptions = { toc: boolean; toc_end: boolean; lists: boolean; cover: boolean; page_numbers: boolean; chapter_pages?: boolean; letterhead?: boolean };
export type Letterhead = { fr: string[][]; en: string[][]; logo?: string | null; institutionId?: string };

export type DocMeta = {
  kind: string;
  words: number;
  headings: number;
  tables: number;
  figures: number;
  lists: number;
  title?: string;
  changes?: string[];
  /** Read from the student's own cover page (hidden from the text, used to fill Paginya's cover). */
  cover?: DocCoverInfo;
};

export type DocCoverInfo = {
  header_fr?: string[];
  header_en?: string[];
  title?: string;
  doc_label?: string;
  authors?: { name: string; info?: string }[];
  supervisors?: { name: string; role?: string; info?: string }[];
  matricule?: string;
  year?: string;
  degree?: string;
  specialty?: string;
  structure?: string;
  period?: string;
};

export type DocView = {
  id: string;
  status: "DRAFT" | "PENDING" | "PAID" | "FAILED" | "EXPIRED";
  product: string;
  label: string;
  amount: number;
  editable: boolean;
  blocks: Block[];
  meta: DocMeta;
  style: DocStyle;
  options: DocOptions;
  has_cover: boolean;
  letterhead?: Letterhead | null;
  render: { pages: number; version: number; stale?: boolean } | null;
};

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) } });
  } catch {
    throw new Error("Connexion impossible. Vérifie ta connexion internet et réessaie.");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? `Erreur ${res.status}`);
  return data as T;
}

function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] ?? "");
    reader.onerror = () => reject(new Error("Lecture du fichier impossible"));
    reader.readAsDataURL(file);
  });
}

export const docs = {
  fromText: (text: string) => call<DocView>("/documents", { method: "POST", body: JSON.stringify({ text }) }),
  fromFile: async (file: File) =>
    call<DocView>("/documents", { method: "POST", body: JSON.stringify({ filename: file.name, data: await toBase64(file) }) }),
  get: (id: string) => call<DocView>(`/documents/${id}`),
  update: (id: string, patch: Partial<{ blocks: Block[]; style: DocStyle; options: DocOptions; kind: string; letterhead: Letterhead; cover_svg: string; remove_cover: boolean }>) =>
    call<DocView>(`/documents/${id}`, { method: "PUT", body: JSON.stringify(patch) }),
  render: (id: string) => call<DocView>(`/documents/${id}/render`, { method: "POST" }),
  pageUrl: (id: string, n: number, version: number) => `${API_URL}/documents/${id}/pages/${n}.webp?v=${version}`,
  before: (id: string) => call<{ pages: number }>(`/documents/${id}/before`, { method: "POST" }),
  beforeUrl: (id: string, n: number) => `${API_URL}/documents/${id}/before/${n}.webp`,
  remove: (id: string) => call<{ deleted: boolean }>(`/documents/${id}`, { method: "DELETE" }),
};

export type ScanResult = { id: string; text: string; straightened: boolean; engine: string; confidence: number };

/** Resize/compress on the phone before upload (saves mobile data). */
export async function compressPhoto(file: File, maxSide = 2000): Promise<string> {
  const url = URL.createObjectURL(file);
  try {
    const img = new Image();
    img.src = url;
    await img.decode();
    const scale = Math.min(1, maxSide / Math.max(img.width, img.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(img.width * scale);
    canvas.height = Math.round(img.height * scale);
    canvas.getContext("2d")!.drawImage(img, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.85).split(",", 2)[1];
  } finally {
    URL.revokeObjectURL(url);
  }
}

export const scans = {
  read: async (file: File, handwriting: boolean, consent: boolean) =>
    call<ScanResult>("/scans", { method: "POST", body: JSON.stringify({ data: await compressPhoto(file), handwriting, consent }) }),
  imageUrl: (id: string) => `${API_URL}/scans/${id}.jpg`,
};

export const THEMES: { id: ThemeId; name: string; hint: string }[] = [
  { id: "academique", name: "Académique", hint: "Normes, noir" },
  { id: "universitaire", name: "Universitaire", hint: "Normes + couleur" },
  { id: "moderne", name: "Moderne", hint: "Titres en couleur" },
  { id: "elegant", name: "Élégant", hint: "Petites capitales" },
  { id: "corporate", name: "Corporate", hint: "Bandeaux colorés" },
  { id: "simple", name: "Simple", hint: "Sobre, Arial" },
];

export const KIND_LABEL: Record<string, string> = {
  memoire: "Mémoire",
  rapport_stage: "Rapport de stage",
  rapport: "Rapport",
  expose: "Exposé / devoir",
  cours: "Cours / notes",
  administratif: "Lettre / administratif",
  document: "Document",
};

/** What the user can pick; each type only adds the pages it really has (the API sets the defaults). */
export const KINDS: { id: string; label: string; hint: string }[] = [
  { id: "document", label: "Document simple", hint: "Texte mis en forme, rien d'ajouté" },
  { id: "cours", label: "Cours / notes", hint: "Titre en haut, pas de sommaire" },
  { id: "expose", label: "Exposé / devoir", hint: "Page de garde, pas de sommaire" },
  { id: "administratif", label: "Lettre / administratif", hint: "Une page propre, sans numéros" },
  { id: "rapport", label: "Rapport", hint: "Page de garde + sommaire" },
  { id: "rapport_stage", label: "Rapport de stage", hint: "Normes complètes (sommaire, table…)" },
  { id: "memoire", label: "Mémoire", hint: "Normes complètes (sommaire, table…)" },
];
