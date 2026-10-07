"use client";

import { useState } from "react";
import { KINDS, type DocMode, type DocPlan, type DocView } from "@/lib/documents";
import { Icon } from "../Icon";
import { PinLabel, Select } from "../ui";
import { PlanChoices } from "./PlanChoices";

type Props = {
  doc: DocView;
  busy: boolean;
  error: string;
  /** The user picked another kind of document (the server proposes the matching plan). */
  onKind: (kind: string) => Promise<void>;
  /** "Oui, c'est une épreuve": the text goes to the exam form. */
  onExam: () => void;
  /** Apply the plan: nothing was changed or laid out before this. */
  onApply: (mode: DocMode, plan: DocPlan) => void;
};

/** "J'ai analysé ton document": what Paginya understood, and one choice per element before anything changes. */
export function AnalysisScreen({ doc, busy, error, onKind, onExam, onApply }: Props) {
  const report = doc.analysis;
  const [plan, setPlan] = useState<DocPlan>(doc.plan);
  const [notExam, setNotExam] = useState(false);
  const mode: DocMode = doc.mode === "keep" ? "keep" : "rebuild";
  if (!report) return null;

  const isExam = report.exam && !notExam;
  const kind = report.kind === "epreuve" && notExam ? report.detected_kind : isExam ? "epreuve" : doc.meta.kind;
  const known = KINDS.filter((k) => k.id !== "epreuve").some((k) => k.id === kind);

  async function changeKind(next: string) {
    if (next === "epreuve") {
      onExam();
      return;
    }
    await onKind(next); // the parent reloads the document with the plan the server proposes for that kind
  }

  return (
    <div className="mx-auto w-full max-w-2xl px-4 pt-8 pb-32">
      <h1 className="rise font-display text-[2.4rem] leading-[0.95] font-black text-white uppercase">J&apos;ai analysé ton document</h1>
      <p className="mt-2 text-[15px] text-white/70">Rien n&apos;est changé tant que tu n&apos;as pas validé.</p>

      <section className="paper pin-in relative mt-6 rounded-[2px] p-5 pt-8 text-ink" aria-label="Type de document">
        <span className="pin top-3 left-1/2 -translate-x-1/2" aria-hidden />
        <p className="font-display text-[26px] leading-none font-black uppercase">
          {isExam ? "J'ai reconnu une épreuve d'examen" : `J'ai reconnu ${report.kind_label}`}
        </p>
        {report.why.length > 0 && <p className="mt-2 text-[14px] text-ink/65">Parce que : {report.why.join(" · ")}.</p>}

        {isExam ? (
          <div className="mt-4 space-y-2">
            <p className="text-[15px]">Je peux la mettre au format camerounais : en-tête bilingue, exercices, barème.</p>
            <div className="flex flex-wrap gap-2">
              <PinLabel type="button" className="!px-5 !py-3 !text-[18px]" onClick={onExam}>Oui, créer l&apos;épreuve</PinLabel>
              <button type="button" onClick={() => setNotExam(true)} className="press rounded-md px-4 py-3 text-[15px] font-bold ring-1 ring-black/15 hover:bg-ink/5">
                Non, c&apos;est un autre document
              </button>
            </div>
          </div>
        ) : (
          <label className="mt-4 block text-[14px] font-semibold text-ink/70">
            Ce n&apos;est pas ça ? Change le type
            <Select value={known ? kind : "document"} disabled={busy} onChange={(e) => changeKind(e.target.value)} className="mt-1.5">
              {KINDS.map((k) => (
                <option key={k.id} value={k.id}>{k.label}{k.id === "epreuve" ? " (autre format)" : ""}</option>
              ))}
            </Select>
          </label>
        )}
      </section>

      {!isExam && (
        <section className="paper mt-5 rounded-[2px] p-5 text-ink" aria-label="Ce que contient ton document">
          <p className="font-display text-[22px] leading-none font-black uppercase">
            {mode === "keep" ? "Ce que ton document a déjà" : "Les pages à ajouter"}
          </p>
          <p className="mt-2 mb-4 text-[14px] text-ink/65">
            {mode === "keep"
              ? "Choisis pour chaque élément : je garde ce que tu as fait, ou je le refais. Ton texte, tes styles et ton tableau ne sont jamais touchés."
              : "Coche ce que tu veux : tu pourras changer d'avis ensuite."}
          </p>
          <PlanChoices existing={report.existing} mode={mode} plan={plan} onPlan={setPlan} hint={report.hint} />
          {mode === "keep" && (
            <button
              type="button"
              disabled={busy}
              onClick={() => onApply("rebuild", plan)}
              className="press mt-4 w-full rounded-md px-3 py-3 text-[14px] font-bold ring-1 ring-black/15 hover:bg-ink/5 disabled:opacity-50"
            >
              Plutôt tout refaire avec la mise en page Paginya
            </button>
          )}
        </section>
      )}

      {error && <p className="mt-4 flex gap-2 rounded-md bg-paper px-4 py-3 text-[15px] text-pin"><Icon name="triangle-alert" size={18} className="mt-0.5" />{error}</p>}

      {!isExam && (
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-black/10 bg-paper/95 px-4 pt-3 pb-[max(.75rem,env(safe-area-inset-bottom))] backdrop-blur">
          <div className="mx-auto max-w-2xl">
            <PinLabel type="button" className="w-full" disabled={busy} onClick={() => onApply(mode, plan)}>
              {busy ? "Un instant…" : mode === "keep" ? "C'est bon, appliquer" : "C'est bon, mettre en forme"}
            </PinLabel>
          </div>
        </div>
      )}
    </div>
  );
}
