import type { Metadata } from "next";
import { Suspense } from "react";
import { ExamApp } from "@/components/forms/ExamForm";

export const metadata: Metadata = {
  title: "Épreuve d'enseignant",
  description: "Tape tes exercices, Paginya fait l'en-tête MINESEC, le barème aligné et la mise en page.",
};

export default function EpreuvePage() {
  return <Suspense><ExamApp /></Suspense>;
}
