# Décisions produit — Propre

Décisions prises le 22/09/2026. **Ce fichier fait foi** quand il contredit PLAN.md ou FONCTIONNEMENT-APP.md.

## Identité

| Sujet | Décision |
|---|---|
| Nom | **Propre** : « C'est propre ! », l'expression camerounaise pour un travail bien fait. Domaine .com et marque à vérifier |
| Couleur principale | **Vert émeraude** `#0E9F6E`, foncé `#065F46`, fond clair `#ECFDF5`, touche jaune `#F59E0B` pour les badges |
| Ton | **Tutoiement chaleureux** : « Ton document est prêt ✨ C'est propre ! » |
| Langues | **Interface en français**, modèles de documents **FR et EN** (Buea, Bamenda, HND : « Chapter One », « Acknowledgements », « Abstract ») |
| Plateforme | Web mobile (PWA) d'abord |

## Produit au lancement

- **Deux portes d'entrée** : Studio de pages de garde / Mettre en forme un document.
- **Styles de pages de garde, première vague** : Officiel Cameroun, Moderne géométrique, Corporate bloc couleur, Minimal/Élégant. Chacun existe en plusieurs palettes et en version noir et blanc.
- **Recettes de mise en forme au lancement** :
  1. Rapport de stage + mémoire
  2. Exposé / devoir / rapport de projet
  3. Lettre / demande administrative
  4. Épreuve d'enseignant
- **Look intérieur selon le type** : académique = noir strict aux normes ; exposé et pro = titres dans la couleur du thème, tableaux avec en-tête coloré. Toujours modifiable.

## Argent

| Sujet | Décision |
|---|---|
| Moment du paiement | **Tout est gratuit jusqu'au téléchargement** : import, analyse, édition, styles, aperçu complet de toutes les pages avec filigrane. On paie pour obtenir le Word et le PDF propres |
| Mode de paiement | **Demande directe Fapshi uniquement** (`direct-pay`) : le client tape son numéro et confirme sur son téléphone, sans quitter Propre. ⚠️ Doit être **activé par Fapshi** en production → à demander en semaine 1 |
| Compte | **Aucun compte**. Accès aux documents par lien secret (sauvegardé sur l'appareil + envoyé par WhatsApp à soi-même). Connexion Google en option plus tard |
| Après achat | **Modifications et nouveaux téléchargements gratuits pendant 7 jours** |

### Grille de prix

| Produit | Prix |
|---|---|
| Page de garde seule | 300 F |
| Lettre / demande | 300 F |
| CV | 500 F |
| Document ≤ 15 pages | 1 000 F |
| Rapport / exposé | 2 000 F |
| Mémoire (> 40 pages) | 3 000 F |
| Pass 30 jours illimité | 5 000 F |

## Questions encore ouvertes

1. **Pass 30 jours sans compte** : comment le retrouver sur un autre téléphone ? Piste : code du pass affiché après paiement et envoyé sur WhatsApp. Il faudra alors un compte ou une vérification pour les habitués.
2. **Limites de l'aperçu gratuit** pour protéger les quotas d'IA gratuits (surtout l'OCR des photos) : par exemple 20 pages photo par jour et par appareil. À régler après mesure.
3. **Disponibilité du domaine** : propre.cm / getpropre.com / propre.app ?
4. **Délai d'activation Fapshi** pour la demande directe : à demander à leur support dès maintenant.

## Mises à jour du 23/09/2026

- **Prix** : plus aucun prix dans les boutons, la page d'accueil ou les parcours. Le prix est affiché sur l'écran de paiement (avant confirmation, comme l'exige la loi 2010/021) et sur une page `/tarifs` accessible depuis le pied de page. À mesurer ensuite (test A/B).
- **Éditeur** : les réglages ne cachent plus jamais le document (panneau latéral sur PC, tiroir mi-hauteur sur mobile).
- **Avant / Après** : l'original est affiché tel qu'envoyé, seul ou côte à côte avec la version Propre, avec la liste des améliorations.
- **Page de garde** : incluse par défaut dans chaque document, avec l'en-tête bilingue ; l'école, le titre et le nom se remplissent dans l'onglet « Page de garde ».
- **Styles de document** : 6 (Académique, Universitaire, Moderne, Élégant, Corporate, Simple).
- **Photos** : lecture par Google Gemini, uniquement avec le consentement explicite de l'utilisateur ; photos supprimées au bout de 24 h.
- **Juridique** : CGU/CGV, politique de confidentialité et mentions légales publiées (informations de l'éditeur à compléter).
