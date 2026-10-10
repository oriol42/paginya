import type { Metadata } from "next";
import { ConvertScreen } from "@/components/doc/ConvertScreen";

export const metadata: Metadata = {
  title: "Convertir Word en PDF",
  description: "Transforme ton fichier Word en PDF prêt à imprimer ou à envoyer.",
};

export default function ConvertPage() {
  return <ConvertScreen />;
}
