import type { Metadata } from "next";
import { CONTACT, LegalPage } from "@/components/Footer";

export const metadata: Metadata = { title: "Confidentialité" };

export default function Confidentialite() {
  return (
    <LegalPage title="Politique de confidentialité" updated="21 octobre 2026">
      <p>
        Cette politique explique quelles données Paginya traite, pourquoi, et quels sont tes droits, conformément à la loi n° 2024/017 du 23 décembre 2024
        relative à la protection des données à caractère personnel au Cameroun.
      </p>

      <h2>1. Quelles données ?</h2>
      <ul>
        <li><b>Tes documents</b> : textes, fichiers et photos que tu envoies, et les informations de ta page de garde (nom, matricule, établissement, encadreurs).</li>
        <li><b>Ton numéro de téléphone</b>, uniquement quand tu paies.</li>
        <li><b>Ton adresse Gmail</b>, seulement si tu prends le pass 30 jours : il est gardé sur ton compte Google pour que tu le retrouves sur un autre téléphone.</li>
        <li><b>Des données techniques</b> (adresse IP, type d&apos;appareil) pour la sécurité et le bon fonctionnement.</li>
        <li><b>Des statistiques de visite</b> : un identifiant au hasard gardé sur ton appareil, le site d&apos;où tu viens et les étapes franchies (ouverture d&apos;un outil, envoi d&apos;un document, paiement). Jamais le contenu de tes documents.</li>
      </ul>
      <p>Pas de compte obligatoire, pas de mot de passe. Nous ne vendons aucune donnée.</p>

      <h2>2. Pourquoi ?</h2>
      <ul>
        <li>Mettre en forme ton document et te le livrer (exécution du service que tu demandes).</li>
        <li>Encaisser le paiement et en garder la preuve (obligation comptable).</li>
        <li>Sécuriser le service et corriger les erreurs.</li>
        <li>Savoir quelles publicités amènent des visiteurs intéressés, et à quelle étape le site les perd, pour l&apos;améliorer.</li>
      </ul>

      <h2>3. Combien de temps ?</h2>
      <ul>
        <li>Documents et pages de garde : <b>supprimés automatiquement 7 jours</b> après le paiement (ou après la création, sans paiement). Tu peux les supprimer immédiatement avec le bouton « Supprimer ».</li>
        <li>Photos envoyées pour lecture : supprimées après <b>24 heures</b>.</li>
        <li>Preuve de paiement (numéro, montant, date) : 12 mois.</li>
        <li>Statistiques de visite : 12 mois.</li>
        <li>Compte du pass (adresse Gmail, date de fin du pass) : tant que tu l&apos;utilises ; supprimé sur simple demande.</li>
      </ul>

      <h2>4. Qui y a accès ?</h2>
      <ul>
        <li><b>Fapshi</b> (Cameroun) : traitement du paiement Mobile Money.</li>
        <li><b>Meta</b> (Facebook, Instagram) : quand tu viens d&apos;une de nos publicités, le pixel Meta lui indique les étapes franchies (page vue, document envoyé, paiement et son montant), pour mesurer nos publicités. Meta peut relier ces informations à ton compte Facebook. Tu peux le bloquer avec un bloqueur de publicités ou dans les réglages « Activité hors Meta » de ton compte.</li>
        <li><b>Nos hébergeurs</b> Cloudflare, Render et Supabase : serveurs aux États-Unis (voir les mentions légales).</li>
        <li><b>Google (Gemini)</b>, ou <b>Groq</b> / <b>OpenRouter</b> quand Gemini est indisponible : <u>seulement pour des pages écrites à la main</u>, si tu le choisis et après ton accord explicite. Le traitement a lieu hors du Cameroun. Les pages imprimées sont lues sur nos propres serveurs, sans les envoyer à personne.</li>
      </ul>
      <p>
        Les transferts de données hors du Cameroun sont encadrés par la loi n° 2024/017. Nous limitons ces transferts au strict nécessaire,
        les soumettons à ton accord quand ils sont facultatifs (photos) et effectuons les démarches requises auprès de l&apos;Autorité de protection des données.
      </p>

      <h2>5. Tes droits</h2>
      <p>
        Tu peux accéder à tes données, les faire corriger ou supprimer, t&apos;opposer à leur traitement et récupérer tes documents.
        La plupart se fait directement dans l&apos;application (modifier, télécharger, supprimer). Pour le reste : {CONTACT.email} ou WhatsApp {CONTACT.whatsapp}. Réponse sous 30 jours maximum.
      </p>

      <h2>6. Sécurité</h2>
      <p>
        Chaque document n&apos;est accessible qu&apos;avec son lien secret (impossible à deviner). Les échanges sont chiffrés (HTTPS).
        En cas de fuite de données, nous prévenons l&apos;Autorité de protection des données et les personnes concernées.
      </p>

      <h2>7. Stockage local</h2>
      <p>
        Pour que tu retrouves ton travail, ton brouillon et ton numéro de paiement sont gardés <b>sur ton propre appareil</b> (stockage du navigateur).
        Tu peux les effacer en vidant les données du site dans ton navigateur.
      </p>
    </LegalPage>
  );
}
