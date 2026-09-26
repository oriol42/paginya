import type { Metadata } from "next";
import Link from "next/link";
import { CONTACT, LegalPage } from "@/components/Footer";

export const metadata: Metadata = { title: "Conditions générales" };

export default function Cgu() {
  return (
    <LegalPage title="Conditions générales d'utilisation et de vente" updated="23 septembre 2026">
      <p>
        Ces conditions encadrent l&apos;utilisation de Paginya (le « Service »), édité par l&apos;entité décrite dans les{" "}
        <Link href="/mentions-legales" className="text-brand-700 underline">mentions légales</Link>. Utiliser le Service, c&apos;est les accepter.
      </p>

      <h2>1. Le Service</h2>
      <p>
        Paginya met en forme des documents fournis par l&apos;utilisateur (texte, fichier Word ou PDF, photos) et crée des pages de garde.
        Paginya <b>ne rédige pas</b> le contenu : il s&apos;occupe uniquement de la présentation (titres, listes, tableaux, sommaire, pagination, page de garde).
        La détection automatique de la structure peut se tromper : l&apos;utilisateur vérifie l&apos;aperçu, gratuit et complet, avant tout paiement.
      </p>

      <h2>2. Utilisation honnête</h2>
      <ul>
        <li>Tu garantis avoir le droit d&apos;utiliser les contenus que tu envoies.</li>
        <li>Paginya ne doit pas servir à la fraude académique (présenter le travail d&apos;un autre comme le sien) ni à produire des documents officiels falsifiés.</li>
        <li>Les contenus illégaux, haineux ou portant atteinte aux droits d&apos;autrui sont interdits.</li>
      </ul>

      <h2>3. Prix et paiement</h2>
      <p>
        L&apos;aperçu est gratuit. Le prix, en francs CFA toutes taxes comprises, est affiché clairement sur l&apos;écran de téléchargement, <b>avant</b> la confirmation du paiement
        (voir aussi la page <Link href="/tarifs" className="text-brand-700 underline">Tarifs</Link>). Le paiement se fait par Mobile Money (MTN MoMo, Orange Money) via notre prestataire de paiement Fapshi.
        La commande est conclue quand l&apos;utilisateur confirme le paiement sur son téléphone.
      </p>

      <h2>4. Livraison, modifications et remboursement</h2>
      <ul>
        <li>Les fichiers (Word, PDF, image) sont disponibles immédiatement après le paiement.</li>
        <li>Pendant <b>7 jours</b> après le paiement, l&apos;utilisateur peut modifier son document et le retélécharger gratuitement, avec le même lien.</li>
        <li>Si un fichier payé est inutilisable à cause d&apos;une erreur du Service et que nous ne pouvons pas la corriger, nous remboursons le montant payé.
          Contact : {CONTACT.email} / WhatsApp {CONTACT.whatsapp}.</li>
        <li>L&apos;aperçu étant gratuit et complet, un document conforme à l&apos;aperçu validé n&apos;est pas remboursable.</li>
      </ul>

      <h2>5. Tes contenus</h2>
      <p>
        Tu restes propriétaire de tes textes et documents. Tu nous autorises seulement à les traiter pour fournir le Service.
        Ils sont supprimés automatiquement 7 jours après le paiement (ou la création, sans paiement), et tu peux les supprimer à tout moment.
        Détails : <Link href="/confidentialite" className="text-brand-700 underline">politique de confidentialité</Link>.
      </p>

      <h2>6. Responsabilité</h2>
      <p>
        Nous faisons de notre mieux pour respecter les normes de présentation courantes, mais chaque établissement a ses propres règles :
        l&apos;utilisateur reste responsable de vérifier que son document respecte les consignes qui lui ont été données.
      </p>

      <h2>7. Droit applicable</h2>
      <p>
        Ces conditions sont soumises au droit camerounais, notamment la loi n° 2010/021 du 21 décembre 2010 régissant le commerce électronique au Cameroun.
        En cas de litige, une solution amiable sera recherchée d&apos;abord ; à défaut, les tribunaux compétents du Cameroun seront saisis.
      </p>
    </LegalPage>
  );
}
