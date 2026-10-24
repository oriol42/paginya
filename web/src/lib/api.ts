import type { Plan } from "./plans";

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
  if (!res.ok) throw Object.assign(new Error(data.detail ?? `Erreur ${res.status}`), { status: res.status });
  return data as T;
}

export const ADMIN_KEY = "propre:admin";

export type Account = {
  token: string; email: string; team: boolean; pass_until: number; pass_days: number;
  /** "" without an active pass */
  plan: Plan | ""; per_day: number; used_today: number;
};

/** NEW: the team's turn to answer · ANSWERED: the customer's turn · CLOSED: solved */
export type TicketStatus = "NEW" | "ANSWERED" | "CLOSED";
export type Ticket = { id: string; status: TicketStatus; created_at: number; messages: { from: "toi" | "paginya"; body: string; ts: number }[] };
export type InboxItem = { id: string; name: string; status: TicketStatus; updated_at: number; last: string; last_author: string };
export type Thread = {
  id: string; name: string; contact: string; status: TicketStatus; created_at: number; order_id: string | null;
  messages: { author: string; body: string; ts: number }[];
  order: { id: string; product: string; amount: number; status: OrderStatus; phone: string | null; trans_id: string | null; created_at: number; paid_at: number | null } | null;
  account: (Omit<Account, "token">) | null;
};

export const api = {
  createOrder: (svg: string, form: unknown, product = "page_de_garde") =>
    call<Order>("/orders", { method: "POST", body: JSON.stringify({ svg, form, product }) }),
  updateOrder: (id: string, svg: string, form: unknown) =>
    call<Order>(`/orders/${id}`, { method: "PUT", body: JSON.stringify({ svg, form }) }),
  getOrder: (id: string) => call<Order>(`/orders/${id}`),
  pay: (id: string, phone: string) =>
    call<Order>(`/orders/${id}/pay`, { method: "POST", body: JSON.stringify({ phone, return_url: `${window.location.origin}/paiement/` }) }),
  /** The team's own documents: after a Google sign-in on the team page, the pass unlocks an order without a payment. */
  adminConfig: () => call<{ client_id: string }>("/admin/config"),
  adminLogin: (credential: string) =>
    call<{ token: string; email: string; account?: Account }>("/admin/login", { method: "POST", body: JSON.stringify({ credential }) }),
  adminFunnel: (token: string, days: number) =>
    call<{ rows: { day: string; src: string; step: string; n: number }[] }>(`/admin/funnel?days=${days}`, { method: "POST", body: JSON.stringify({ token }) }),
  adminUsage: (token: string, days: number) =>
    call<{ rows: { day: string; what: string; n: number }[] }>(`/admin/usage?days=${days}`, { method: "POST", body: JSON.stringify({ token }) }),
  adminUnlock: (id: string, token: string) => call<Order>(`/orders/${id}/admin`, { method: "POST", body: JSON.stringify({ token }) }),
  /** Customer accounts (Google): the 30-day pass, and the team's free documents. */
  accountConfig: () => call<{ client_id: string }>("/account/config"),
  accountGoogle: (credential: string) => call<Account>("/account/google", { method: "POST", body: JSON.stringify({ credential }) }),
  accountMe: (token: string) => call<Omit<Account, "token">>("/account/me", { method: "POST", body: JSON.stringify({ token }) }),
  buyPass: (token: string, plan: Plan) =>
    call<{ id: string; status: OrderStatus; amount: number }>("/account/pass", { method: "POST", body: JSON.stringify({ token, plan }) }),
  unlock: (id: string, token: string) => call<{ id: string; status: OrderStatus }>(`/orders/${id}/unlock`, { method: "POST", body: JSON.stringify({ token }) }),
  prices: () => call<Record<string, { label: string; amount: number; per_day?: number }>>("/prices"),
  /** Support: the customer writes, the team answers from /coulisses. */
  support: (b: { message: string; name?: string; contact?: string; order_id?: string; token?: string }) =>
    call<Ticket>("/support", { method: "POST", body: JSON.stringify(b) }),
  ticket: (id: string) => call<Ticket>(`/support/${id}`),
  ticketAnswer: (id: string, message: string) => call<Ticket>(`/support/${id}/messages`, { method: "POST", body: JSON.stringify({ message }) }),
  myTickets: (token: string) =>
    call<{ id: string; status: TicketStatus; updated_at: number; last: string }[]>("/account/tickets", { method: "POST", body: JSON.stringify({ token }) }),
  adminInbox: (token: string) => call<{ waiting: number; tickets: InboxItem[] }>("/admin/support", { method: "POST", body: JSON.stringify({ token }) }),
  adminThread: (id: string, token: string) => call<Thread>(`/admin/support/${id}`, { method: "POST", body: JSON.stringify({ token }) }),
  adminReply: (id: string, token: string, message: string) =>
    call<Thread>(`/admin/support/${id}/reply`, { method: "POST", body: JSON.stringify({ token, message }) }),
  adminStatus: (id: string, token: string, status: TicketStatus) =>
    call<Thread>(`/admin/support/${id}/status`, { method: "POST", body: JSON.stringify({ token, status }) }),
  adminGift: (token: string, email: string, plan: Plan, days: number) =>
    call<Omit<Account, "token">>("/admin/gift", { method: "POST", body: JSON.stringify({ token, email, plan, days }) }),
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
