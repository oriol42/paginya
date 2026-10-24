import type { Metadata } from "next";
import { Suspense } from "react";
import { LegalPage } from "@/components/Footer";
import { SupportPage } from "@/components/SupportPage";

export const metadata: Metadata = { title: "Aide", description: "Un souci avec un paiement ou un document ? Écris à l'équipe Paginya, on te répond vite." };

export default function Aide() {
  return (
    <LegalPage title="Aide">
      <Suspense><SupportPage /></Suspense>
    </LegalPage>
  );
}
