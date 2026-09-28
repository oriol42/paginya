import type { Metadata } from "next";

export const metadata: Metadata = { title: "Paiement", robots: { index: false } };

/** Where Fapshi's payment page sends the customer back (it opened in a new tab). */
export default function Paiement() {
  return (
    <main className="grid min-h-dvh place-items-center bg-ink/[0.03] px-6 text-center">
      <div>
        <span className="stamp stamp-in text-[40px]">Payé</span>
        <h1 className="mt-5 font-display text-2xl font-extrabold text-ink">Paiement envoyé</h1>
        <p className="mx-auto mt-2 max-w-xs text-ink/70">
          Tu peux fermer cet onglet et revenir sur Paginya : ton document se débloque tout seul dès que Fapshi confirme.
        </p>
      </div>
    </main>
  );
}
