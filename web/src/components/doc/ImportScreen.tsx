"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { KIND_LABEL, scans, type ScanResult } from "@/lib/documents";
import { forget, recents, type Recent } from "@/lib/recents";
import { Icon, type IconName } from "../Icon";
import { PinLabel } from "../ui";

type Props = {
  error: string;
  onText: (text: string) => void;
  onFile: (file: File) => void;
  /** Reopen a document from this phone's recent list. */
  onOpen: (id: string) => void;
};

type Photo = { file: File; url: string; result?: ScanResult; status: "todo" | "reading" | "done" | "error"; error?: string };

export function ImportScreen({ error, onText, onFile, onOpen }: Props) {
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
        <h1 className="font-display text-[2.4rem] leading-[0.95] font-black uppercase">Vérifie le texte lu</h1>
        <p className="mt-2 max-w-prose text-[16px] text-ink/70">Compare avec ta photo et corrige les mots mal lus. Paginya ne touchera plus à ton texte ensuite.</p>
        <div className="mt-6 space-y-6">
          {done.map((p, i) => (
            <div key={p.url} className="paper grid gap-3 rounded-[2px] p-3 md:grid-cols-2">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={scans.imageUrl(p.result!.id)} alt={`Page ${i + 1}`} className="max-h-[520px] w-full object-contain" />
              <div className="flex flex-col">
                <p className="mb-2 flex items-center gap-2 text-[13px] font-bold text-ink/60">
                  Page {i + 1}
                  {p.result!.straightened && <span className="stamp text-[13px]">Redressée</span>}
                </p>
                {p.result!.confidence < 70 && (
                  <p className="mb-2 flex gap-2 rounded-md bg-hi/40 px-3 py-2 text-[14px] text-ink">
                    <Icon name="triangle-alert" size={18} className="mt-0.5" />
                    Lecture difficile sur cette page : vérifie bien le texte. Si elle est écrite à la main, recommence en cochant « écrites à la main ».
                  </p>
                )}
                <textarea
                  value={p.result!.text}
                  onChange={(e) => setPhotos((all) => all.map((x) => (x.url === p.url ? { ...x, result: { ...x.result!, text: e.target.value } } : x)))}
                  className="min-h-[300px] flex-1 resize-y rounded-md bg-wall/60 p-4 text-[16px] leading-relaxed ring-1 ring-black/10 focus:bg-paper focus:ring-2 focus:ring-hi-deep focus:outline-none"
                />
              </div>
            </div>
          ))}
        </div>
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-black/10 bg-paper/95 px-4 pt-3 pb-[max(.75rem,env(safe-area-inset-bottom))] backdrop-blur">
          <div className="mx-auto flex max-w-5xl gap-3">
            <button type="button" onClick={() => setReview(false)} className="press grid w-14 place-items-center rounded-md ring-1 ring-black/15" aria-label="Retour">
              <Icon name="arrow-left" />
            </button>
            <PinLabel className="flex-1" onClick={() => onText(done.map((p) => p.result!.text).join("\n\n"))}>
              C&apos;est bon, mettre en forme
            </PinLabel>
          </div>
        </div>
      </div>
    );
  }

  const TABS: { value: typeof mode; label: string; icon: IconName }[] = [
    { value: "file", label: "Fichier", icon: "file-up" },
    { value: "photos", label: "Photos", icon: "camera" },
    { value: "text", label: "Texte", icon: "clipboard-paste" },
  ];

  return (
    <div className="flex flex-1 flex-col">
      <section className="board px-5 pt-8 pb-24">
        <div className="mx-auto max-w-2xl">
          <h1 className="rise font-display text-[2.8rem] leading-[0.9] font-black uppercase sm:text-[3.6rem]">
            Dépose ton document,<br />
            on le <span className="hi text-ink">met au propre</span>.
          </h1>
          <p className="mt-4 max-w-md text-[16px] text-white/75">Tel qu&apos;il est, même sans aucune mise en forme. Tu vois le résultat gratuitement.</p>
        </div>
      </section>

      <div className="mx-auto -mt-16 w-full max-w-2xl px-4 pb-14">
        <div className="paper pin-in relative rounded-[2px] px-4 pt-9 pb-5 sm:px-7" style={{ animationDelay: "60ms" }}>
          <span className="pin top-3 left-1/2 -translate-x-1/2" aria-hidden />
          <div role="tablist" className="grid grid-cols-3 gap-1.5 border-b border-black/10 pb-3">
            {TABS.map((t) => (
              <button
                key={t.value}
                type="button"
                role="tab"
                aria-selected={mode === t.value}
                onClick={() => setMode(t.value)}
                className={`press flex flex-col items-center gap-1 rounded-md py-2.5 text-[15px] font-bold transition-colors sm:flex-row sm:justify-center sm:gap-2 ${mode === t.value ? "bg-board text-white" : "text-ink/60 hover:bg-ink/5 hover:text-ink"}`}
              >
                <Icon name={t.icon} size={20} />
                {t.label}
              </button>
            ))}
          </div>

          {mode === "file" && (
            <button
              type="button"
              onClick={() => input.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
              onDragLeave={() => setDrag(false)}
              onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files?.[0]; if (f) onFile(f); }}
              className={`press mt-4 flex w-full flex-col items-center justify-center rounded-md border-2 border-dashed px-6 py-12 text-center transition-colors ${drag ? "border-board bg-brand-50" : "border-ink/20 hover:border-board/60 hover:bg-brand-50/50"}`}
            >
              <Icon name="file-text" size={44} stroke={1.5} className="text-board" />
              <span className="mt-4 font-display text-[26px] leading-none font-black uppercase">Choisis ton fichier</span>
              <span className="mt-2 text-[14px] text-ink/60">Word (.docx), PDF, texte ou Markdown · 15 Mo max</span>
              <span className="mt-5 inline-flex items-center gap-2 rounded-md bg-hi px-5 py-3 text-[16px] font-bold text-ink shadow-[0_2px_0_0_var(--color-hi-deep)]">
                <Icon name="folder-open" size={18} /> Parcourir
              </span>
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
                  <div key={p.url} className="relative aspect-[3/4] overflow-hidden rounded-sm bg-wall ring-1 ring-black/10">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={p.result ? scans.imageUrl(p.result.id) : p.url} alt={`Page ${i + 1}`} className="h-full w-full object-cover" />
                    <span className="absolute top-1.5 left-1.5 rounded bg-ink/80 px-1.5 py-0.5 text-[12px] font-bold text-white tabular">{i + 1}</span>
                    {p.status === "reading" && (
                      <div className="absolute inset-0 grid place-items-center bg-paper/70">
                        <Icon name="loader-circle" size={30} className="animate-spin text-board" />
                      </div>
                    )}
                    {p.status === "done" && <span className="stamp stamp-in absolute right-1.5 bottom-2 bg-paper/80 text-[12px]">Lu</span>}
                    {p.status === "error" && <span className="absolute inset-x-1 bottom-1 rounded bg-pin/95 px-1.5 py-1 text-[11px] font-semibold text-white">{p.error}</span>}
                    {!reading && (
                      <button type="button" onClick={() => setPhotos((all) => all.filter((x) => x.url !== p.url))} className="absolute top-1.5 right-1.5 grid h-7 w-7 place-items-center rounded bg-paper/90 text-ink" aria-label="Retirer">
                        <Icon name="x" size={15} />
                      </button>
                    )}
                  </div>
                ))}
                <label className="press flex aspect-[3/4] cursor-pointer flex-col items-center justify-center gap-2 rounded-sm border-2 border-dashed border-board/40 bg-brand-50/60 px-2 text-center text-[14px] font-bold text-board">
                  <Icon name="camera" size={28} stroke={1.75} />
                  {photos.length ? "Ajouter" : "Prendre ou choisir des photos"}
                  <input type="file" accept="image/*" multiple capture="environment" className="hidden" onChange={(e) => { addPhotos(e.target.files); e.target.value = ""; }} />
                </label>
              </div>
              <p className="text-[14px] text-ink/60">Pose la feuille sur une table sombre, bien éclairée, et prends toute la page. Paginya la redresse tout seul.</p>
              {photos.length > 0 && (
                <>
                  <label className="flex items-center justify-between gap-3 rounded-md bg-paper p-3.5 text-[15px] font-semibold ring-1 ring-black/10">
                    <span className="flex items-center gap-2"><Icon name="signature" size={18} className="text-board" /> Mes pages sont écrites à la main</span>
                    <input type="checkbox" checked={handwriting} onChange={(e) => setHandwriting(e.target.checked)} className="h-5 w-5 accent-[#1c3a2a]" />
                  </label>
                  {handwriting ? (
                    <label className="flex items-start gap-3 rounded-md bg-hi/35 p-3.5 text-[14px]">
                      <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5 h-5 w-5 accent-[#1c3a2a]" />
                      <span>
                        Pour l&apos;écriture à la main, j&apos;accepte que mes photos soient lues par une intelligence artificielle (Google Gemini, hors du Cameroun).{" "}
                        <Link href="/confidentialite" className="font-bold underline">En savoir plus</Link>
                      </span>
                    </label>
                  ) : (
                    <p className="flex items-center gap-2 text-[14px] text-ink/60"><Icon name="lock" size={16} /> Pages imprimées : lues sur nos serveurs, tes photos ne sont envoyées à personne.</p>
                  )}
                  <PinLabel className="w-full" disabled={(handwriting && !consent) || reading} onClick={readAll}>
                    {reading ? `Lecture… ${photos.filter((p) => p.status === "done").length}/${photos.length}` : `Lire ${photos.length} page${photos.length > 1 ? "s" : ""}`}
                  </PinLabel>
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
                className="w-full resize-y rounded-md border-0 bg-wall/50 p-4 text-[16px] leading-relaxed ring-1 ring-black/10 placeholder:text-ink/35 focus:bg-paper focus:ring-2 focus:ring-hi-deep focus:outline-none"
              />
              <div className="mt-3 flex items-center justify-between gap-3">
                <span className="text-[14px] text-ink/55 tabular">{words ? `${words.toLocaleString("fr-FR")} mots` : ""}</span>
                <PinLabel disabled={words < 5} onClick={() => onText(text)}>Mettre en forme</PinLabel>
              </div>
            </div>
          )}

          {error && <p className="mt-4 flex gap-2 rounded-md bg-pin/10 px-4 py-3 text-[15px] text-pin"><Icon name="triangle-alert" size={18} className="mt-0.5" />{error}</p>}
        </div>

        <RecentList onOpen={onOpen} />

        <ul className="mt-7 grid gap-3 text-[15px] text-ink/75 sm:grid-cols-3">
          {([["lock", "Tes mots ne sont jamais modifiés"], ["eye", "Aperçu gratuit de toutes les pages"], ["trash-2", "Supprimé après 7 jours"]] as const).map(([icon, label]) => (
            <li key={label} className="flex items-center gap-2.5">
              <Icon name={icon} size={18} className="text-board" />
              {label}
            </li>
          ))}
        </ul>
        <p className="mt-6 text-[13px] text-ink/55">
          En continuant, tu acceptes les <Link href="/cgu" className="underline">conditions d&apos;utilisation</Link> et la{" "}
          <Link href="/confidentialite" className="underline">politique de confidentialité</Link>.
        </p>
      </div>
    </div>
  );
}

const ago = (at: number) => {
  const d = Math.round((Date.now() - at) / 86400000);
  return d <= 0 ? "aujourd'hui" : d === 1 ? "hier" : `il y a ${d} jours`;
};

/** "Reprendre un document": the ones opened on this phone, never reopened on their own. */
function RecentList({ onOpen }: { onOpen: (id: string) => void }) {
  const [list, setList] = useState<Recent[]>([]);
  useEffect(() => {
    const t = setTimeout(() => setList(recents())); // after hydration: the list only exists on this phone
    return () => clearTimeout(t);
  }, []);
  if (!list.length) return null;
  return (
    <section className="rise mt-8">
      <h2 className="font-display text-[22px] leading-none font-black text-white uppercase">Reprendre un document</h2>
      <ul className="mt-3 grid gap-2 sm:grid-cols-2">
        {list.map((r) => (
          <li key={r.id} className="paper flex items-center gap-3 rounded-[2px] py-2.5 pr-2 pl-4">
            <button type="button" onClick={() => onOpen(r.id)} className="press flex min-w-0 flex-1 items-center gap-3 text-left">
              <Icon name="file-text" size={22} className="shrink-0 text-board" />
              <span className="min-w-0">
                <span className="block truncate text-[15px] font-bold">{r.title || KIND_LABEL[r.kind] || "Document"}</span>
                <span className="block text-[13px] text-ink/60">{KIND_LABEL[r.kind] ?? "Document"}{r.pages ? ` · ${r.pages} pages` : ""} · {ago(r.at)}</span>
              </span>
            </button>
            <button type="button" onClick={() => { forget(r.id); setList(recents()); }} className="press grid h-9 w-9 shrink-0 place-items-center rounded-md text-ink/45 hover:text-ink" aria-label="Retirer de la liste">
              <Icon name="x" size={16} />
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
