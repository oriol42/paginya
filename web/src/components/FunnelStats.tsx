"use client";

import { useEffect, useState } from "react";
import { ADMIN_KEY, api } from "@/lib/api";

type Row = { day: string; src: string; step: string; n: number };

/** The path from the ad to the payment, in order: where the visitors stop. */
const STEPS: [string, string][] = [
  ["visit", "Visiteurs"],
  ["open_document", "Ouvrent la mise en page"],
  ["open_garde", "Ouvrent la page de garde"],
  ["upload", "Envoient un document"],
  ["pay_open", "Ouvrent le paiement"],
  ["pay_start", "Lancent le paiement"],
  ["paid", "Paient"],
];

/** Team only: visitors per step over the last days, by source (facebook, tiktok, direct…). */
export function FunnelStats() {
  const [days, setDays] = useState(7);
  const [src, setSrc] = useState("");
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let token = "";
    try { token = localStorage.getItem(ADMIN_KEY) ?? ""; } catch { /* ignore */ }
    api.adminFunnel(token, days).then((r) => { setRows(r.rows); setError(""); }).catch((e) => setError((e as Error).message));
  }, [days]);

  const sources = [...new Set((rows ?? []).map((r) => r.src))].sort();
  const count = (step: string) => (rows ?? []).filter((r) => r.step === step && (!src || r.src === src)).reduce((a, r) => a + r.n, 0);
  const visits = count("visit");

  return (
    <section className="mt-8">
      <h2 className="font-display text-[22px] font-black uppercase leading-none">Visiteurs</h2>
      <div className="mt-3 flex flex-wrap gap-2 text-[14px]">
        {[1, 7, 30].map((d) => (
          <button key={d} type="button" onClick={() => setDays(d)}
            className={`rounded-full border px-3 py-1 ${days === d ? "border-ink bg-ink text-paper" : "border-ink/20"}`}>
            {d === 1 ? "Aujourd'hui" : `${d} jours`}
          </button>
        ))}
      </div>
      {sources.length > 1 && (
        <div className="mt-2 flex flex-wrap gap-2 text-[14px]">
          {["", ...sources].map((s) => (
            <button key={s || "all"} type="button" onClick={() => setSrc(s)}
              className={`rounded-full border px-3 py-1 ${src === s ? "border-pen text-pen" : "border-ink/20 text-ink/70"}`}>
              {s || "Toutes sources"}
            </button>
          ))}
        </div>
      )}
      {error && <p className="mt-3 text-[14px] text-pin">{error}</p>}
      {rows === null && !error && <p className="mt-3 text-[14px] text-ink/60">Chargement…</p>}
      {rows && (
        <ol className="mt-4 space-y-2">
          {STEPS.map(([step, label]) => {
            const n = count(step);
            const share = visits ? Math.round((n / visits) * 100) : 0;
            return (
              <li key={step}>
                <div className="flex items-baseline justify-between gap-3 text-[15px]">
                  <span>{label}</span>
                  <span className="tabular font-semibold">{n}{step !== "visit" && visits > 0 && <span className="ml-1 font-normal text-ink/50">({share} %)</span>}</span>
                </div>
                <div className="mt-1 h-1.5 rounded-full bg-ink/10">
                  <div className="h-full rounded-full bg-board" style={{ width: `${visits ? Math.max(n ? 2 : 0, (n / visits) * 100) : 0}%` }} />
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
