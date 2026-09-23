# Checklist d'un SaaS pro : état de Propre

Mise à jour le 23/09/2026. ✅ fait · 🟡 partiel · ⬜ à faire (⏳ = prévu à la mise en ligne)

## Produit
- ✅ Studio de pages de garde (parcours guidé, 4 styles × 5 couleurs, N&B)
- ✅ Mise en forme de documents (Word/PDF/texte → structure → Word + PDF)
- ✅ Avant / Après / Côte à côte, carte « Ce que Propre a fait », 6 styles avec vraies miniatures, page de garde incluse et modifiable dans le document
- ✅ Panneaux à côté du document (PC) / tiroir mi-hauteur sans voile (mobile)
- ✅ Prix retirés des parcours (affichés à la fin + page /tarifs)
- ✅ Photos et scans : redressement automatique, lecture locale Tesseract (gratuite), relecture côte à côte ; manuscrit via Gemini (clé gratuite à ajouter) ; ajustement manuel des coins ⬜
- ✅ Lettres et demandes administratives (`/lettre`)
- ✅ Épreuves d'enseignants (`/epreuve`)
- ✅ Renommage en Paginya
- ⬜ Assistant ✨ (modifications en langage naturel)
- ⬜ « Mes documents » (historique sans compte)

## Paiement
- ✅ Fapshi direct-pay (mode simulé), montant calculé côté serveur, webhook et vérification régulière, idempotence
- ⏳ Clés sandbox puis production, activation de la demande directe par Fapshi
- ⬜ Reçu de paiement (PDF) et historique

## Juridique (voir JURIDIQUE.md)
- ✅ CGU / CGV, politique de confidentialité, mentions légales (pages en ligne)
- ✅ Consentements (import, photos), suppression après 7 jours, bouton « Supprimer maintenant »
- ⬜ Informations de l'éditeur, RCCM/NIU, relecture par un juriste, autorisation de transfert

## Sécurité
- ✅ Nettoyage des SVG (pas de script), prix côté serveur, liens secrets non devinables (128 bits), validation des blocs
- ✅ Limites de taille des fichiers (15 Mo) et des textes
- ⏳ HTTPS, limitation du nombre de requêtes par IP, sauvegardes de la base, secrets en variables d'environnement
- ⏳ Protection contre les fichiers piégés (LibreOffice isolé dans un conteneur, délais maximum)

## Qualité
- ✅ Tests automatiques de l'API (parcours complet texte → paiement → téléchargement)
- ✅ Tests navigateur scriptés (mobile) des parcours principaux
- ⬜ Corpus de 40 vrais documents annotés pour mesurer la détection

## Mise en ligne et exploitation ⏳
- ⏳ Serveur (Oracle gratuit ou hébergeur local), Docker, nom de domaine
- ⏳ Suivi des erreurs (Sentry gratuit), statistiques de visite respectueuses (Cloudflare)
- ⏳ Nettoyage automatique des fichiers (tâche planifiée)
- ⏳ Support : numéro WhatsApp affiché, réponse sous 24 h

## Croissance
- ✅ Générateur de vidéos TikTok
- ⬜ Pages par école pour Google (« page de garde ESSTIC »…)
- ⬜ Programme ambassadeurs (codes promo)
- ⬜ Mesure : visites → aperçus → paiements (taux de conversion)
