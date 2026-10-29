import type { Metadata } from "next";
import { ConvertScreen } from "@/components/doc/ConvertScreen";

export const metadata: Metadata = {
  title: "Convertir Word en PDF, PDF en Word",
  description: "Transforme ton Word en PDF prêt à imprimer, ou ton PDF en Word modifiable. Résultat visible avant de payer.",
};

export default function ConvertPage() {
  return <ConvertScreen />;
}
