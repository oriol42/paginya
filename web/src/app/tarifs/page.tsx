import type { Metadata } from "next";
import Link from "next/link";
import { LegalPage } from "@/components/Footer";
import { DOC_PRICE, perDayText, PLANS } from "@/lib/plans";

export const metadata: Metadata = { title: "Tarifs", description: "Aperçu gratuit. Un document 550 F, ou un pass 30 jours dès 3 000 F (illimité à 5 000 F), par Mobile Money." };

const F = (n: number) => `${n.toLocaleString("fr-FR").replace(/ | /g, " ")} F`;

const OFFERS = [
  {
    name: "Un document", price: F(DOC_PRICE), per: "une fois", href: "/document", cta: "Commencer",
    points: ["N'importe quel document : mémoire, rapport, page de garde, lettre, CV, épreuve", "Quel que soit le nombre de pages", "Sans compte"],
  },
  {
    name: `Pass ${PLANS.essentiel.name}`, price: F(PLANS.essentiel.price), per: "30 jours", href: "/compte/?formule=essentiel", cta: "Prendre le pass", best: true,
    points: [perDayText(PLANS.essentiel.perDay), "Moins de 100 F par jour", PLANS.essentiel.who],
  },
  {
    name: `Pass ${PLANS.pro.name}`, price: F(PLANS.pro.price), per: "30 jours", href: "/compte/?formule=pro", cta: "Prendre le pass",
    points: [perDayText(PLANS.pro.perDay), PLANS.pro.who, "Pour traiter les documents de tes clients"],
  },
];

export default function Tarifs() {
  return (
    <LegalPage title="Tarifs" updated="24 octobre 2026">
      <p>Tu vois ton document en entier <b>gratuitement</b>. Tu paies seulement pour le télécharger sans filigrane, par MTN Mobile Money ou Orange Money.</p>
      <div className="grid gap-4 sm:grid-cols-3">
        {OFFERS.map((o) => (
          <div key={o.name} className={`relative flex flex-col rounded-md bg-paper p-5 ${o.best ? "ring-2 ring-ink" : "ring-1 ring-black/10"}`}>
            {o.best && <span className="absolute -top-3 left-5 rounded bg-board px-2 py-0.5 text-[12px] font-bold tracking-wide text-white uppercase">Le plus choisi</span>}
            <p className="text-[15px] font-bold text-ink">{o.name}</p>
            <p className="mt-1 font-display text-[32px] leading-none font-black text-ink">{o.price}</p>
            <p className="text-[13px] text-ink/60">{o.per}</p>
            <ul className="mt-3 flex-1 text-[14px]">
              {o.points.map((pt) => <li key={pt}>{pt}</li>)}
            </ul>
            <Link href={o.href} className={`press mt-4 rounded-md px-4 py-2.5 text-center text-[15px] font-bold ${o.best ? "bg-hi text-ink shadow-[0_2px_0_0_var(--color-hi-deep)]" : "ring-1 ring-ink/25"}`}>{o.cta}</Link>
          </div>
        ))}
      </div>
      <ul>
        <li>Word modifiable + PDF prêt à imprimer. La page de garde est incluse quand tu mets en forme un document.</li>
        <li>Modifications et nouveaux téléchargements gratuits pendant 7 jours : ils ne comptent pas dans la limite du jour.</li>
        <li>Le pass est gardé sur ton compte Google : tu le retrouves sur n&apos;importe quel téléphone. Le compteur du jour repart à minuit.</li>
        <li><b>Pas d&apos;abonnement automatique</b> : rien n&apos;est jamais prélevé sans toi. Au bout de 30 jours, tu repaies seulement si tu veux continuer.</li>
        <li>Tu changes de formule en cours de route ? Les jours qui te restent sont gardés, convertis à leur valeur.</li>
        <li>Prix en francs CFA, toutes taxes comprises, rappelés avant chaque paiement.</li>
      </ul>
      <p>Un souci ? <Link href="/aide" className="font-semibold text-brand-700 underline">Écris-nous</Link>.</p>
    </LegalPage>
  );
}
