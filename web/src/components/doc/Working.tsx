"use client";

import type { DocMeta } from "@/lib/documents";
import { Icon } from "../Icon";

/** Analysis screen: the sheet is on the board, each real step ticks as the server reports it. */
export function Working({ meta, rendering }: { meta: DocMeta | null; rendering: boolean }) {
  const steps = [
    { label: "Lecture de ton document", done: !!meta },
    { label: meta ? `${meta.headings} titres détectés` : "Détection des titres et des chapitres", done: !!meta },
    {
      label: meta ? `${meta.lists} éléments de liste · ${meta.tables} tableau${meta.tables > 1 ? "x" : ""} · ${meta.figures} image${meta.figures > 1 ? "s" : ""}` : "Listes, tableaux et figures",
      done: !!meta,
    },
    { label: "Mise en page et pagination", done: false, active: rendering || !!meta },
  ];
  return (
    <div className="board flex flex-1 flex-col items-center justify-center px-6 py-14">
      <div className="paper pin-in relative w-full max-w-sm rounded-[2px] px-6 pt-10 pb-6" style={{ ["--tilt" as string]: "-1.5deg" }}>
        <span className="pin top-3 left-1/2 -translate-x-1/2" aria-hidden />
        <h1 className="font-display text-[30px] leading-[0.95] font-black uppercase">On met ton document au propre</h1>
        <ul className="mt-6 space-y-3.5">
          {steps.map((s) => (
            <li key={s.label} className="flex items-center gap-3">
              {s.done ? (
                <span className="rise grid h-7 w-7 shrink-0 place-items-center rounded-full bg-board text-white">
                  <Icon name="check" size={16} stroke={3} />
                </span>
              ) : s.active ? (
                <Icon name="loader-circle" size={28} className="animate-spin text-board" />
              ) : (
                <span className="h-7 w-7 shrink-0 rounded-full border-2 border-dashed border-ink/25" />
              )}
              <span className={`text-[16px] ${s.done ? "font-bold" : "text-ink/60"}`}>{s.label}</span>
            </li>
          ))}
        </ul>
        {meta && <span className="stamp stamp-in absolute right-4 bottom-4 text-[20px]">En cours</span>}
      </div>
      <p className="mt-6 text-[15px] text-white/70">Quelques secondes, même pour un mémoire.</p>
    </div>
  );
}
