"use client";

import { useEffect, useState } from "react";
import { ADMIN_KEY, api } from "@/lib/api";

/** What the server did (AI calls, photos, renders), against the free quotas: tells the team when to pay for more. */
const LINES: [string, (w: string) => boolean, string][] = [
  ["Pages manuscrites lues par l'IA", (w) => w.startsWith("ia:") && !w.startsWith("ia:orthographe"), "Gratuit : Gemini puis Groq en secours (Groq : 1 000 / jour)"],
  ["Appels de correction des fautes", (w) => w.startsWith("ia:orthographe"), "Un appel par tranche d'environ 1 000 mots"],
  ["Lectures IA ratées", (w) => w === "ia_echec", "Si ça monte : quota atteint, il faut une clé payante"],
  ["Photos imprimées lues", (w) => w === "ocr", "Sur notre serveur (Tesseract), sans limite"],
  ["Mises en page", (w) => w === "rendu", "Sur notre serveur (LibreOffice), environ 40 s chacune"],
];

export function UsageStats() {
  const [rows, setRows] = useState<{ day: string; what: string; n: number }[] | null>(null);
  const [today] = useState(() => new Date(Date.now() + 3600_000).toISOString().slice(0, 10)); // Cameroon day (UTC+1)
  const [error, setError] = useState("");

  useEffect(() => {
    let token = "";
    try { token = localStorage.getItem(ADMIN_KEY) ?? ""; } catch { /* ignore */ }
    api.adminUsage(token, 30).then((r) => setRows(r.rows)).catch((e) => setError((e as Error).message));
  }, []);

  const sum = (match: (w: string) => boolean, onlyToday: boolean) =>
    (rows ?? []).filter((r) => match(r.what) && (!onlyToday || r.day === today)).reduce((a, r) => a + r.n, 0);
  const peak = (match: (w: string) => boolean) => {
    const byDay: Record<string, number> = {};
    for (const r of rows ?? []) if (match(r.what)) byDay[r.day] = (byDay[r.day] ?? 0) + r.n;
    return Math.max(0, ...Object.values(byDay));
  };

  return (
    <section className="mt-10 border-t border-dashed border-ink/20 pt-6">
      <h2 className="font-display text-[22px] leading-none font-black uppercase">Machine</h2>
      {error && <p className="mt-3 text-[14px] text-pin">{error}</p>}
      {rows === null && !error && <p className="mt-3 text-[14px] text-ink/60">Chargement…</p>}
      {rows && (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[480px] text-left text-[14px]">
            <thead className="text-[12px] font-bold tracking-wide text-ink/50 uppercase">
              <tr><th className="pb-2 font-bold">Quoi</th><th className="pb-2 text-right">Aujourd&apos;hui</th><th className="pb-2 text-right">Pire jour</th><th className="pb-2 text-right">30 jours</th></tr>
            </thead>
            <tbody className="divide-y divide-ink/10">
              {LINES.map(([label, match, note]) => (
                <tr key={label}>
                  <td className="py-2.5 pr-3"><span className="font-semibold">{label}</span><span className="block text-[12px] text-ink/55">{note}</span></td>
                  <td className="py-2.5 text-right font-display text-[22px] font-black tabular-nums">{sum(match, true)}</td>
                  <td className="py-2.5 text-right tabular-nums">{peak(match)}</td>
                  <td className="py-2.5 text-right tabular-nums">{sum(match, false)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
