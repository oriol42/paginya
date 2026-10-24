"use client";

import { useCallback, useEffect, useState } from "react";
import { ADMIN_KEY, api, formatXaf, type InboxItem, type Thread, type TicketStatus } from "@/lib/api";
import { PLANS, type Plan } from "@/lib/plans";
import { Icon } from "./Icon";
import { Input, PinLabel, Select, TextArea } from "./ui";

const STATUS: Record<TicketStatus, [string, string]> = {
  NEW: ["À traiter", "bg-pin text-white"],
  ANSWERED: ["Répondu", "bg-hi text-ink"],
  CLOSED: ["Résolu", "bg-ink/10 text-ink/60"],
};

const when = (ts: number) => new Date(ts * 1000).toLocaleString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
const who = (author: string) => (author === "client" ? "Client" : author.split("@")[0]);

function token() {
  try { return localStorage.getItem(ADMIN_KEY) ?? ""; } catch { return ""; }
}

/** A WhatsApp or e-mail link to answer outside the site, with the answer already typed. */
function outsideLink(contact: string, text: string): string | null {
  if (contact.includes("@")) return `mailto:${contact}?subject=${encodeURIComponent("Paginya : ta demande")}&body=${encodeURIComponent(text)}`;
  const digits = contact.replace(/\D/g, "").replace(/^(?!237)(6\d{8})$/, "237$1");
  return digits.length >= 9 ? `https://wa.me/${digits}?text=${encodeURIComponent(text)}` : null;
}

/** The team's shared inbox: both members see every conversation, who answered, and what is left to do. */
export function SupportInbox() {
  const [items, setItems] = useState<InboxItem[] | null>(null);
  const [filter, setFilter] = useState<"open" | "all">("open");
  const [thread, setThread] = useState<Thread | null>(null);
  const [reply, setReply] = useState("");
  const [gift, setGift] = useState<{ plan: Plan; days: number }>({ plan: "essentiel", days: 30 });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api.adminInbox(token()).then((r) => { setItems(r.tickets); setError(""); }).catch((e) => setError((e as Error).message));
  }, []);

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

  const open = (id: string) => act(() => api.adminThread(id, token()));

  if (thread) {
    const answer = reply.trim();
    const outside = outsideLink(thread.contact, answer || "Bonjour, c'est l'équipe Paginya. ");
    return (
      <section className="mt-8 space-y-4">
        <button type="button" onClick={() => { setThread(null); setReply(""); }} className="text-[15px] font-semibold text-ink/60 underline">← Tous les messages</button>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-[22px] leading-none font-black uppercase">{thread.name || "Client"}</h2>
            <p className="mt-1 text-[14px] text-ink/65">{thread.contact} · {when(thread.created_at)}</p>
          </div>
          <span className={`shrink-0 rounded px-2 py-1 text-[12px] font-bold ${STATUS[thread.status][1]}`}>{STATUS[thread.status][0]}</span>
        </div>

        {thread.order && (
          <div className="rounded-md bg-ink/[0.04] p-3 text-[14px]">
            <p><b>Commande</b> {thread.order.product} · {formatXaf(thread.order.amount)} · <b>{thread.order.status}</b></p>
            {thread.order.phone && <p>Payé avec le {thread.order.phone}{thread.order.trans_id ? ` · Fapshi ${thread.order.trans_id}` : ""}</p>}
            {thread.order.status !== "PAID" && (
              <button type="button" disabled={busy} className="mt-2 font-bold text-board underline"
                onClick={() => act(async () => { await api.adminUnlock(thread.order!.id, token()); return api.adminThread(thread.id, token()); })}>
                Débloquer ce document sans paiement
              </button>
            )}
          </div>
        )}
        {thread.account && (
          <div className="rounded-md bg-ink/[0.04] p-3 text-[14px]">
            <p><b>Compte</b> {thread.account.email}</p>
            <p>{thread.account.team ? "Équipe" : thread.account.plan ? `Pass ${PLANS[thread.account.plan].name} · ${thread.account.pass_days} j · ${thread.account.used_today}/${thread.account.per_day || "∞"} aujourd'hui` : "Pas de pass"}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Select value={gift.plan} onChange={(e) => setGift({ ...gift, plan: e.target.value as Plan })} className="w-36">
                {(Object.keys(PLANS) as Plan[]).map((p) => <option key={p} value={p}>{PLANS[p].name}</option>)}
              </Select>
              <Input type="number" min={1} max={366} value={gift.days} onChange={(e) => setGift({ ...gift, days: Number(e.target.value) })} className="!w-20" />
              <button type="button" disabled={busy} className="font-bold text-board underline"
                onClick={() => act(async () => { await api.adminGift(token(), thread.account!.email, gift.plan, gift.days); return api.adminThread(thread.id, token()); })}>
                Offrir ces jours
              </button>
            </div>
          </div>
        )}

        <ol className="space-y-2">
          {thread.messages.map((m, i) => (
            <li key={i} className={`rounded-md p-3 ${m.author === "client" ? "mr-8 bg-ink/[0.05]" : "ml-8 bg-board/10"}`}>
              <p className="text-[12px] font-bold text-ink/55">{who(m.author)} · {when(m.ts)}</p>
              <p className="whitespace-pre-wrap text-[15px]">{m.body}</p>
            </li>
          ))}
        </ol>

        <TextArea rows={3} value={reply} onChange={(e) => setReply(e.target.value)} placeholder="Ta réponse (le client la voit sur le site)" maxLength={3000} />
        {error && <p className="text-[14px] text-pin">{error}</p>}
        <PinLabel className="w-full" disabled={busy || !answer} onClick={() => act(async () => { const t = await api.adminReply(thread.id, token(), answer); setReply(""); return t; })}>
          Répondre
        </PinLabel>
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-[15px] font-semibold">
          {outside && <a href={outside} target="_blank" rel="noreferrer" className="text-board underline">{thread.contact.includes("@") ? "Répondre par e-mail" : "Répondre sur WhatsApp"}</a>}
          {thread.status !== "CLOSED" ? (
            <button type="button" disabled={busy} className="underline" onClick={() => act(() => api.adminStatus(thread.id, token(), "CLOSED"))}>Marquer résolu</button>
          ) : (
            <button type="button" disabled={busy} className="underline" onClick={() => act(() => api.adminStatus(thread.id, token(), "NEW"))}>Rouvrir</button>
          )}
        </div>
      </section>
    );
  }

  const shown = (items ?? []).filter((t) => filter === "all" || t.status !== "CLOSED");
  const waiting = (items ?? []).filter((t) => t.status === "NEW").length;
  return (
    <section className="mt-8">
      <h2 className="flex items-center gap-2 font-display text-[22px] leading-none font-black uppercase">
        Support {waiting > 0 && <span className="rounded-full bg-pin px-2 py-0.5 font-sans text-[13px] text-white">{waiting}</span>}
      </h2>
      <div className="mt-3 flex gap-2 text-[14px]">
        {([["open", "En cours"], ["all", "Tout"]] as const).map(([id, label]) => (
          <button key={id} type="button" onClick={() => setFilter(id)}
            className={`rounded-full border px-3 py-1 ${filter === id ? "border-ink bg-ink text-paper" : "border-ink/20"}`}>{label}</button>
        ))}
      </div>
      {error && <p className="mt-3 text-[14px] text-pin">{error}</p>}
      {items === null && !error && <p className="mt-3 text-[14px] text-ink/60">Chargement…</p>}
      {items && shown.length === 0 && <p className="mt-3 flex items-center gap-2 text-[15px] text-ink/60"><Icon name="circle-check" size={18} /> Rien à traiter.</p>}
      <ul className="mt-3 space-y-2">
        {shown.map((t) => (
          <li key={t.id}>
            <button type="button" onClick={() => open(t.id)} className="block w-full rounded-md p-3 text-left ring-1 ring-black/10 hover:bg-ink/[0.03]">
              <span className="flex items-center justify-between gap-2">
                <span className="truncate font-bold">{t.name || "Client"}</span>
                <span className={`shrink-0 rounded px-2 py-0.5 text-[11px] font-bold ${STATUS[t.status][1]}`}>{STATUS[t.status][0]}</span>
              </span>
              <span className="block truncate text-[14px] text-ink/70">{who(t.last_author)} : {t.last}</span>
              <span className="block text-[12px] text-ink/50">{when(t.updated_at)}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
