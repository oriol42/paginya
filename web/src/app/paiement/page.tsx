import type { Metadata } from "next";

export const metadata: Metadata = { title: "Paiement", robots: { index: false } };

/** Where Fapshi's payment page sends the customer back (it opened in a new tab). */
export default function Paiement() {
  return (
    <main className="grid min-h-dvh place-items-center bg-slate-50 px-6 text-center">
      <div>
        <div className="mx-auto grid h-20 w-20 place-items-center rounded-full bg-brand-500 text-4xl text-white">✓</div>
        <h1 className="mt-5 font-display text-2xl font-extrabold text-ink">Paiement envoyé</h1>
        <p className="mx-auto mt-2 max-w-xs text-slate-600">
          Tu peux fermer cet onglet et revenir sur Paginya : ton document se débloque tout seul dès que Fapshi confirme.
        </p>
      </div>
    </main>
  );
}
