"use client";

import { useEffect, useState } from "react";
import { ADMIN_KEY, api, type FlaggedDoc, type LearnStatus } from "@/lib/api";

/** What Paginya learned by itself each night, and the documents it handled badly (they need a new rule). */
const day = (t: number) => new Date(t * 1000).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
const pct = (v: number | null | undefined) => (v == null ? "—" : `${(v * 100).toFixed(1)} %`);

export function LearnStats() {
  const [data, setData] = useState<LearnStatus | null>(null);
  const [error, setError] = useState("");
  const [token] = useState(() => {
    try { return localStorage.getItem(ADMIN_KEY) ?? ""; } catch { return ""; }
  });

  useEffect(() => {
    api.adminLearn(token).then(setData).catch((e) => setError((e as Error).message));
  }, [token]);

  const reviewed = (d: FlaggedDoc) => {
    api.adminLearnReviewed(d.id, token).then(() => setData((x) => x && { ...x, docs: x.docs.map((y) => (y.id === d.id ? { ...y, reviewed: 1 } : y)) }))
      .catch((e) => setError((e as Error).message));
  };
  const download = async (d: FlaggedDoc) => {
    try {
      const url = URL.createObjectURL(await api.adminLearnFile(d.id, token));
      const a = Object.assign(document.createElement("a"), { href: url, download: `paginya-${d.id.slice(0, 8)}` });
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const last = data?.history.at(-1);
  const waiting = data?.docs.filter((d) => !d.reviewed) ?? [];

  return (
    <section className="mt-10 border-t border-dashed border-ink/20 pt-6">
      <h2 className="font-display text-[22px] leading-none font-black uppercase">Apprentissage</h2>
      {error && <p className="mt-3 text-[14px] text-pin">{error}</p>}
      {data === null && !error && <p className="mt-3 text-[14px] text-ink/60">Chargement…</p>}
      {data && (
        <>
          <p className="mt-3 max-w-2xl text-[14px] text-ink/70">
            Chaque nuit, Paginya apprend des plans que les clients ont corrigés avant de payer. Un nouveau modèle ne remplace
            l&apos;ancien que s&apos;il fait au moins aussi bien partout.
          </p>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Documents appris" value={String(data.samples)} />
            <Stat label="Dernière nuit" value={last ? day(last.at) : "—"} />
            <Stat label="Résultat" value={last ? (last.accepted ? "Modèle amélioré" : "Inchangé") : "—"} />
            <Stat label="Modèle actuel" value={data.learned_model && data.model_date ? `appris le ${day(data.model_date)}` : "celui d'origine"} />
          </div>
          {last && !last.accepted && last.why && <p className="mt-2 text-[13px] text-ink/55">Pourquoi : {last.why}.</p>}
          {last?.real?.[1] != null && (
            <p className="mt-2 text-[13px] text-ink/55">
              Justesse sur des documents réels jamais vus : {pct(last.real[0])} → {pct(last.real[1])} · documents de référence : {pct(last.corpus?.[0])} → {pct(last.corpus?.[1])}
            </p>
          )}

          <h3 className="mt-7 font-display text-[18px] leading-none font-black uppercase">À regarder ({waiting.length})</h3>
          <p className="mt-2 max-w-2xl text-[13px] text-ink/55">
            Documents que le moteur a mal compris : ils demandent une nouvelle règle. Le fichier n&apos;est gardé que si le client l&apos;a accepté.
          </p>
          {data.docs.length === 0 ? (
            <p className="mt-3 text-[14px] text-ink/60">Rien pour l&apos;instant.</p>
          ) : (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-[14px]">
                <thead className="text-[12px] font-bold tracking-wide text-ink/50 uppercase">
                  <tr><th className="pb-2">Date</th><th className="pb-2">Ce qui cloche</th><th className="pb-2 text-right">Corrections</th><th className="pb-2" /></tr>
                </thead>
                <tbody className="divide-y divide-ink/10">
                  {data.docs.map((d) => (
                    <tr key={d.id} className={d.reviewed ? "text-ink/40" : ""}>
                      <td className="py-2.5 pr-3 align-top whitespace-nowrap">{day(d.created_at)}<span className="block text-[12px] text-ink/50">{d.kind || "document"} · {d.words} mots</span></td>
                      <td className="py-2.5 pr-3 align-top">{d.reasons.join(" · ") || "fichier gardé"}</td>
                      <td className="py-2.5 pr-3 text-right align-top tabular-nums">{d.corrections < 0 ? "—" : d.corrections}</td>
                      <td className="py-2.5 text-right align-top whitespace-nowrap">
                        {d.has_file ? <button type="button" onClick={() => download(d)} className="press mr-2 font-semibold text-board underline">Fichier</button> : null}
                        {!d.reviewed && <button type="button" onClick={() => reviewed(d)} className="press font-semibold text-ink/60 underline">Vu</button>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-wall/60 p-3 ring-1 ring-ink/10">
      <span className="block text-[12px] font-bold tracking-wide text-ink/50 uppercase">{label}</span>
      <span className="mt-1 block font-display text-[19px] leading-tight font-black">{value}</span>
    </div>
  );
}
