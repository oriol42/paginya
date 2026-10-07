"use client";

import type { DocExisting, DocMode, DocPlan, PlanChoice } from "@/lib/documents";
import { Icon } from "../Icon";

type Element = "cover" | "toc" | "numbers";

type Props = {
  existing: DocExisting | null;
  mode: DocMode;
  plan: DocPlan;
  onPlan: (plan: DocPlan) => void;
  hint?: string;
};

const LABEL: Record<Element, string> = { cover: "Page de garde", toc: "Sommaire", numbers: "Numéros de page" };

/** The words for each choice depend on whether the element is already in the file. */
function choices(el: Element, has: boolean, own: boolean): { value: PlanChoice; label: string }[] {
  if (!own) return [{ value: "add", label: "Oui" }, { value: "none", label: "Non" }];
  if (el === "cover") return has ? [{ value: "keep", label: "Garder la mienne" }, { value: "redo", label: "En créer une nouvelle" }] : [{ value: "add", label: "En créer une" }, { value: "none", label: "Sans" }];
  if (el === "toc") return has ? [{ value: "keep", label: "Garder le mien" }, { value: "redo", label: "Le refaire" }] : [{ value: "add", label: "Ajouter" }, { value: "none", label: "Sans" }];
  return has ? [{ value: "keep", label: "Garder" }, { value: "redo", label: "Refaire aux normes" }] : [{ value: "add", label: "Ajouter aux normes" }, { value: "none", label: "Sans" }];
}

function note(el: Element, has: boolean, own: boolean, e: DocExisting | null, value: PlanChoice): string {
  if (!own) {
    if (el === "numbers") return "Chiffres romains (i, ii, iii…) avant l'introduction, puis 1, 2, 3… ; rien sur la page de garde.";
    return "";
  }
  if (el === "cover") return has ? (value === "redo" ? "Ta page de garde est remplacée : on reprend ton nom, ton matricule, ton encadreur…" : "Ta page de garde reste exactement comme elle est.") : "";
  if (el === "toc") {
    if (has) return value === "redo" ? "Ton sommaire est recalculé avec les bons numéros de page." : "Ton sommaire reste comme il est.";
    if (e && (e.titles ?? 0) === 0) return "Aucun titre repérable dans ton texte : impossible d'en faire un sommaire.";
    return value === "add" ? `Fait à partir de tes ${e?.titles ?? ""} titres, même s'ils n'ont pas de style Word.` : "";
  }
  if (has) {
    const scheme = e?.numbering === "roman_arabic" ? "romains puis arabes" : e?.numbering === "roman" ? "romains" : "arabes";
    return value === "redo" ? "Page de garde comptée sans numéro, pages avant l'introduction en i, ii, iii…, puis 1, 2, 3…" : `Tes numéros (${scheme}) restent comme ils sont.`;
  }
  return value === "add" ? "Page de garde sans numéro, pages avant l'introduction en i, ii, iii…, puis 1, 2, 3…" : "";
}

/** One row per element of the document: what the file already has, and what to do about it. */
export function PlanChoices({ existing, mode, plan, onPlan, hint }: Props) {
  const own = mode === "keep";
  const has: Record<Element, boolean> = {
    cover: !!existing?.cover,
    toc: !!existing?.toc,
    numbers: !!existing?.page_numbers,
  };
  const set = (el: Element, value: PlanChoice) => onPlan({ ...plan, [el]: value });

  return (
    <ul className="space-y-3">
      {(["cover", "toc", "numbers"] as Element[]).map((el) => {
        const options = choices(el, own && has[el], own);
        const value = options.some((o) => o.value === plan[el]) ? plan[el] : options[0].value;
        const blocked = own && el === "toc" && !has.toc && (existing?.titles ?? 0) === 0;
        const text = note(el, has[el], own, existing, value);
        return (
          <li key={el} className="rounded-md bg-paper p-3 ring-1 ring-black/10">
            <p className="flex items-center gap-2 text-[15px] font-bold">
              {own && (
                <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[12px] font-bold ${has[el] ? "bg-board/10 text-board" : "bg-ink/5 text-ink/55"}`}>
                  <Icon name={has[el] ? "check" : "x"} size={12} stroke={2.8} />
                  {has[el] ? "déjà là" : "absent"}
                </span>
              )}
              {LABEL[el]}
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5" role="radiogroup" aria-label={LABEL[el]}>
              {options.map((o) => {
                const on = value === o.value;
                const off = blocked && o.value === "add";
                return (
                  <button
                    key={o.value}
                    type="button"
                    role="radio"
                    aria-checked={on}
                    disabled={off}
                    onClick={() => set(el, o.value)}
                    className={`press rounded-md px-3 py-2 text-[14px] font-bold ring-1 transition-colors disabled:opacity-40 ${on ? "bg-board text-white ring-board" : "bg-paper text-ink/70 ring-black/15 hover:bg-ink/5"}`}
                  >
                    {o.label}
                  </button>
                );
              })}
            </div>
            {text && <p className="mt-2 text-[13px] leading-snug text-ink/60">{text}</p>}
            {el === "numbers" && hint && value === "keep" && (
              <p className="mt-2 flex gap-2 rounded-md bg-hi/35 px-3 py-2 text-[13px] leading-snug text-ink">
                <Icon name="info" size={16} className="mt-0.5 shrink-0" />
                <span>{hint}</span>
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}
