"use client";

import { useCallback, useEffect, useState } from "react";
import { ADMIN_KEY, api, formatXaf, type InboxItem, type Thread, type TicketStatus } from "@/lib/api";
import { PLANS, type Plan } from "@/lib/plans";
import { Icon } from "./Icon";
import { Input, PinLabel, Select, TextArea } from "./ui";

const STATUS: Record<TicketStatus, string> = { NEW: "À traiter", ANSWERED: "Répondu", CLOSED: "Résolu" };

const when = (ts: number) => new Date(ts * 1000).toLocaleString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
const who = (author: string) => (author === "client" ? "Client" : author.split("@")[0]);

function token() {
  try { return localStorage.getItem(ADMIN_KEY) ?? ""; } catch { return ""; }
}

/** A WhatsApp or e-mail link to answer outside the site, with the answer already typed. */
function outsideLink(contact: string, text: string): string | null {
  if (contact.includes("@")) return `mailto:${contact}?subject=${encodeURIComponent("Paginya : ta demande")}&body=${encodeURIComponent(text)}`;
  const digits = contact.replace(/\D/g, "").replace(/^(6\d{8})$/, "237$1");
  return digits.length >= 9 ? `https://wa.me/${digits}?text=${encodeURIComponent(text)}` : null;
}

/** Status is a small violet stamp (DESIGN.md: never a coloured badge); a ticket waiting for us gets a pin. */
function StatusStamp({ status }: { status: TicketStatus }) {
  return (
    <span className={`inline-block -rotate-3 rounded-[4px] border-[1.5px] px-1.5 py-px font-display text-[13px] leading-tight font-black tracking-wide uppercase ${status === "CLOSED" ? "border-ink/30 text-ink/45" : "border-stamp text-stamp"}`}>
      {STATUS[status]}
    </span>
  );
}

/** The team's shared inbox: both members see every conversation, who answered, and what is left to do. */
export function SupportInbox({ onWaiting }: { onWaiting?: (n: number) => void }) {
  const [items, setItems] = useState<InboxItem[] | null>(null);
  const [filter, setFilter] = useState<"open" | "all">("open");
  const [thread, setThread] = useState<Thread | null>(null);
  const [reply, setReply] = useState("");
  const [gift, setGift] = useState<{ plan: Plan; days: number }>({ plan: "essentiel", days: 30 });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api.adminInbox(token()).then((r) => {
      setItems(r.tickets);
      onWaiting?.(r.waiting);
      setError("");
    }).catch((e) => setError((e as Error).message));
  }, [onWaiting]);

  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [load]);

  async function act(fn: () => Promise<Thread>) {
    setError("");
    setBusy(true);
    try {
      setThread(await fn());
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const shown = (items ?? []).filter((t) => filter === "all" || t.status !== "CLOSED");
  const answer = reply.trim();
  const outside = thread && outsideLink(thread.contact, answer || "Bonjour, c'est l'équipe Paginya. ");

  return (
    <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
      {/* ---------- List (hidden on phones while a conversation is open) ---------- */}
      <section className={`paper relative rounded-[2px] px-4 pt-7 pb-4 sm:px-5 ${thread ? "hidden lg:block" : ""}`}>
        <span className="pin top-2.5 left-1/2 -translate-x-1/2" aria-hidden />
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-display text-[26px] leading-none font-black uppercase">Messages</h2>
          <div className="flex rounded-md bg-ink/[0.07] p-0.5 text-[14px] font-bold">
            {([["open", "En cours"], ["all", "Tout"]] as const).map(([id, label]) => (
              <button key={id} type="button" onClick={() => setFilter(id)}
                className={`press rounded px-3 py-1.5 ${filter === id ? "bg-paper text-ink shadow-[0_1px_2px_rgba(0,0,0,0.18)]" : "text-ink/55 hover:text-ink"}`}>{label}</button>
            ))}
          </div>
        </div>
        {error && !thread && <p className="mt-3 flex gap-1.5 text-[14px] text-pin"><Icon name="triangle-alert" size={16} className="mt-0.5 shrink-0" />{error}</p>}
        {items === null && !error && <p className="mt-4 flex items-center gap-2 text-[15px] text-ink/60"><Icon name="loader-circle" size={16} className="animate-spin" /> Chargement…</p>}
        {items && shown.length === 0 && (
          <p className="mt-5 mb-2 flex items-center gap-2 text-[15px] text-ink/60"><Icon name="circle-check" size={18} className="text-board" /> Rien à traiter. Tout le monde a sa réponse.</p>
        )}
        <ul className="mt-3 divide-y divide-ink/10 border-t border-ink/10">
          {shown.map((t) => (
            <li key={t.id}>
              <button type="button" onClick={() => act(() => api.adminThread(t.id, token()))}
                className={`press relative block w-full py-3 pr-1 pl-4 text-left hover:bg-ink/[0.03] ${thread?.id === t.id ? "bg-hi/25" : ""}`}>
                {t.status === "NEW" && <span className="absolute top-[18px] left-0.5 h-2 w-2 rounded-full bg-pin shadow-[0_2px_2px_rgba(0,0,0,0.35)]" aria-label="Non traité" />}
                <span className="flex items-baseline justify-between gap-2">
                  <span className={`truncate text-[16px] ${t.status === "NEW" ? "font-bold" : "font-semibold text-ink/80"}`}>{t.name || "Client"}</span>
                  <span className="shrink-0 text-[12px] text-ink/50 tabular-nums">{when(t.updated_at)}</span>
                </span>
                <span className="mt-0.5 block truncate text-[14px] text-ink/65">{who(t.last_author)} : {t.last}</span>
                <span className="mt-1.5 block"><StatusStamp status={t.status} /></span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      {/* ---------- Conversation ---------- */}
      {thread ? (
        <section className="paper relative rounded-[2px] px-4 pt-7 pb-5 sm:px-7">
          <span className="pin top-2.5 left-1/2 -translate-x-1/2" aria-hidden />
          <button type="button" onClick={() => { setThread(null); setReply(""); }}
            className="press -ml-1 inline-flex items-center gap-1 rounded px-1 py-1 text-[15px] font-semibold text-ink/60 hover:text-ink lg:hidden">
            <Icon name="arrow-left" size={17} /> Tous les messages
          </button>
          <div className="mt-1 flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="truncate font-display text-[30px] leading-none font-black uppercase">{thread.name || "Client"}</h2>
              <p className="mt-1.5 text-[14px] break-all text-ink/65">{thread.contact} · depuis le {when(thread.created_at)}</p>
            </div>
            <StatusStamp status={thread.status} />
          </div>

          {(thread.order || thread.account) && (
            <dl className="mt-5 grid gap-x-6 gap-y-3 border-y border-dashed border-ink/20 py-4 text-[14px] sm:grid-cols-2">
              {thread.order && (
                <div>
                  <dt className="text-[12px] font-bold tracking-wide text-ink/50 uppercase">Commande</dt>
                  <dd className="mt-0.5">{thread.order.product.replace(/_/g, " ")} · {formatXaf(thread.order.amount)} · <b>{thread.order.status}</b></dd>
                  {thread.order.phone && <dd className="text-ink/65">Payé avec le {thread.order.phone}{thread.order.trans_id ? ` · ${thread.order.trans_id}` : ""}</dd>}
                  {thread.order.status !== "PAID" && (
                    <dd className="mt-1.5">
                      <button type="button" disabled={busy} className="press rounded-md bg-board px-3 py-2 text-[14px] font-bold text-white hover:bg-board-2 disabled:opacity-50"
                        onClick={() => act(async () => { await api.adminUnlock(thread.order!.id, token()); return api.adminThread(thread.id, token()); })}>
                        Débloquer sans paiement
                      </button>
                    </dd>
                  )}
                </div>
              )}
              {thread.account && (
                <div>
                  <dt className="text-[12px] font-bold tracking-wide text-ink/50 uppercase">Compte</dt>
                  <dd className="mt-0.5 break-all">{thread.account.email}</dd>
                  <dd className="text-ink/65">
                    {thread.account.team ? "Équipe" : thread.account.plan
                      ? `Pass ${PLANS[thread.account.plan].name} · ${thread.account.pass_days} j · ${thread.account.used_today}/${thread.account.per_day || "∞"} aujourd'hui`
                      : "Pas de pass"}
                  </dd>
                  {!thread.account.team && (
                    <dd className="mt-1.5 flex flex-wrap items-center gap-2">
                      <Select aria-label="Formule offerte" value={gift.plan} onChange={(e) => setGift({ ...gift, plan: e.target.value as Plan })} className="w-32">
                        {(Object.keys(PLANS) as Plan[]).map((p) => <option key={p} value={p}>{PLANS[p].name}</option>)}
                      </Select>
                      <Input aria-label="Jours offerts" type="number" min={1} max={366} value={gift.days} onChange={(e) => setGift({ ...gift, days: Number(e.target.value) })} className="!w-20" />
                      <button type="button" disabled={busy} className="press rounded-md bg-board px-3 py-2.5 text-[14px] font-bold text-white hover:bg-board-2 disabled:opacity-50"
                        onClick={() => act(async () => { await api.adminGift(token(), thread.account!.email, gift.plan, gift.days); return api.adminThread(thread.id, token()); })}>
                        Offrir {gift.days} j
                      </button>
                    </dd>
                  )}
                </div>
              )}
            </dl>
          )}

          <ol className="mt-5 space-y-3">
            {thread.messages.map((m, i) => (
              <li key={i} className={`max-w-[85%] rounded-md px-3.5 py-2.5 ${m.author === "client" ? "bg-ink/[0.05]" : "ml-auto bg-[#fff8c9]"}`}>
                <p className={`text-[12px] font-bold ${m.author === "client" ? "text-ink/55" : "text-pen"}`}>{who(m.author)} · {when(m.ts)}</p>
                <p className="mt-0.5 text-[15px] leading-relaxed whitespace-pre-wrap">{m.body}</p>
              </li>
            ))}
          </ol>

          <div className="mt-6">
            <TextArea rows={3} value={reply} onChange={(e) => setReply(e.target.value)} placeholder="Ta réponse : le client la voit sur le site" maxLength={3000} aria-label="Ta réponse" />
            {error && <p className="mt-2 flex gap-1.5 text-[14px] text-pin"><Icon name="triangle-alert" size={16} className="mt-0.5 shrink-0" />{error}</p>}
            <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <PinLabel className="w-full sm:w-auto" disabled={busy || !answer}
                onClick={() => act(async () => { const t = await api.adminReply(thread.id, token(), answer); setReply(""); return t; })}>
                {busy ? "…" : "Répondre"}
              </PinLabel>
              <div className="flex flex-wrap gap-x-5 gap-y-2 text-[15px] font-semibold">
                {outside && (
                  <a href={outside} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-board underline underline-offset-4">
                    <Icon name={thread.contact.includes("@") ? "mail" : "smartphone"} size={16} />
                    {thread.contact.includes("@") ? "Par e-mail" : "Sur WhatsApp"}
                  </a>
                )}
                {thread.status !== "CLOSED" ? (
                  <button type="button" disabled={busy} className="inline-flex items-center gap-1.5 underline underline-offset-4" onClick={() => act(() => api.adminStatus(thread.id, token(), "CLOSED"))}>
                    <Icon name="circle-check" size={16} /> Marquer résolu
                  </button>
                ) : (
                  <button type="button" disabled={busy} className="inline-flex items-center gap-1.5 underline underline-offset-4" onClick={() => act(() => api.adminStatus(thread.id, token(), "NEW"))}>
                    <Icon name="rotate-ccw" size={16} /> Rouvrir
                  </button>
                )}
              </div>
            </div>
          </div>
        </section>
      ) : (
        <section className="hidden min-h-[320px] place-items-center rounded-[2px] border-2 border-dashed border-ink/15 p-8 text-center lg:grid">
          <p className="max-w-[28ch] text-[16px] text-ink/55">Choisis un message à gauche. Ton camarade voit la même boîte et sait qui a répondu.</p>
        </section>
      )}
    </div>
  );
}
