"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Ticket } from "@/lib/api";
import { savedAccount } from "@/lib/account";
import { CONTACT } from "./Footer";
import { Field, Input, PinLabel, TextArea } from "./ui";

const KEY = "propre:tickets";

function savedTickets(): string[] {
  try { return JSON.parse(localStorage.getItem(KEY) ?? "[]"); } catch { return []; }
}

function keepTicket(id: string) {
  try { localStorage.setItem(KEY, JSON.stringify([id, ...savedTickets().filter((x) => x !== id)].slice(0, 20))); } catch { /* ignore */ }
}

const when = (ts: number) => new Date(ts * 1000).toLocaleString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

/** Write to the team (both members get it), then follow the conversation here: the link is kept in this browser and on the account. */
export function SupportPage() {
  // Client-only (under Suspense because of useSearchParams): the browser's storage can be read right away.
  const q = useSearchParams();
  const orderId = q.get("commande") ?? "";
  const open = q.get("t");
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [mine, setMine] = useState<Ticket[]>([]);
  const [signedIn] = useState(() => !!savedAccount());
  const [name, setName] = useState("");
  const [contact, setContact] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) api.ticket(open).then((t) => { keepTicket(t.id); setTicket(t); }).catch(() => {});
    Promise.all(savedTickets().map((id) => api.ticket(id).catch(() => null))).then((all) => setMine(all.filter((t): t is Ticket => !!t)));
  }, [open]);

  useEffect(() => {
    if (!ticket) return;
    const t = setInterval(() => api.ticket(ticket.id).then(setTicket).catch(() => {}), 20000); // the answer shows up without reloading
    return () => clearInterval(t);
  }, [ticket?.id]); // eslint-disable-line react-hooks/exhaustive-deps -- one poll per conversation

  async function send() {
    setError("");
    setBusy(true);
    try {
      const t = ticket
        ? await api.ticketAnswer(ticket.id, message)
        : await api.support({ message, name, contact, order_id: orderId, token: savedAccount()?.token });
      keepTicket(t.id);
      setTicket(t);
      setMessage("");
      if (!ticket) setMine((m) => [t, ...m]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (ticket) {
    return (
      <>
        <button type="button" onClick={() => setTicket(null)} className="text-[15px] font-semibold text-ink/60 underline">← Toutes mes demandes</button>
        <ol className="!list-none space-y-3 !pl-0">
          {ticket.messages.map((m, i) => (
            <li key={i} className={`!ml-0 !list-none rounded-md p-3.5 ${m.from === "toi" ? "ml-8 bg-hi/30" : "mr-8 bg-board/10"}`}>
              <p className="text-[12px] font-bold text-ink/55">{m.from === "toi" ? "Toi" : "Équipe Paginya"} · {when(m.ts)}</p>
              <p className="whitespace-pre-wrap">{m.body}</p>
            </li>
          ))}
        </ol>
        {ticket.status === "NEW" && <p className="text-[14px] text-ink/60">Message reçu par l&apos;équipe. La réponse s&apos;affiche ici (garde cette page), et on peut aussi te répondre sur WhatsApp ou par e-mail.</p>}
        {ticket.status === "CLOSED" && <p className="text-[14px] font-semibold text-board">Problème résolu. Tu peux quand même répondre si ce n&apos;est pas le cas.</p>}
        <Field label="Répondre">
          <TextArea rows={3} value={message} onChange={(e) => setMessage(e.target.value)} maxLength={3000} />
        </Field>
        {error && <p className="text-[14px] text-pin">{error}</p>}
        <PinLabel className="w-full" disabled={busy || message.trim().length < 1} onClick={send}>{busy ? "Envoi…" : "Envoyer"}</PinLabel>
      </>
    );
  }

  return (
    <>
      <p>Un paiement passé mais un document toujours bloqué, un pass qui n&apos;apparaît pas, une mise en page bizarre ? Écris-nous : toute l&apos;équipe reçoit ton message et on te répond vite.</p>
      {mine.length > 0 && (
        <ul className="!list-none space-y-2 !pl-0">
          {mine.map((t) => (
            <li key={t.id} className="!ml-0 !list-none">
              <button type="button" onClick={() => setTicket(t)} className="block w-full rounded-md p-3 text-left ring-1 ring-black/10 hover:bg-ink/[0.03]">
                <span className={`text-[13px] font-bold ${t.status === "ANSWERED" ? "text-pen" : "text-ink/55"}`}>
                  {t.status === "NEW" ? "En attente de notre réponse" : t.status === "ANSWERED" ? "On t'a répondu" : "Résolu"}
                </span>
                <span className="block truncate text-[15px]">{t.messages[0]?.body}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="space-y-4">
        <Field label="Ton problème">
          <TextArea rows={4} value={message} onChange={(e) => setMessage(e.target.value)} maxLength={3000} placeholder="Explique ce qui se passe (et le numéro qui a payé, s'il s'agit d'un paiement)." />
        </Field>
        <Field label="Ton nom (facultatif)">
          <Input value={name} onChange={(e) => setName(e.target.value)} maxLength={80} />
        </Field>
        <Field label={signedIn ? "WhatsApp ou e-mail (facultatif : on a celui de ton compte)" : "Ton WhatsApp ou ton e-mail"} hint="Pour te répondre aussi en dehors du site.">
          <Input value={contact} onChange={(e) => setContact(e.target.value)} maxLength={120} placeholder="6 70 00 00 00 ou toi@gmail.com" />
        </Field>
        {orderId && <p className="text-[14px] text-ink/60">Le document concerné est joint à ton message.</p>}
        {error && <p className="text-[14px] text-pin">{error}</p>}
        <PinLabel className="w-full" disabled={busy || message.trim().length < 3 || (!signedIn && contact.trim().length < 6)} onClick={send}>
          {busy ? "Envoi…" : "Envoyer à l'équipe"}
        </PinLabel>
      </div>
      <p className="text-[14px] text-ink/60">Urgent ? WhatsApp {CONTACT.whatsapp}.</p>
    </>
  );
}
