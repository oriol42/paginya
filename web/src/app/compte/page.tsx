import type { Metadata } from "next";
import { Suspense } from "react";
import { AccountPage } from "@/components/AccountPage";
import { LegalPage } from "@/components/Footer";

export const metadata: Metadata = { title: "Mon compte", robots: { index: false } };

export default function Compte() {
  return (
    <LegalPage title="Mon compte" >
      <Suspense><AccountPage /></Suspense>
    </LegalPage>
  );
}
