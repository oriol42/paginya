"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { docs } from "@/lib/documents";
import { Icon } from "../Icon";
import { Logo } from "../Logo";

/** Word -> PDF (PDF -> Word is not sold yet): pick the file, then the usual preview and payment on /document. */
export function ConvertScreen() {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  async function pick(file: File | undefined) {
    if (!file || busy) return;
    const name = file.name.toLowerCase();
    if (!name.endsWith(".docx")) {
      setError("Choisis un fichier Word (.docx). La conversion PDF vers Word arrive bientôt.");
      return;
    }
    setError("");
    setBusy("Lecture du fichier Word…");
    try {
      const view = await docs.convert(file);
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
          Ton Word devient un PDF prêt à imprimer ou à envoyer, tel qu&apos;il est. Tu vois le résultat avant de payer.
        </p>
        <button
          type="button"
          disabled={!!busy}
          onClick={() => input.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files?.[0]); }}
          className={`press mt-6 flex w-full flex-col items-center justify-center rounded-md border-2 border-dashed px-6 py-12 text-center transition-colors ${drag ? "border-board bg-brand-50" : "border-ink/20 hover:border-board/60 hover:bg-brand-50/50"}`}
        >
          <Icon name={busy ? "loader-circle" : "refresh-cw"} size={44} stroke={1.5} className={`text-board ${busy ? "animate-spin" : ""}`} />
          <span className="mt-4 font-display text-[26px] leading-none font-black uppercase">{busy || "Choisis ton fichier"}</span>
          <span className="mt-2 text-[14px] text-ink/60">Word (.docx) · 15 Mo max</span>
          <input
            ref={input}
            type="file"
            accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="hidden"
            onChange={(e) => { pick(e.target.files?.[0]); e.target.value = ""; }}
          />
        </button>
        {error && <p className="mt-3 flex gap-2 text-[15px] text-pin"><Icon name="triangle-alert" size={18} className="mt-0.5" />{error}</p>}
        <p className="mt-6 text-[14px] text-ink/60">
          PDF vers Word : bientôt disponible.
        </p>
      </main>
    </div>
  );
}
