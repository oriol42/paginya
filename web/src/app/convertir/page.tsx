import type { Metadata } from "next";
import { ConvertScreen } from "@/components/doc/ConvertScreen";

export const metadata: Metadata = {
  title: "Convertir Word, PDF et PowerPoint",
  description: "Transforme ton Word en PDF prêt à imprimer, ton PDF en Word modifiable, ou l'un des deux en présentation PowerPoint préparée par l'IA. Résultat visible avant de payer.",
};

export default function ConvertPage() {
  return <ConvertScreen />;
}
