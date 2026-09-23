"use client";

import type { DocMeta } from "@/lib/documents";

/** Analysis screen: shows the real steps (and what was found) while the server works. */
export function Working({ meta, rendering }: { meta: DocMeta | null; rendering: boolean }) {
  const steps = [
    { label: "Lecture de ton document", done: !!meta },
    {
      label: meta ? `${meta.headings} titres détectés` : "Détection des titres et des chapitres",
      done: !!meta,
    },
    {
      label: meta ? `${meta.lists} éléments de liste · ${meta.tables} tableau${meta.tables > 1 ? "x" : ""} · ${meta.figures} image${meta.figures > 1 ? "s" : ""}` : "Listes, tableaux et figures",
      done: !!meta,
    },
    { label: "Mise en page, sommaire et pagination", done: false, active: rendering },
  ];
  return (
    <div className="mx-auto flex w-full max-w-md flex-1 flex-col items-center justify-center px-6 py-16 text-center">
      <div className="relative h-28 w-24">
        <div className="absolute inset-0 rotate-6 rounded-xl bg-brand-200" />
        <div className="absolute inset-0 -rotate-3 rounded-xl bg-white shadow-xl ring-1 ring-slate-100">
          <div className="space-y-1.5 p-3">
            <div className="h-2 w-2/3 animate-pulse rounded bg-brand-500" />
            {[0, 1, 2, 3, 4].map((i) => (
              <div key={i} className="h-1.5 animate-pulse rounded bg-slate-200" style={{ width: `${90 - i * 9}%`, animationDelay: `${i * 120}ms` }} />
            ))}
          </div>
        </div>
      </div>
      <h1 className="mt-8 font-display text-2xl font-extrabold text-ink">On met ton document au propre…</h1>
      <ul className="mt-6 w-full space-y-3 text-left">
        {steps.map((s) => (
          <li key={s.label} className="flex items-center gap-3 rounded-2xl bg-white px-4 py-3 ring-1 ring-slate-100">
            {s.done ? (
              <span className="pop grid h-6 w-6 shrink-0 place-items-center rounded-full bg-brand-500 text-xs font-bold text-white">✓</span>
            ) : (
              <span className={`h-6 w-6 shrink-0 rounded-full border-[3px] ${s.active ? "animate-spin border-brand-100 border-t-brand-500" : "border-slate-200"}`} />
            )}
            <span className={`text-[15px] ${s.done ? "font-semibold text-ink" : "text-slate-500"}`}>{s.label}</span>
          </li>
        ))}
      </ul>
      <p className="mt-6 text-xs text-slate-400">Quelques secondes, même pour un mémoire.</p>
    </div>
  );
}
