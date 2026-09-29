import { API_URL } from "./api";

export type FormKind = "lettre" | "epreuve";

export type FormView = {
  id: string;
  kind: FormKind;
  status: "DRAFT" | "PENDING" | "PAID" | "FAILED" | "EXPIRED";
  amount: number;
  label: string;
  editable: boolean;
  data: Record<string, unknown>;
  render: { pages: number; version: number } | null;
  total_points?: number;
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

export const forms = {
  create: (kind: FormKind, data: object) => call<FormView>("/forms", { method: "POST", body: JSON.stringify({ kind, data }) }),
  update: (id: string, data: object) => call<FormView>(`/forms/${id}`, { method: "PUT", body: JSON.stringify({ data }) }),
  get: (id: string) => call<FormView>(`/forms/${id}`),
  refresh: (id: string) => call<FormView>(`/forms/${id}/refresh`, { method: "POST" }),
  pageUrl: (id: string, n: number, v: number) => `${API_URL}/forms/${id}/pages/${n}.webp?v=${v}`,
};

export function todayFr(): string {
  return new Date().toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
}
