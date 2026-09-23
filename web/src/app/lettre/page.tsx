import type { Metadata } from "next";
import { Suspense } from "react";
import { LetterApp } from "@/components/forms/LetterForm";

export const metadata: Metadata = {
  title: "Lettre et demande administrative · Paginya",
  description: "Demande d'emploi, de stage, de congé… au format administratif camerounais, prête à imprimer.",
};

export default function LettrePage() {
  return <Suspense><LetterApp /></Suspense>;
}
