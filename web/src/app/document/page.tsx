import type { Metadata } from "next";
import { Suspense } from "react";
import { DocumentApp } from "@/components/doc/DocumentApp";

export const metadata: Metadata = {
  title: "Mise en forme · Paginya",
  description: "Importe ton Word, ton PDF ou colle ton texte : titres, listes, tableaux, sommaire et pagination automatiques.",
};

export default function DocumentPage() {
  return (
    <Suspense>
      <DocumentApp />
    </Suspense>
  );
}
