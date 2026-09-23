"use client";

import { KINDS } from "@/lib/cover/kinds";
import type { DocKind } from "@/lib/cover/types";

const HINTS: Record<DocKind, string> = {
  rapport_stage: "Stage académique ou professionnel",
  memoire: "Licence, master, DIPES…",
  expose: "Lycée, université, travail de groupe",
  rapport_projet: "Projet tutoré, fin de cycle",
  rapport_pro: "Entreprise, association, PME",
  autre: "Dossier, document libre",
};

export function KindPicker({ onPick }: { onPick: (k: DocKind) => void }) {
  return (
    <div className="mx-auto w-full max-w-2xl px-5 pt-8 pb-16">
      <p className="text-sm font-bold tracking-wide text-brand-600 uppercase">Page de garde</p>
      <h1 className="mt-2 font-display text-[2rem] leading-tight font-extrabold text-ink sm:text-4xl">C&apos;est pour quel document ?</h1>
      <p className="mt-2 text-slate-600">On adapte les informations et le style à ton cas.</p>
      <div className="mt-7 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {(Object.keys(KINDS) as DocKind[]).map((k, i) => (
          <button
            key={k}
            type="button"
            onClick={() => onPick(k)}
            style={{ animationDelay: `${i * 40}ms` }}
            className="sheet-in group flex flex-col items-start rounded-3xl bg-white p-4 text-left ring-1 ring-slate-200 transition hover:-translate-y-0.5 hover:shadow-lg hover:ring-brand-300 active:scale-[.98]"
          >
            <span className="grid h-12 w-12 place-items-center rounded-2xl bg-brand-50 text-2xl transition group-hover:scale-110">{KINDS[k].emoji}</span>
            <span className="mt-3 font-display text-[15px] leading-tight font-bold text-ink">{KINDS[k].label}</span>
            <span className="mt-1 text-xs leading-snug text-slate-500">{HINTS[k]}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
