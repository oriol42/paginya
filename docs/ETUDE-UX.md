# Étude UX : ce qu'on reprend des applications qui marchent

Étude du 23/09/2026. Objectif : que Propre soit aussi évident que les meilleures apps, pour des gens qui ne maîtrisent pas Word.

## 1. Ce que font les meilleures

| App | Ce qui marche | Source |
|---|---|---|
| **Gamma** | Le contenu est séparé du design : on change de thème en un clic, **on voit le résultat directement sur le document**, puis on referme le sélecteur. Personnalisation volontairement limitée : cohérence et rapidité plutôt que réglages au pixel près. | [Thèmes](https://help.gamma.app/en/articles/10262646-how-do-i-change-my-gamma-theme), [cartes](https://help.gamma.app/en/articles/11969695-how-do-i-style-cards-and-adjust-layout-settings-in-my-gamma) |
| **Canva** | Un **panneau latéral** avec des onglets (Modèles, Éléments…) qui change de contenu instantanément, **sans jamais quitter ni cacher le design**. On clique sur un modèle : il s'applique sur la page. | [Panneau latéral](https://www.c-sharpcorner.com/article/canva-sidebar-and-its-tabs-learn-canva/) |
| **iLovePDF** | « Chaque outil fait une seule chose, bien. » Déposer le fichier, choisir l'action, télécharger. Aucun compte. | [iLovePDF](https://ilovepdf.org/about/) |
| **CamScanner / Adobe Scan** | Détection des bords en direct (coins bleus), recadrage **ajustable à la main**, redressement de la perspective, **filtres** (couleur, noir et blanc, « magique »), plusieurs pages dans un seul document. | [Adobe Scan](https://www.adobe.com/devnet-docs/adobescan/android/en/scan.html), [comparatif](https://www.mksguide.com/adobe-scan-vs-camscanner/) |
| **Retouche photo, immobilier** | **Curseur avant / après** : on fait glisser une ligne sur la même image. « On inspecte au lieu de se souvenir. » | [RevelRaw](https://revelraw.com/blog/before-after-comparison-slider.html) |
| **remove.bg** | Résultat gratuit immédiatement, avec la qualité réduite. On paie pour la haute qualité. | [Costbench](https://costbench.com/software/ai-design-tools/remove-bg/) |

## 2. Ce que ça change dans Propre (décisions)

| Problème relevé | Solution reprise | Modèle |
|---|---|---|
| Les réglages s'ouvrent dans une fenêtre qui **cache** le document | **Panneau latéral** sur PC, **tiroir bas à mi-hauteur sans voile sombre** sur mobile : le document reste visible et se met à jour pendant qu'on règle | Canva, Gamma |
| On ne voit pas **ce qui a changé** | Mode **Avant / Après** : la page d'origine et la page Propre, avec un curseur de comparaison, plus une liste « Ce que Propre a fait » (17 titres structurés, 9 puces, 1 tableau reconstruit, sommaire ajouté…) | Curseur avant/après, résumé à la Grammarly |
| Pas assez de styles | **6 styles de document** avec une **vraie miniature** (générée par notre moteur), appliqués en un clic | Galerie de thèmes Gamma/Canva |
| L'en-tête officiel FR/EN n'apparaît pas | **Page de garde incluse par défaut** dans chaque document, pré-remplie avec le titre détecté ; on complète l'école et le nom dans le panneau | Modèle prérempli (Canva) |
| Photos | Parcours façon CamScanner : prendre ou importer plusieurs pages, **redressement automatique + ajustement des coins**, filtre « document », puis lecture et **relecture côte à côte** | CamScanner, Adobe Scan |
| Prix trop présents | Pas de prix dans les boutons d'action ni dans les parcours. Le prix apparaît **à la fin**, sur l'écran de téléchargement, avec le récapitulatif. Une page **Tarifs** discrète reste accessible (voir §3) | remove.bg, obligation légale |

## 3. La question des prix

Deux avis contradictoires :
- **Les études SaaS** : cacher les prix fait perdre de la confiance et des conversions quand le produit est en libre-service ([Webstacks](https://www.webstacks.com/blog/saas-pricing-page-design), [Orbix](https://www.orbix.studio/blogs/saas-pricing-page-psychology-convert)).
- **Le fondateur** : les gens doivent d'abord voir la valeur. C'est aussi ce que disent les données sur le paywall : un paiement demandé **après le résultat** convertit 3 à 5 fois mieux.
- **La loi camerounaise sur le commerce électronique** ([loi 2010/021](https://www.mincommerce.gov.cm/sites/default/files/documents/loi-n-2010-021-du-21-decembre-2010-regissant-le-commerce-electronique-au-cameroun.pdf)) exige que le prix soit indiqué **avant la confirmation de la commande**.

**Décision :** aucun prix dans le parcours (ni dans les boutons, ni sur la page d'accueil). Le prix est affiché clairement sur l'écran de téléchargement, avant le paiement. Une page `/tarifs`, accessible depuis le pied de page, permet la transparence pour ceux qui la cherchent. On mesurera ensuite si ça convertit mieux (test A/B).

## 4. Principes de design retenus

1. **Une action principale par écran**, un seul gros bouton vert.
2. **Le document ne disparaît jamais** pendant qu'on le modifie.
3. **Montrer le travail fait** (analyse animée, avant/après, liste des améliorations) : c'est ce qui justifie le paiement.
4. **Tout est modifiable plus tard** (7 jours), donc on ne demande que le strict nécessaire au départ.
5. **Des mots simples, du tutoiement** : « Ta page de garde », pas « Paramètres de couverture ».
