# Cadre juridique de Propre (Cameroun)

Étude du 23/09/2026. **Ceci n'est pas un avis d'avocat.** Avant le lancement commercial, faire relire les CGU et la politique de confidentialité par un juriste camerounais (quelques dizaines de milliers de FCFA, c'est un bon investissement).

## 1. Protection des données personnelles : loi n° 2024/017 du 23 décembre 2024

Sources : [texte officiel (Présidence)](https://prc.cm/fr/multimedia/documents/10258-loi-n-2024-017-du-23-12-2024-web), [10 questions (Village de la Justice)](https://www.village-justice.com/articles/cameroun-comprendre-questions-nouvelle-loi-sur-protection-des-donnees-caractere,52122.html), [Techhive](https://www.techhiveadvisory.africa/insights/operationnalisation-de-la-loi-camerounaise-sur-la-protection-des-donnees-un-examen-des-principales-dispositions-et-des-impacts).

- **Applicable depuis le 23 juin 2026** (fin de la période de 18 mois). Propre y est donc soumis dès son lancement.
- **Consentement préalable** et **information** sur les finalités (art. 43). → Case « J'accepte » à l'import et politique de confidentialité claire.
- **Droits des personnes** :
  - accès et rectification (art. 42) ;
  - effacement / « droit à l'oubli » (art. 37) ;
  - opposition (art. 40) ;
  - portabilité ;
  - opposition au profilage (art. 44).

  → Bouton « Supprimer mon document maintenant » et adresse de contact.
- **Sécurité et notification des failles** à l'Autorité et aux personnes concernées.
- **Transferts hors du Cameroun : autorisation préalable de l'Autorité de protection des données.** Amende de 10 à 50 millions de FCFA en cas de violation.

### Conséquences pour Propre (points à régler avant le lancement)

| Traitement | Où | Risque | Mesure |
|---|---|---|---|
| Hébergement des documents | Serveur Oracle (Europe) | Transfert hors du Cameroun | Demander l'autorisation à l'Autorité dès qu'elle est opérationnelle, **ou** héberger au Cameroun (Camtel, hébergeurs locaux) si le coût le permet. Suppression automatique après 7 jours dans tous les cas |
| Lecture des photos (IA) | Google Gemini (hors Cameroun) | Transfert + réutilisation des données par l'offre gratuite | Seulement **si l'utilisateur envoie des photos**, avec un consentement spécifique affiché à ce moment-là. Passer à l'offre payante (pas d'entraînement sur les données) dès les premiers revenus |
| Numéro de téléphone (paiement) | Fapshi (Cameroun) + notre base | Donnée personnelle | Utilisé uniquement pour le paiement, conservé avec la commande pendant 12 mois (preuve comptable) |
| Mise en forme de texte / Word | Notre serveur, **sans IA externe** | Faible | Traitement par règles, rien n'est envoyé à un tiers |

## 2. Commerce électronique : loi n° 2010/021 du 21 décembre 2010

Sources : [texte (MINCOMMERCE)](https://www.mincommerce.gov.cm/sites/default/files/documents/loi-n-2010-021-du-21-decembre-2010-regissant-le-commerce-electronique-au-cameroun.pdf), [MINPOSTEL](https://www.minpostel.gov.cm/index.php/fr/les-textes/telecoms-tic/lois-telecoms-tic/274-loi-n-2010-021-du-21-decembre-2010-regissant-le-commerce-electronique-au-cameroun), décret d'application n° 2011/1521/PM du 15 juin 2011.

- **Mentions légales** : identité du vendeur, adresse, RCCM, NIU, contact.
- **Prix TTC et frais indiqués avant la confirmation de la commande** : c'est fait sur l'écran de paiement.
- Le contrat électronique vaut contrat écrit.

→ Tant que l'activité n'est pas immatriculée, le démarrage se fait en informel (Fapshi le permet). **Créer l'entreprise** (établissement individuel ou SARL, via le CFCE) avant de vraiment grandir, pour pouvoir afficher RCCM et NIU.

## 3. Ce qui est en place dans l'application

- `/cgu` : conditions générales d'utilisation et de vente (service, prix, paiement, 7 jours de modifications, remboursement si le fichier est inutilisable, propriété du contenu, interdiction de la fraude académique).
- `/confidentialite` : données collectées, finalités, durées, sous-traitants, transferts, droits, contact.
- `/mentions-legales` : éditeur (à compléter avec le nom, le RCCM et le NIU), hébergeur, contact.
- Consentement au moment de l'import (« En continuant, tu acceptes les CGU et la politique de confidentialité ») et consentement spécifique pour les photos (IA externe).
- Suppression automatique des documents après 7 jours et bouton « Supprimer maintenant ».

## 4. À compléter par le fondateur

- [ ] Nom légal de l'éditeur, adresse, e-mail et WhatsApp de contact
- [ ] RCCM et NIU (après immatriculation)
- [ ] Relecture par un juriste
- [ ] Démarche auprès de l'Autorité de protection des données (transferts)
