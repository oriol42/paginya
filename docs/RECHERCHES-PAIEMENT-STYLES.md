# Recherches : paiement, moment du paiement, styles, Gamma

Recherches du 22/09/2026.

## 1. À quel moment faire payer (sans frustrer)

**Ce que disent les données :**
- Le moment du paywall compte plus que son design. Le meilleur moment est **juste après la première réussite de l'utilisateur**, quand la motivation est au plus haut ([Yu-kai Chou](https://yukaichou.com/gamification-analysis/paywall-placement-timing-strategies/), [RevenueCat](https://www.revenuecat.com/blog/growth/paywall-placement)).
- Un paywall **après le résultat** convertit **3 à 5 fois mieux** qu'un paywall avant l'accès : l'utilisateur a vu la valeur, et « l'effet de possession » le rend réticent à perdre ce qu'il a déjà obtenu ([Airbridge](https://www.airbridge.io/en/blog/paywall-conversion-structural-decisions), [RevenueCat 2026](https://www.revenuecat.com/blog/growth/subscription-app-trends-benchmarks-2026)).
- Le modèle **remove.bg** est l'exemple le plus proche du nôtre : le résultat est gratuit en basse qualité, on paie pour la haute définition. L'aperçu gratuit sert d'outil de conversion ([costbench](https://costbench.com/software/ai-design-tools/remove-bg/)).

**Appliqué à Propre**, c'est le modèle retenu :

```
Contenu → Analyse animée → Questions → Éditeur-aperçu (tout gratuit, filigrane léger)
                                          │  l'utilisateur voit SON document transformé = effet wow
                                          ▼
                              ┌──────────────────────────────────────┐
                              │ Ton document est prêt ✨ C'est propre ! │
                              │ ✔ 32 pages mises en forme            │
                              │ ✔ Page de garde · sommaire · table   │
                              │ ✔ 3 tableaux et 5 figures légendés   │
                              │ ✔ Word + PDF sans filigrane          │
                              │ ✔ Modifications gratuites 7 jours    │
                              │                                      │
                              │  Numéro : [6 7 _ _ _ _ _ _ _]         │
                              │  [ Payer 2 000 F ]  MTN · Orange      │
                              └──────────────────────────────────────┘
```

**Règles pour déclencher le « wow » sans frustrer :**
1. **Ne jamais demander d'argent avant que l'utilisateur ait vu son propre document transformé.** Pas de prix, pas de formulaire de paiement avant.
2. **Montrer le prix tôt, mais discrètement** (« Gratuit jusqu'au téléchargement · dès 300 F ») : pas de surprise à la fin.
3. **Résumer le travail accompli** dans l'écran de paiement : pages, sommaire, tableaux, figures légendées. Le client voit ce qu'il achète.
4. **Filigrane léger** (« aperçu · Propre » en diagonale, gris clair). Il doit être assez visible pour ne pas imprimer l'aperçu, mais laisser le document lisible et beau.
5. **Les 7 jours de modifications gratuites** éliminent la peur du « et si mon encadreur demande des changements ? ».
6. **Le numéro est mémorisé sur l'appareil** : le deuxième achat se fait en 2 touchers.

## 2. Paiement : intégration de la demande directe Fapshi

Sources : [direct-pay](https://docs.fapshi.com/en/api-reference/endpoint/direct-pay.md), [payment-status](https://docs.fapshi.com/en/api-reference/endpoint/payment-status.md), [webhook](https://docs.fapshi.com/en/api-reference/endpoint/webhook.md), [environnements](https://docs.fapshi.com/en/api-reference/preliminary-knowledge/environment.md).

**Faits clés :**
- `POST {base}/direct-pay`, en-têtes `apiuser` et `apikey`. Corps : `amount` (entier, **minimum 100 XAF**), `phone` (format `67XXXXXXX`), `medium` optionnel (`"mobile money"` / `"orange money"`, détecté automatiquement si absent), `externalId`, `userId`, `message`. Réponse : `transId`.
- **Désactivé par défaut en production** : il faut demander l'activation à Fapshi. La doc prévient : un mauvais usage peut entraîner la **suspension du compte**. On n'envoie donc une demande qu'après une action explicite du client.
- Adresses : sandbox `https://sandbox.fapshi.com`, production `https://live.fapshi.com`.
- Numéros de test en sandbox : `670000000` = succès, `670000001` = échec.
- Les clés de production ne sont affichées **qu'une seule fois** à leur création.
- Webhook : statuts `SUCCESSFUL` / `FAILED` / `EXPIRED`. Il est **envoyé une seule fois**, avec l'en-tête `x-wh-secret` à vérifier. Il faut répondre 200 rapidement.

**Déroulement dans Propre :**

1. Le client touche **Payer**. Le serveur crée une commande : `orderId`, document, **montant calculé côté serveur** (jamais envoyé par le navigateur), statut `PENDING`.
2. Le serveur appelle `direct-pay` avec `amount`, `phone`, `externalId = orderId` et `message = "Propre – Rapport de stage"`, puis enregistre le `transId`.
3. L'app affiche l'écran « ⏳ Confirme le paiement sur ton téléphone », avec les instructions propres à l'opérateur (à valider en sandbox puis en production) et un compte à rebours.
4. Le serveur apprend le résultat de **deux façons**, pour ne jamais rater un paiement :
   - par le **webhook** (on vérifie `x-wh-secret`) ;
   - par une **vérification régulière** de `payment-status/{transId}` toutes les 5 s pendant 3 minutes, car le webhook n'est envoyé qu'une fois.
5. Si le statut est `SUCCESSFUL`, que `amount` correspond et que `externalId` = `orderId`, la commande passe à `PAID`. Le serveur génère alors le Word et le PDF sans filigrane. L'app affiche « C'est propre ! », avec le téléchargement, l'envoi sur WhatsApp et un reçu.
6. Si le statut est `FAILED` ou `EXPIRED`, un message bienveillant s'affiche (« Le paiement n'a pas abouti, rien n'a été débité ») avec « Réessayer » et « Changer de numéro ».
7. Les deux notifications (webhook et vérification) sont traitées de façon **idempotente** : un même paiement ne débloque qu'une seule fois.

## 3. Styles de pages de garde : tendances 2026

- **Formes géométriques** avec palette réduite ou fort contraste : moderne, confiant, reconnaissable même en petit ([Troubador](https://troubador.co.uk/blog/book-cover-trends)).
- **Minimalisme** : un titre fort, une palette maîtrisée, des espacements volontaires. Ce style transmet sérieux et autorité, idéal pour les documents professionnels ([BookCoverHub](https://bookcoverhub.com/blog/book-cover-design-trends/)).
- **Grands aplats de couleur** (color blocking) : de grandes zones de couleur contrastées ([BookCoverHub](https://bookcoverhub.com/blog/book-cover-design-trends/)).
- **Rapports d'entreprise** : couvertures géométriques avec icônes et visuels ([Visme](https://visme.co/blog/annual-report-design/)).

Ça confirme les 4 familles retenues : Officiel Cameroun (norme locale), Moderne géométrique, Corporate bloc couleur, Minimal/Élégant.

**Palettes de départ proposées pour les pages de garde** (chacune avec sa version N&B) :

| Palette | Primaire | Secondaire | Accent |
|---|---|---|---|
| Émeraude (couleur de Propre) | `#0E9F6E` | `#065F46` | `#F59E0B` |
| Bleu académique | `#1E3A8A` | `#0F172A` | `#FACC15` |
| Bordeaux | `#9F1239` | `#4C0519` | `#D4AF37` |
| Terracotta | `#C2410C` | `#431407` | `#0D9488` |
| Graphite | `#334155` | `#0F172A` | `#38BDF8` |

## 4. Gamma : ce qu'on reprend

Sources : [Gamma](https://gamma.app/explore/content/guides/what-is-gamma-and-how-does-it-use-ai-to-build-presentations), [revue 2026](https://www.presentations.ai/blog/gamma-review), [édition par IA](https://help.gamma.app/en/articles/8033284-can-i-edit-my-content-using-ai).

- **Séparation du contenu et du design** : le panneau de thèmes change tout le style sans toucher au contenu.
- **Cartes (blocs)** : on change la mise en page d'un bloc en un clic, et le contenu d'origine reste intact.
- **Agent IA permanent** (Gamma 3.0, septembre 2025) : un assistant de chat dans l'outil (orthographe, traduction, commandes libres).
- **4 façons de commencer** : consigne écrite, texte collé, fichier importé, modèle.

Différence de Propre : **sortie A4 imprimable conforme aux normes, et l'IA ne réécrit pas les mots par défaut.**
