"use client";

import { todayFr } from "@/lib/forms";
import { Field, Input, TextArea, Toggle } from "../ui";
import { FormShell } from "./FormShell";

type LetterType = "emploi" | "stage" | "conge" | "absence" | "explication" | "libre";

export type Letter = {
  type: LetterType;
  sender: { name: string; extra: string; address: string; phone: string; email: string };
  place: string;
  date: string;
  recipient: { civility: "Monsieur" | "Madame"; title: string; org: string; city: string };
  via: string;
  subject: string;
  attachments: string[];
  body: string;
  stamp: boolean;
  bodyEdited: boolean;
};

const TYPES: { id: LetterType; emoji: string; label: string; subject: string; attachments: string[] }[] = [
  { id: "emploi", emoji: "💼", label: "Demande d'emploi", subject: "Demande d'emploi", attachments: ["Curriculum vitae", "Copie certifiée du diplôme", "Copie de la CNI"] },
  { id: "stage", emoji: "🎓", label: "Demande de stage", subject: "Demande de stage académique", attachments: ["Curriculum vitae", "Lettre de recommandation de l'établissement"] },
  { id: "conge", emoji: "🌴", label: "Demande de congé", subject: "Demande de congé annuel", attachments: [] },
  { id: "absence", emoji: "📅", label: "Autorisation d'absence", subject: "Demande d'autorisation d'absence", attachments: [] },
  { id: "explication", emoji: "📝", label: "Réponse à une demande d'explication", subject: "Réponse à la demande d'explication n° [numéro] du [date]", attachments: [] },
  { id: "libre", emoji: "✉️", label: "Autre demande", subject: "Demande de [objet]", attachments: [] },
];

function appellation(l: Letter): string {
  return `${l.recipient.civility} ${l.recipient.title}`.trim();
}

/** Standard Cameroonian wording; [words in brackets] are for the user to replace. */
export function templateBody(l: Letter): string {
  const who = appellation(l);
  const end = `Dans l'attente d'une suite favorable, je vous prie d'agréer, ${who}, l'expression de ma haute considération.`;
  switch (l.type) {
    case "emploi":
      return `J'ai l'honneur de venir très respectueusement auprès de votre haute bienveillance solliciter un emploi de [poste recherché] au sein de votre structure.\n\nTitulaire d'un [diplôme], je dispose de compétences en [domaine] que je souhaite mettre au service de votre entreprise. Sérieux, rigoureux et disponible, je suis prêt à m'investir pleinement dans les missions qui me seront confiées.\n\n${end}`;
    case "stage":
      return `J'ai l'honneur de venir très respectueusement solliciter auprès de votre haute bienveillance un stage académique au sein de votre structure, pour une durée de [durée], à compter du [date].\n\nÉtudiant(e) en [filière] à [établissement], ce stage me permettra de mettre en pratique les connaissances acquises et de découvrir le monde professionnel.\n\n${end}`;
    case "conge":
      return `J'ai l'honneur de venir très respectueusement solliciter de votre haute bienveillance un congé annuel de [nombre] jours, du [date de début] au [date de fin] inclus.\n\nJe prendrai toutes les dispositions pour que mes tâches soient assurées pendant mon absence.\n\n${end}`;
    case "absence":
      return `J'ai l'honneur de venir très respectueusement solliciter une autorisation d'absence le [date], pour [motif].\n\nJe m'engage à rattraper le travail en retard dès mon retour.\n\n${end}`;
    case "explication":
      return `Suite à votre demande d'explication citée en objet, j'ai l'honneur de vous apporter les précisions suivantes.\n\n[Explique les faits simplement et honnêtement.]\n\nJe vous prie de bien vouloir m'en excuser et vous assure de ma volonté de faire mieux à l'avenir.\n\nJe vous prie d'agréer, ${who}, l'expression de mon profond respect.`;
    default:
      return `J'ai l'honneur de venir très respectueusement solliciter [ce que tu demandes].\n\n[Explique ta demande.]\n\n${end}`;
  }
}

export function initialLetter(): Letter {
  const base: Letter = {
    type: "emploi",
    sender: { name: "", extra: "", address: "", phone: "", email: "" },
    place: "Yaoundé",
    date: todayFr(),
    recipient: { civility: "Monsieur", title: "le Directeur Général", org: "", city: "" },
    via: "",
    subject: TYPES[0].subject,
    attachments: TYPES[0].attachments,
    body: "",
    stamp: false,
    bodyEdited: false,
  };
  return { ...base, body: templateBody(base) };
}

function missing(l: Letter): string[] {
  const m: string[] = [];
  if (!l.sender.name.trim()) m.push("ton nom");
  if (!l.recipient.title.trim()) m.push("le destinataire");
  if (/\[[^\]]+\]/.test(l.body + l.subject)) m.push("les passages entre [crochets]");
  return m;
}

export function LetterApp() {
  return (
    <FormShell<Letter>
      kind="lettre"
      title="Ta lettre ou demande"
      initial={initialLetter()}
      missing={missing}
      heading="Ta lettre est prête ✨"
      bullets={["Format administratif camerounais", "Word modifiable + PDF prêt à imprimer", "Modifications gratuites pendant 7 jours"]}
    >
      {(l, set) => {
        const regen = (next: Letter) => (next.bodyEdited ? next.body : templateBody(next));
        const setAndRegen = (patch: Partial<Letter>) => {
          const next = { ...l, ...patch };
          set({ ...patch, body: regen(next) });
        };
        return (
          <div className="space-y-7">
            <section>
              <h3 className="mb-3 text-xs font-bold tracking-wider text-slate-500 uppercase">Type de lettre</h3>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {TYPES.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setAndRegen({ type: t.id, subject: t.subject, attachments: t.attachments })}
                    className={`rounded-2xl p-3 text-left text-sm font-semibold transition ${l.type === t.id ? "bg-ink text-white" : "bg-white text-slate-700 ring-1 ring-slate-200 hover:ring-brand-300"}`}
                  >
                    <span className="mr-1">{t.emoji}</span>{t.label}
                  </button>
                ))}
              </div>
            </section>

            <section className="space-y-3">
              <h3 className="text-xs font-bold tracking-wider text-slate-500 uppercase">Toi</h3>
              <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-3">
                <Field label="Nom et prénom"><Input value={l.sender.name} placeholder="MBALLA Junior" onChange={(e) => set({ sender: { ...l.sender, name: e.target.value } })} /></Field>
                <Field label="Téléphone"><Input value={l.sender.phone} inputMode="tel" placeholder="6XX XX XX XX" onChange={(e) => set({ sender: { ...l.sender, phone: e.target.value } })} /></Field>
              </div>
              <Field label="Fonction / matricule (facultatif)"><Input value={l.sender.extra} placeholder="Ex. : Agent commercial, Mle 123456" onChange={(e) => set({ sender: { ...l.sender, extra: e.target.value } })} /></Field>
              <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-3">
                <Field label="Adresse (facultatif)"><Input value={l.sender.address} placeholder="BP 1234 Yaoundé" onChange={(e) => set({ sender: { ...l.sender, address: e.target.value } })} /></Field>
                <Field label="E-mail (facultatif)"><Input value={l.sender.email} placeholder="toi@mail.cm" onChange={(e) => set({ sender: { ...l.sender, email: e.target.value } })} /></Field>
              </div>
            </section>

            <section className="space-y-3">
              <h3 className="text-xs font-bold tracking-wider text-slate-500 uppercase">Le destinataire</h3>
              <div className="flex gap-2">
                {(["Monsieur", "Madame"] as const).map((c) => (
                  <button key={c} type="button" onClick={() => setAndRegen({ recipient: { ...l.recipient, civility: c } })} className={`rounded-full px-4 py-2 text-sm font-bold ${l.recipient.civility === c ? "bg-ink text-white" : "bg-white text-slate-600 ring-1 ring-slate-200"}`}>
                    {c}
                  </button>
                ))}
              </div>
              <Field label="Titre"><Input value={l.recipient.title} placeholder="le Directeur Général" onChange={(e) => setAndRegen({ recipient: { ...l.recipient, title: e.target.value } })} /></Field>
              <div className="grid grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] gap-3">
                <Field label="Structure"><Input value={l.recipient.org} placeholder="de ENEO Cameroun" onChange={(e) => set({ recipient: { ...l.recipient, org: e.target.value } })} /></Field>
                <Field label="Ville"><Input value={l.recipient.city} placeholder="Douala" onChange={(e) => set({ recipient: { ...l.recipient, city: e.target.value } })} /></Field>
              </div>
              <Field label="Sous couvert de (facultatif)" hint="Quand la lettre doit passer par un chef intermédiaire"><Input value={l.via} placeholder="Monsieur le Chef du personnel" onChange={(e) => set({ via: e.target.value })} /></Field>
            </section>

            <section className="space-y-3">
              <h3 className="text-xs font-bold tracking-wider text-slate-500 uppercase">La lettre</h3>
              <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)] gap-3">
                <Field label="Lieu"><Input value={l.place} onChange={(e) => set({ place: e.target.value })} /></Field>
                <Field label="Date"><Input value={l.date} onChange={(e) => set({ date: e.target.value })} /></Field>
              </div>
              <Field label="Objet"><Input value={l.subject} onChange={(e) => set({ subject: e.target.value })} /></Field>
              <Field label="Pièces jointes" hint="Une par ligne">
                <TextArea rows={3} value={l.attachments.join("\n")} onChange={(e) => set({ attachments: e.target.value.split("\n") })} />
              </Field>
              <Field label="Texte" hint="Déjà rédigé dans le style administratif : remplace les passages entre [crochets].">
                <TextArea rows={11} value={l.body} onChange={(e) => set({ body: e.target.value, bodyEdited: true })} />
              </Field>
              {l.bodyEdited && (
                <button type="button" onClick={() => set({ body: templateBody(l), bodyEdited: false })} className="text-sm font-semibold text-brand-700">↺ Revenir au modèle</button>
              )}
              <Toggle label="Emplacement pour timbre fiscal" checked={l.stamp} onChange={(stamp) => set({ stamp })} />
            </section>
          </div>
        );
      }}
    </FormShell>
  );
}
