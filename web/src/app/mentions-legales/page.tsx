import type { Metadata } from "next";
import { CONTACT, LegalPage } from "@/components/Footer";

export const metadata: Metadata = { title: "Mentions légales · Paginya" };

export default function MentionsLegales() {
  return (
    <LegalPage title="Mentions légales" updated="23 septembre 2026">
      <h2>Éditeur</h2>
      <ul>
        <li>Nom / raison sociale : <b>[À COMPLÉTER]</b></li>
        <li>Forme juridique : <b>[À COMPLÉTER : établissement individuel, SARL…]</b></li>
        <li>Adresse : <b>[À COMPLÉTER]</b>, Cameroun</li>
        <li>RCCM : <b>[À COMPLÉTER]</b> · NIU : <b>[À COMPLÉTER]</b></li>
        <li>Contact : {CONTACT.email} · WhatsApp {CONTACT.whatsapp}</li>
        <li>Responsable de la publication : <b>[À COMPLÉTER]</b></li>
      </ul>

      <h2>Hébergement</h2>
      <p><b>[À COMPLÉTER à la mise en ligne : nom, adresse et pays de l&apos;hébergeur]</b></p>

      <h2>Paiement</h2>
      <p>Paiements Mobile Money traités par Fapshi (Cameroun).</p>

      <h2>Propriété intellectuelle</h2>
      <p>
        La marque Paginya, le logo, le site et les modèles de mise en page sont protégés. Les documents des utilisateurs leur appartiennent.
        Les polices utilisées sont sous licence libre (SIL Open Font License, Apache).
      </p>
    </LegalPage>
  );
}
