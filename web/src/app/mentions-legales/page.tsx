import type { Metadata } from "next";
import { CONTACT, LegalPage } from "@/components/Footer";

export const metadata: Metadata = { title: "Mentions légales" };

export default function MentionsLegales() {
  return (
    <LegalPage title="Mentions légales" updated="28 septembre 2026">
      <h2>Éditeur</h2>
      <ul>
        <li>Éditeur : <b>Zeudjo Tiyo Varela Oriol</b>, développeur, personne physique (entrepreneur individuel, pas encore immatriculé au RCCM)</li>
        <li>Adresse : Ebolowa, Cameroun</li>
        <li>Contact : {CONTACT.email} · WhatsApp {CONTACT.whatsapp}</li>
        <li>Responsable de la publication : Zeudjo Tiyo Varela Oriol</li>
      </ul>

      <h2>Hébergement</h2>
      <ul>
        <li>Site : <b>Vercel Inc.</b>, États-Unis (vercel.com)</li>
        <li>Serveurs de traitement : <b>Render Services, Inc.</b>, États-Unis (render.com)</li>
        <li>Base de données et fichiers : <b>Supabase, Inc.</b>, serveurs aux États-Unis (supabase.com)</li>
      </ul>

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
