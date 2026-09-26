import type { Metadata } from "next";
import Link from "next/link";
import { LegalPage } from "@/components/Footer";

export const metadata: Metadata = { title: "Tarifs", description: "Aperçu gratuit. Tu paies seulement pour télécharger ton document, par Mobile Money." };

const PRICES = [
  { label: "Page de garde", price: "300 F", note: "Word + PDF + image" },
  { label: "Document", price: "1 000 F", note: "jusqu'à 15 pages" },
  { label: "Rapport", price: "2 000 F", note: "16 à 40 pages" },
  { label: "Mémoire", price: "3 000 F", note: "plus de 40 pages" },
];

export default function Tarifs() {
  return (
    <LegalPage title="Tarifs" updated="23 septembre 2026">
      <p>Tu vois ton document en entier <b>gratuitement</b>. Tu paies une seule fois, pour le télécharger sans filigrane, par MTN Mobile Money ou Orange Money.</p>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {PRICES.map((p) => (
          <div key={p.label} className="rounded-3xl bg-white p-5 ring-1 ring-slate-100">
            <p className="text-sm font-semibold text-slate-500">{p.label}</p>
            <p className="mt-1 font-display text-2xl font-extrabold text-ink">{p.price}</p>
            <p className="mt-1 text-xs text-slate-500">{p.note}</p>
          </div>
        ))}
      </div>
      <ul>
        <li>Word modifiable + PDF prêt à imprimer.</li>
        <li>La page de garde est incluse quand tu mets en forme un document.</li>
        <li>Modifications et nouveaux téléchargements gratuits pendant 7 jours.</li>
        <li>Prix en francs CFA, toutes taxes comprises, rappelés avant chaque paiement.</li>
      </ul>
      <p><Link href="/document" className="font-semibold text-brand-700 underline">Commencer gratuitement →</Link></p>
    </LegalPage>
  );
}
