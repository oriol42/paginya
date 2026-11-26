"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { docs } from "@/lib/documents";
import { Icon } from "../Icon";
import { Logo } from "../Logo";
import { PurposePick, SlideCount, ThemePick } from "./DeckChoices";

/** Word -> PDF (the file as it is), PDF -> Word (to edit), Word or PDF -> a presentation written by the AI: pick the file, then the usual preview and payment on /document. */
export function ConvertScreen() {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [slides, setSlides] = useState(false);
  const [count, setCount] = useState(12);
  const [theme, setTheme] = useState("auto");
  const [consent, setConsent] = useState(false);
  const [school, setSchool] = useState(true);
  const [drawn, setDrawn] = useState(false); // pictures made by the AI instead of real photos: asked before anything is made
  const [source, setSource] = useState<{ id: string; title: string } | null>(null); // a document already formatted on Paginya

  // /convertir?vers=powerpoint: straight to the presentation (read here: the page itself is static)
  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (query.get("vers") === "powerpoint") setSlides(true);
    const id = query.get("doc");
    if (id) docs.get(id).then((d) => setSource({ id, title: d.meta.cover?.title || d.meta.title || "Ton document" })).catch(() => setError("Ce document n'est plus disponible : choisis ton fichier."));
  }, []);

  async function fromDocument() {
    if (!source || busy) return;
    if (!consent) {
      setError("Coche la case pour que l'IA puisse lire ton document.");
      return;
    }
    setError("");
    setBusy("L'IA prépare tes diapos…");
    try {
      const view = await docs.presentFrom(source.id, count, theme, school, drawn ? "ia" : "photos");
      router.push(`/document?doc=${view.id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy("");
    }
  }

  async function pick(file: File | undefined) {
    if (!file || busy) return;
    const name = file.name.toLowerCase();
    const pdf = name.endsWith(".pdf");
    if (!pdf && !name.endsWith(".docx")) {
      setError("Choisis un fichier Word (.docx) ou PDF.");
      return;
    }
    if (slides && !consent) {
      setError("Coche la case pour que l'IA puisse lire ton document.");
      return;
    }
    setError("");
    setBusy("Envoi du fichier… 0 %");
    try {
      const progress = (sent: number) => setBusy(sent < 1 ? `Envoi du fichier… ${Math.round(sent * 100)} %` : slides ? `L'IA lit « ${file.name.slice(0, 40)} »…` : pdf ? "Lecture du PDF…" : "Lecture du fichier Word…");
      const view = await (slides ? docs.present(file, count, theme, school, drawn ? "ia" : "photos", progress) : docs.convert(file, progress));
      router.push(`/document?doc=${view.id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy("");
    }
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="board sticky top-0 z-30 border-b border-black/25 pt-[env(safe-area-inset-top)]">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-1 px-3">
          <Link href="/" className="press grid h-10 w-10 place-items-center rounded-md text-white/80 hover:bg-white/10 hover:text-white" aria-label="Accueil">
            <Icon name="arrow-left" />
          </Link>
          <Logo tone="board" />
        </div>
      </header>
      <main className="mx-auto w-full max-w-2xl px-5 pt-8 pb-24">
        <h1 className="font-display text-[2.6rem] leading-[0.95] font-black uppercase">Convertir un fichier</h1>
        <p className="mt-3 max-w-prose text-[16px] text-ink/70">
          {slides
            ? "L'IA lit ton Word ou ton PDF, garde l'essentiel et prépare une vraie présentation, avec le nombre de diapos que tu veux et les notes pour l'oral. Tu vois le résultat avant de payer."
            : "Ton Word devient un PDF prêt à imprimer ou à envoyer, tel qu'il est. Ton PDF devient un Word que tu peux modifier : texte, titres, listes, tableaux et images. Tu vois le résultat avant de payer."}
        </p>
        {source && <p className="mt-5 rounded-md bg-brand-50 px-4 py-3 text-[15px] font-semibold">Depuis ton document : {source.title}</p>}
        <div role="radiogroup" aria-label="Type de conversion" className={`mt-5 grid-cols-2 gap-2 ${source ? "hidden" : "grid"}`}>
          {[{ on: true, label: "Faire un PowerPoint", hint: "L'IA prépare ta présentation" }, { on: false, label: "Word ↔ PDF", hint: "Changer le format du fichier" }].map((choice) => (
            <button
              key={choice.label}
              type="button"
              role="radio"
              aria-checked={slides === choice.on}
              disabled={!!busy}
              onClick={() => setSlides(choice.on)}
              className={`press rounded-md px-3 py-3.5 text-left ring-1 ${slides === choice.on ? "bg-board text-white ring-board" : "ring-black/15 hover:bg-ink/5"}`}
            >
              <span className="block text-[16px] font-bold">{choice.label}</span>
              <span className={`mt-0.5 block text-[13px] ${slides === choice.on ? "text-white/75" : "text-ink/60"}`}>{choice.hint}</span>
            </button>
          ))}
        </div>
        {slides && (
          <div className="mt-5 space-y-5">
            <PurposePick school={school} disabled={!!busy} onChange={setSchool} />
            <SlideCount value={count} max={30} disabled={!!busy} onChange={setCount} />
            <ThemePick value={theme} disabled={!!busy} onChange={setTheme} auto />
            <label className={`flex cursor-pointer items-start gap-3 rounded-md p-3.5 ring-1 transition-colors ${drawn ? "bg-brand-50 ring-board" : "ring-black/15 hover:bg-ink/5"}`}>
              <input type="checkbox" name="images-ia" checked={drawn} disabled={!!busy} onChange={(e) => setDrawn(e.target.checked)} className="mt-0.5 h-5 w-5 shrink-0 accent-[var(--color-board)]" />
              <span className="min-w-0">
                <span className="block text-[15px] font-bold">Utiliser des images créées par l&apos;IA</span>
                <span className="mt-0.5 block text-[13px] leading-snug text-ink/65">Une image dessinée pour chaque diapo, avec des personnes d&apos;ici. Sans cette case, Paginya cherche de vraies photos sur internet. Tu pourras changer d&apos;avis dans l&apos;éditeur.</span>
              </span>
            </label>
            <label className="flex cursor-pointer items-start gap-3 text-[14px] text-ink/75">
              <input type="checkbox" checked={consent} disabled={!!busy} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5 h-5 w-5 shrink-0 accent-[var(--color-board)]" />
              J&apos;accepte que le texte de mon document soit envoyé à un service d&apos;IA pour préparer la présentation, et que de courtes descriptions d&apos;images soient envoyées à un service d&apos;illustration.
            </label>
          </div>
        )}
        {source && (
          <button type="button" disabled={!!busy} onClick={fromDocument} className="press mt-6 flex w-full items-center justify-center gap-2 rounded-md bg-board px-4 py-4 text-[17px] font-bold text-white">
            {busy && <Icon name="loader-circle" size={20} className="animate-spin" />}
            {busy || `Créer mes ${count} diapos`}
          </button>
        )}
        <button
          type="button"
          disabled={!!busy}
          hidden={!!source}
          onClick={() => input.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files?.[0]); }}
          className={`press mt-6 flex w-full flex-col items-center justify-center rounded-md border-2 border-dashed px-6 py-12 text-center transition-colors ${drag ? "border-board bg-brand-50" : "border-ink/20 hover:border-board/60 hover:bg-brand-50/50"}`}
        >
          <Icon name={busy ? "loader-circle" : "refresh-cw"} size={44} stroke={1.5} className={`text-board ${busy ? "animate-spin" : ""}`} />
          <span className="mt-4 font-display text-[26px] leading-none font-black uppercase">{busy || "Choisis ton fichier"}</span>
          <span className="mt-2 text-[14px] text-ink/60">Word (.docx) ou PDF · 15 Mo max</span>
          <input
            ref={input}
            type="file"
            accept=".docx,.pdf,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="hidden"
            onChange={(e) => { pick(e.target.files?.[0]); e.target.value = ""; }}
          />
        </button>
        {error && <p className="mt-3 flex gap-2 text-[15px] text-pin"><Icon name="triangle-alert" size={18} className="mt-0.5" />{error}</p>}
        <p className="mt-6 text-[14px] text-ink/60">
          PDF scanné (photos de pages) : le texte est lu automatiquement, relis-le avant de payer.
        </p>
      </main>
    </div>
  );
}
