"use client";

import { useState } from "react";
import { PALETTES } from "@/lib/cover/palettes";
import type { FormView } from "@/lib/forms";
import { Field, Input, TextArea, Toggle } from "../ui";
import { FormShell } from "./FormShell";
import { Icon } from "@/components/Icon";

export type Exam = {
  country: boolean;
  ministry: string;
  delegation: string;
  school: string;
  department: string;
  year: string;
  exam: string;
  subject: string;
  class: string;
  duration: string;
  coef: string;
  teacher: string;
  instructions: string;
  content: string;
  color: string;
};

const EXAMPLE = `Exercice 1 (5 pts)
1) Résoudre dans R l'équation x² - 5x + 6 = 0. (2 pts)
2) En déduire les solutions de l'inéquation x² - 5x + 6 < 0. (3 pts)

Exercice 2 : QCM (5 pts)
1. La dérivée de f(x) = x³ est :
A) 3x²
B) x²
C) 3x

Problème (10 pts)
Partie A
a) Étudier les variations de la fonction f.
b) Tracer sa courbe représentative.`;

export function initialExam(): Exam {
  return {
    country: true,
    ministry: "MINISTÈRE DES ENSEIGNEMENTS SECONDAIRES",
    delegation: "",
    school: "",
    department: "",
    year: "2025-2026",
    exam: "Évaluation de la 1ère séquence",
    subject: "",
    class: "",
    duration: "2 heures",
    coef: "",
    teacher: "",
    instructions: "",
    content: EXAMPLE,
    color: "#0E9F6E",
  };
}

function missing(e: Exam): string[] {
  const m: string[] = [];
  if (!e.school.trim()) m.push("le nom de l'établissement");
  if (!e.subject.trim()) m.push("la matière");
  if (!e.class.trim()) m.push("la classe");
  return m;
}

export function ExamApp() {
  return (
    <FormShell<Exam>
      kind="epreuve"
      title="Ton épreuve"
      initial={initialExam()}
      missing={missing}
      heading="Ton épreuve est prête"
      bullets={["En-tête MINESEC, barème aligné, pages numérotées", "Word modifiable + PDF prêt à tirer", "Modifications gratuites pendant 7 jours"]}
    >
      {(e, set, view) => <ExamSteps e={e} set={set} view={view} />}
    </FormShell>
  );
}

const STEPS = ["En-tête", "Exercices", "Finitions"] as const;

function ExamSteps({ e, set, view }: { e: Exam; set: (patch: Partial<Exam>) => void; view: FormView | null }) {
  const [step, setStep] = useState(0);
  const next = step < STEPS.length - 1 && (
    <button type="button" onClick={() => setStep(step + 1)} className="mt-2 w-full rounded-md bg-ink py-3.5 font-display font-bold text-white">
      Suivant : {STEPS[step + 1]} <Icon name="arrow-right" size={18} />
    </button>
  );
  return (
    <div>
      <div className="mb-6 grid grid-cols-3 gap-1.5">
        {STEPS.map((name, i) => (
          <button key={name} type="button" onClick={() => setStep(i)} className="text-left">
            <span className={`block h-1.5 rounded-full ${i <= step ? "bg-brand-500" : "bg-ink/10"}`} />
            <span className={`mt-1.5 block text-[12px] font-bold ${i === step ? "text-ink" : "text-ink/45"}`}>{i + 1}. {name}</span>
          </button>
        ))}
      </div>

      {step === 0 && (
        <section className="space-y-3">
          <h3 className="font-display text-xl font-bold text-ink">L&apos;en-tête de l&apos;épreuve</h3>
          <Field label="Établissement"><Input value={e.school} placeholder="Lycée de Biyem-Assi" onChange={(x) => set({ school: x.target.value })} /></Field>
          <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-3">
            <Field label="Matière"><Input value={e.subject} placeholder="Mathématiques" onChange={(x) => set({ subject: x.target.value })} /></Field>
            <Field label="Classe"><Input value={e.class} placeholder="Terminale C" onChange={(x) => set({ class: x.target.value })} /></Field>
          </div>
          <Field label="Évaluation"><Input value={e.exam} placeholder="Évaluation de la 1ère séquence" onChange={(x) => set({ exam: x.target.value })} /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Durée"><Input value={e.duration} onChange={(x) => set({ duration: x.target.value })} /></Field>
            <Field label="Coef."><Input value={e.coef} placeholder="4" onChange={(x) => set({ coef: x.target.value })} /></Field>
          </div>
          {next}
        </section>
      )}

      {step === 1 && (
        <section className="space-y-2">
          <div className="flex items-end justify-between">
            <h3 className="font-display text-xl font-bold text-ink">Les exercices</h3>
            {view?.total_points !== undefined && (
              <span className={`rounded-full px-3 py-1 text-xs font-bold ${view.total_points === 20 ? "bg-brand-100 text-brand-700" : "bg-amber-100 text-amber-800"}`}>
                Barème : {view.total_points} pts{view.total_points === 20 ? "" : " (≠ 20)"}
              </span>
            )}
          </div>
          <p className="text-sm leading-relaxed text-ink/60">
            Écris simplement : « Exercice 1 (5 pts) », puis « 1) … (2 pts) », « a) … » pour les sous-questions, « A) … » pour un QCM. Paginya aligne le barème tout seul.
          </p>
          <TextArea rows={16} value={e.content} className="font-mono text-[13.5px]" onChange={(x) => set({ content: x.target.value })} />
          {next}
        </section>
      )}

      {step === 2 && (
        <section className="space-y-3">
          <h3 className="font-display text-xl font-bold text-ink">Finitions (facultatif)</h3>
          <Field label="Examinateur"><Input value={e.teacher} placeholder="M. NGONO Paul" onChange={(x) => set({ teacher: x.target.value })} /></Field>
          <Field label="Consignes"><Input value={e.instructions} placeholder="Calculatrice non autorisée. Soigner la présentation." onChange={(x) => set({ instructions: x.target.value })} /></Field>
          <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-3">
            <Field label="Département"><Input value={e.department} placeholder="Département de Mathématiques" onChange={(x) => set({ department: x.target.value })} /></Field>
            <Field label="Délégation"><Input value={e.delegation} placeholder="Délégation régionale du Centre" onChange={(x) => set({ delegation: x.target.value })} /></Field>
          </div>
          <Field label="Année scolaire"><Input value={e.year} onChange={(x) => set({ year: x.target.value })} /></Field>
          <Toggle label="République du Cameroun · Paix-Travail-Patrie" checked={e.country} onChange={(country) => set({ country })} />
          <div>
            <span className="mb-1.5 block text-[13px] font-semibold text-ink/80">Couleur</span>
            <div className="flex gap-3">
              {PALETTES.map((p) => (
                <button key={p.id} type="button" aria-label={p.name} onClick={() => set({ color: p.primary })} className={`h-9 w-9 rounded-full ${e.color === p.primary ? "ring-2 ring-ink ring-offset-2" : ""}`} style={{ background: p.primary }} />
              ))}
              <button type="button" onClick={() => set({ color: "#1F1F1F" })} className={`h-9 rounded-full px-3 text-xs font-bold ${e.color === "#1F1F1F" ? "bg-ink text-white" : "bg-paper ring-1 ring-black/10"}`}>N&amp;B</button>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
