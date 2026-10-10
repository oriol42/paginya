export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type OrderStatus = "DRAFT" | "PENDING" | "PAID" | "FAILED" | "EXPIRED";

export type Order = {
  id: string;
  product: string;
  label: string;
  amount: number;
  status: OrderStatus;
  form: Record<string, unknown>;
  editable: boolean;
  is_document?: boolean;
  /** Fapshi payment page, when the payment is not confirmed on the phone directly. */
  pay_link?: string | null;
};

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new Error("Connexion impossible. Vérifie ta connexion internet et réessaie.");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? `Erreur ${res.status}`);
  return data as T;
}

export const ADMIN_KEY = "propre:admin";

export const api = {
  createOrder: (svg: string, form: unknown, product = "page_de_garde") =>
    call<Order>("/orders", { method: "POST", body: JSON.stringify({ svg, form, product }) }),
  updateOrder: (id: string, svg: string, form: unknown) =>
    call<Order>(`/orders/${id}`, { method: "PUT", body: JSON.stringify({ svg, form }) }),
  getOrder: (id: string) => call<Order>(`/orders/${id}`),
  pay: (id: string, phone: string) =>
    call<Order>(`/orders/${id}/pay`, { method: "POST", body: JSON.stringify({ phone, return_url: `${window.location.origin}/paiement/` }) }),
  /** The team's own documents: the admin code (saved on /admin) unlocks the order without a payment. */
  adminCheck: (code: string) => call<{ ok: boolean }>("/admin/check", { method: "POST", body: JSON.stringify({ code }) }),
  adminUnlock: (id: string, code: string) => call<Order>(`/orders/${id}/admin`, { method: "POST", body: JSON.stringify({ code }) }),
  retry: (id: string) => call<Order>(`/orders/${id}/retry`, { method: "POST" }),
  fileUrl: (id: string, fmt: "pdf" | "docx" | "png") => `${API_URL}/orders/${id}/file.${fmt}`,
};

/** Best-effort operator guess from the prefix (Fapshi also auto-detects). */
export function operatorOf(phone: string): "MTN MoMo" | "Orange Money" | null {
  const d = phone.replace(/\D/g, "").replace(/^237/, "");
  if (d.length < 3) return null;
  const p2 = Number(d.slice(0, 2));
  const p3 = Number(d.slice(0, 3));
  if (p2 === 67 || (p3 >= 650 && p3 <= 654) || (p3 >= 680 && p3 <= 689)) return "MTN MoMo";
  if (p2 === 69 || (p3 >= 655 && p3 <= 659) || p3 === 640) return "Orange Money";
  return null;
}

export function formatXaf(n: number): string {
  return `${n.toLocaleString("fr-FR").replace(/ /g, " ")} F`;
}
