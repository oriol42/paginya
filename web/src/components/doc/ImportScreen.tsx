"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { scans, type ScanResult } from "@/lib/documents";
import { Segmented } from "../ui";

type Props = {
  error: string;
  onText: (text: string) => void;
  onFile: (file: File) => void;
};

type Photo = { file: File; url: string; result?: ScanResult; status: "todo" | "reading" | "done" | "error"; error?: string };

export function ImportScreen({ error, onText, onFile }: Props) {
  const [mode, setMode] = useState<"file" | "photos" | "text">("file");
  const [text, setText] = useState("");
  const [drag, setDrag] = useState(false);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [handwriting, setHandwriting] = useState(false);
  const [consent, setConsent] = useState(false);
  const [reading, setReading] = useState(false);
  const [review, setReview] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;

  function addPhotos(files: FileList | null) {
    if (!files) return;
    const next = [...files].filter((f) => f.type.startsWith("image/")).map((file) => ({ file, url: URL.createObjectURL(file), status: "todo" as const }));
    setPhotos((p) => [...p, ...next].slice(0, 30));
  }

  async function readAll() {
    setReading(true);
    const copy = [...photos];
    for (let i = 0; i < copy.length; i++) {
      if (copy[i].status === "done") continue;
      copy[i] = { ...copy[i], status: "reading" };
      setPhotos([...copy]);
      try {
        copy[i] = { ...copy[i], status: "done", result: await scans.read(copy[i].file, handwriting, consent) };
      } catch (e) {
        copy[i] = { ...copy[i], status: "error", error: (e as Error).message };
      }
      setPhotos([...copy]);
      if (copy[i].status === "error" && /activée|clé|installé/.test(copy[i].error ?? "")) break; // not configured: stop early
    }
    setReading(false);
    if (copy.some((p) => p.status === "done")) setReview(true);
  }

  if (review) {
    const done = photos.filter((p) => p.result);
    return (
      <div className="mx-auto w-full max-w-5xl px-5 pt-6 pb-32">
        <p className="text-sm font-bold tracking-wide text-brand-600 uppercase">Étape de relecture</p>
        <h1 className="mt-1 font-display text-3xl font-extrabold text-ink">Vérifie le texte lu</h1>
        <p className="mt-2 text-slate-600">Compare avec ta photo et corrige les mots mal lus. Paginya ne touchera plus à ton texte ensuite.</p>
        <div className="mt-6 space-y-6">
          {done.map((p, i) => (
            <div key={p.url} className="grid gap-3 rounded-3xl bg-white p-3 ring-1 ring-slate-100 md:grid-cols-2">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={scans.imageUrl(p.result!.id)} alt={`Page ${i + 1}`} className="max-h-[520px] w-full rounded-2xl object-contain" />
              <div className="flex flex-col">
                <p className="mb-2 text-xs font-bold text-slate-500">
                  Page {i + 1} {p.result!.straightened && <span className="ml-1 rounded-full bg-brand-50 px-2 py-0.5 text-brand-700">✓ redressée</span>}
                </p>
                {p.result!.confidence < 70 && (
                  <p className="mb-2 rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800 ring-1 ring-amber-200">
                    Lecture difficile sur cette page : vérifie bien le texte. Si elle est écrite à la main, recommence en cochant « écrites à la main ».
                  </p>
                )}
                <textarea
                  value={p.result!.text}
                  onChange={(e) => setPhotos((all) => all.map((x) => (x.url === p.url ? { ...x, result: { ...x.result!, text: e.target.value } } : x)))}
                  className="min-h-[300px] flex-1 resize-y rounded-2xl bg-slate-50 p-4 text-[15px] leading-relaxed ring-1 ring-slate-200 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-none"
                />
              </div>
            </div>
          ))}
        </div>
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-100 bg-white/95 px-4 pt-3 pb-[max(.75rem,env(safe-area-inset-bottom))] backdrop-blur">
          <div className="mx-auto flex max-w-5xl gap-3">
            <button type="button" onClick={() => setReview(false)} className="rounded-2xl bg-slate-100 px-5 font-bold text-slate-600">←</button>
            <button type="button" onClick={() => onText(done.map((p) => p.result!.text).join("\n\n"))} className="flex-1 rounded-2xl bg-brand-500 py-4 font-display text-lg font-bold text-white shadow-lg shadow-brand-500/25">
              C&apos;est bon, mettre en forme ✨
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-2xl px-5 pt-8 pb-16">
      <p className="text-sm font-bold tracking-wide text-brand-600 uppercase">Mise en forme automatique</p>
      <h1 className="mt-2 font-display text-[2rem] leading-tight font-extrabold text-ink sm:text-4xl">
        Mets ton document <span className="text-brand-500">au propre</span>.
      </h1>
      <p className="mt-3 text-slate-600">Titres, listes, tableaux, sommaire, page de garde… Donne-nous ton texte tel qu&apos;il est, même sans aucune mise en forme.</p>

      <div className="mt-7">
        <Segmented
          value={mode}
          onChange={setMode}
          options={[{ value: "file", label: "📁 Fichier" }, { value: "photos", label: "📷 Photos" }, { value: "text", label: "📋 Texte" }]}
        />
      </div>

      {mode === "file" && (
        <button
          type="button"
          onClick={() => input.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files?.[0]; if (f) onFile(f); }}
          className={`mt-4 flex w-full flex-col items-center justify-center rounded-[28px] border-2 border-dashed px-6 py-14 text-center transition ${drag ? "border-brand-500 bg-brand-50" : "border-slate-300 bg-white hover:border-brand-300 hover:bg-brand-50/40"}`}
        >
          <span className="grid h-16 w-16 place-items-center rounded-2xl bg-brand-50 text-3xl">📄</span>
          <span className="mt-4 font-display text-lg font-bold text-ink">Choisis ton fichier</span>
          <span className="mt-1 text-sm text-slate-500">Word (.docx), PDF ou texte · 15 Mo max</span>
          <span className="mt-5 rounded-full bg-brand-500 px-5 py-2.5 text-sm font-bold text-white shadow-md shadow-brand-500/25">Parcourir</span>
          <input
            ref={input}
            type="file"
            accept=".docx,.pdf,.txt,.md,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/pdf,text/plain"
            className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ""; }}
          />
        </button>
      )}

      {mode === "photos" && (
        <div className="mt-4 space-y-4">
          <div className="grid grid-cols-3 gap-2.5 sm:grid-cols-4">
            {photos.map((p, i) => (
              <div key={p.url} className="relative aspect-[3/4] overflow-hidden rounded-2xl bg-slate-100 ring-1 ring-slate-200">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={p.result ? scans.imageUrl(p.result.id) : p.url} alt={`Page ${i + 1}`} className="h-full w-full object-cover" />
                <span className="absolute top-1.5 left-1.5 rounded-full bg-ink/80 px-2 py-0.5 text-[11px] font-bold text-white">{i + 1}</span>
                {p.status === "reading" && <div className="absolute inset-0 grid place-items-center bg-white/70"><span className="h-8 w-8 animate-spin rounded-full border-4 border-brand-100 border-t-brand-500" /></div>}
                {p.status === "done" && <span className="absolute right-1.5 bottom-1.5 grid h-6 w-6 place-items-center rounded-full bg-brand-500 text-xs font-bold text-white">✓</span>}
                {p.status === "error" && <span className="absolute inset-x-1 bottom-1 rounded-lg bg-red-600/90 px-1.5 py-1 text-[10px] font-semibold text-white">{p.error}</span>}
                {!reading && (
                  <button type="button" onClick={() => setPhotos((all) => all.filter((x) => x.url !== p.url))} className="absolute top-1.5 right-1.5 grid h-6 w-6 place-items-center rounded-full bg-white/90 text-xs" aria-label="Retirer">✕</button>
                )}
              </div>
            ))}
            <label className="flex aspect-[3/4] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-brand-300 bg-brand-50/50 text-center text-sm font-bold text-brand-700">
              <span className="text-2xl">📷</span>
              {photos.length ? "Ajouter" : "Prendre / choisir des photos"}
              <input type="file" accept="image/*" multiple capture="environment" className="hidden" onChange={(e) => { addPhotos(e.target.files); e.target.value = ""; }} />
            </label>
          </div>
          <p className="text-xs text-slate-500">Astuce : pose la feuille sur une table sombre, bien éclairée, et prends toute la page. Paginya la redresse tout seul.</p>
          {photos.length > 0 && (
            <>
              <label className="flex items-center justify-between gap-3 rounded-2xl bg-white p-3.5 text-sm font-medium text-slate-700 ring-1 ring-slate-200">
                <span>✍️ Mes pages sont écrites à la main</span>
                <input type="checkbox" checked={handwriting} onChange={(e) => setHandwriting(e.target.checked)} className="h-5 w-5 accent-[#0E9F6E]" />
              </label>
              {handwriting ? (
                <label className="flex items-start gap-3 rounded-2xl bg-amber-50 p-3.5 text-sm text-slate-700 ring-1 ring-amber-200">
                  <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5 h-5 w-5 accent-[#0E9F6E]" />
                  <span>
                    Pour l&apos;écriture à la main, j&apos;accepte que mes photos soient lues par une intelligence artificielle (Google Gemini, hors du Cameroun).{" "}
                    <Link href="/confidentialite" className="font-semibold text-brand-700 underline">En savoir plus</Link>
                  </span>
                </label>
              ) : (
                <p className="text-xs text-slate-500">🔒 Pages imprimées : lues directement sur nos serveurs, tes photos ne sont envoyées à personne.</p>
              )}
              <button
                type="button"
                disabled={(handwriting && !consent) || reading}
                onClick={readAll}
                className="w-full rounded-2xl bg-brand-500 py-4 font-display text-lg font-bold text-white shadow-lg shadow-brand-500/25 disabled:opacity-40"
              >
                {reading ? `Lecture… ${photos.filter((p) => p.status === "done").length}/${photos.length}` : `Lire ${photos.length} page${photos.length > 1 ? "s" : ""} ✨`}
              </button>
            </>
          )}
        </div>
      )}

      {mode === "text" && (
        <div className="mt-4">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={12}
            placeholder={"Colle ici tout ton texte…\n\nINTRODUCTION\nComme le disait…\n\nCHAPITRE I : PRÉSENTATION\n- premier point\n- deuxième point"}
            className="w-full resize-y rounded-[24px] border-0 bg-white p-5 text-[15px] leading-relaxed ring-1 ring-slate-200 placeholder:text-slate-400 focus:ring-2 focus:ring-brand-500 focus:outline-none"
          />
          <div className="mt-3 flex items-center justify-between gap-3">
            <span className="text-sm text-slate-500">{words ? `${words.toLocaleString("fr-FR")} mots` : ""}</span>
            <button
              type="button"
              disabled={words < 5}
              onClick={() => onText(text)}
              className="rounded-2xl bg-brand-500 px-6 py-3.5 font-display font-bold text-white shadow-lg shadow-brand-500/25 transition hover:bg-brand-600 active:scale-[.98] disabled:opacity-40"
            >
              Mettre en forme ✨
            </button>
          </div>
        </div>
      )}

      {error && <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-100">{error}</p>}

      <p className="mt-5 text-center text-xs text-slate-500">
        En continuant, tu acceptes les <Link href="/cgu" className="underline">conditions d&apos;utilisation</Link> et la{" "}
        <Link href="/confidentialite" className="underline">politique de confidentialité</Link>. Tes fichiers sont supprimés au bout de 7 jours.
      </p>

      <div className="mt-6 grid grid-cols-3 gap-3 text-center text-xs text-slate-500">
        {[
          ["🔒", "Ton texte n'est jamais modifié"],
          ["👀", "Aperçu gratuit de toutes les pages"],
          ["🗑", "Supprimé automatiquement après 7 jours"],
        ].map(([icon, label]) => (
          <div key={label} className="rounded-2xl bg-white/70 p-3 ring-1 ring-slate-100">
            <div className="text-xl">{icon}</div>
            <div className="mt-1 leading-snug">{label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
