# Comment fonctionne l'application (vision « Gamma pour les documents »)

Version 2, 22/09/2026. Elle complète `PLAN.md` et en élargit le périmètre : **tous les types de documents** (pas seulement les mémoires) et un **générateur de pages de garde stylisées**, utilisable seul.

## 0. Ce qu'on reprend de Gamma (et ce qu'on change)

Gamma ([présentation](https://gamma.app/explore/content/guides/what-is-gamma-and-how-does-it-use-ai-to-build-presentations), [thèmes](https://www.presentations.ai/blog/gamma-review), [agent IA](https://help.gamma.app/en/articles/8033284-can-i-edit-my-content-using-ai)) fonctionne sur 4 idées. On les reprend toutes :

1. **Le contenu est séparé du design.** On change de thème en un clic, le texte ne bouge pas.
2. **Le document est fait de blocs** (les « cartes » de Gamma). Chaque bloc a un type : titre, paragraphe, liste, tableau, figure…
3. **L'aperçu est l'éditeur.** On modifie directement sur le rendu final, pas dans un logiciel à menus.
4. **Un assistant IA reste toujours disponible** (« mets les titres en bleu », « fais un tableau avec ça »).

Ce qui change chez nous :
- **La sortie est un vrai document imprimable** : A4, Word + PDF, pagination, sommaire, normes camerounaises. Pas des diapositives.
- **Par défaut, l'IA ne réécrit jamais les mots de l'utilisateur.** Elle organise et met en forme. Reformuler ou corriger l'orthographe reste une option que l'utilisateur doit demander.

## 1. Deux portes d'entrée sur l'accueil

```
┌─────────────────────────────────────┐
│  [logo]                              │
│                                      │
│  Des documents propres,              │
│  sans toucher à Word.                │
│                                      │
│  ┌───────────────────────────────┐  │
│  │ 🎨  Créer une page de garde    │  │
│  │     30+ styles, prête en 1 min │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │ 📄  Mettre en forme un document│  │
│  │     Word, PDF, photo ou texte  │  │
│  └───────────────────────────────┘  │
│                                      │
│  Mes documents récents  ›            │
└─────────────────────────────────────┘
```

Deux gros boutons, rien d'autre. Chaque porte est un produit complet à elle seule.

## 2. Porte 1 : le studio de pages de garde

### Comment ça marche pour l'utilisateur
1. **Type** : Rapport de stage · Mémoire · Exposé · Rapport de projet · Rapport d'activité · Proposition commerciale · Dossier · Devoir · Autre.
2. **Informations** : un formulaire court adapté au type (titre, auteur, établissement ou entreprise, encadreur, date…). **L'établissement se choisit dans une liste** : l'en-tête officiel bilingue et le logo se remplissent automatiquement.
3. **Style** : un carrousel d'aperçus **réels, avec ses propres informations déjà dedans**. On fait défiler, on touche, c'est appliqué.
4. **Couleurs** : une rangée de palettes (pastilles). Un toucher suffit, l'aperçu change instantanément.
5. **Télécharger** : Word + PDF, ou « Continuer vers la mise en forme du document ».

### Les familles de styles (6 familles × 5 palettes × variantes = plus de 30 designs au lancement)

| Famille | Look | Pour qui |
|---|---|---|
| **Officiel Cameroun** | En-tête bilingue République/Ministère/Université, séparateurs `****`, sobre, cadre fin | Mémoires, rapports universitaires (obligatoire dans beaucoup d'écoles) |
| **Moderne géométrique** | Bandes diagonales, triangles et cercles de couleur dans les coins, titre en grand | Rapports de stage en école privée, exposés, projets |
| **Élégant** | Police à empattements, filets dorés ou fins, beaucoup de blanc | Mémoires en lettres, documents juridiques |
| **Corporate** | Grand bloc de couleur (tiers de page), logo d'entreprise, typographie sans empattements | Rapports d'activité, propositions commerciales, PME |
| **Vagues / créatif** | Vagues ou courbes en bas de page, dégradés doux | Exposés, lycée, associations |
| **Minimal** | Typographie seule, une ligne d'accent | Tout public, impression noir et blanc économique |

Chaque design reste lisible **en impression noir et blanc** : on génère une version « N&B » automatique, parce que la plupart des gens impriment en noir au cybercafé.

### Comment c'est fabriqué techniquement
- Un design est un **modèle SVG** avec :
  - des **zones nommées** (`titre`, `sous_titre`, `auteur`, `date`, `logo`, `entete_fr`, `entete_en`…) ;
  - des **formes** dont la couleur vient de variables (`--primaire`, `--secondaire`, `--accent`) ;
  - des **règles d'ajustement** (le titre rétrécit s'il est trop long, deux lignes maximum…).
- **Aperçu** : rendu SVG directement dans le navigateur, donc **instantané** à chaque lettre tapée ou couleur choisie.
- **Export Word** :
  - les formes décoratives deviennent une **image de fond haute définition** placée derrière le texte ;
  - le **texte reste du vrai texte modifiable** dans Word (zones positionnées) ;
  - le PDF est produit par LibreOffice.
- Ajouter un style = ajouter un fichier SVG + un petit fichier JSON, **sans toucher au code**. On peut en sortir un nouveau chaque semaine (« Nouveau style de la semaine », utile pour TikTok).

## 3. Porte 2 : la mise en forme de n'importe quel document

### Catalogue des types (chacun a sa « recette »)

| Famille | Types |
|---|---|
| Académique | Rapport de stage, mémoire, thèse, rapport de projet, exposé, devoir/TP, dossier, article |
| Enseignants | **Épreuve / sujet d'examen** (en-tête lycée, classe, durée, coefficient, barème), fiche de cours, fiche de TD |
| Professionnel | Rapport d'activité, compte rendu / PV de réunion, proposition commerciale, offre de service, procédure, note de service, business plan |
| Administratif | Demande, lettre administrative, attestation, déclaration sur l'honneur, procuration, plainte |
| Personnel | CV, lettre de motivation, programme d'obsèques, faire-part, invitation, texte libre |

Une **recette** précise :
- la page de garde (oui/non, familles de styles proposées) ;
- les pages préliminaires attendues ;
- le sommaire et la table des matières (oui/non) ;
- le thème par défaut ;
- **les questions à poser** (uniquement ce qui manque).

Une lettre n'aura ni sommaire ni page de garde. Une épreuve aura un en-tête d'établissement et un barème.

### Le parcours

```
① Contenu  →  ② Analyse (5-20 s)  →  ③ 2-3 questions  →  ④ Éditeur-aperçu  →  ⑤ Télécharger
```

**① Contenu** : coller du texte, importer un Word/PDF, prendre des photos (plusieurs pages), ou combiner plusieurs fichiers.

**② Analyse** : une animation montre les étapes réelles (« Lecture… », « Détection des titres… », « 3 tableaux trouvés… », « Mise en page… »). Voir le travail se faire donne confiance.

**③ Questions intelligentes** : l'IA a déjà deviné le type et prérempli les champs.
- « C'est bien un **rapport de stage** ? ✔ »
- « Établissement : **ESSTIC – UY2** ? ✔ »
- « Il manque le nom de ton encadreur : ___ »

Tout est modifiable, mais souvent il suffit de valider.

**④ Éditeur-aperçu** : c'est le cœur de l'application (section 4).

**⑤ Télécharger** : paiement Mobile Money, puis Word + PDF + lien WhatsApp.

## 4. L'éditeur-aperçu : simple, beau, modifiable en continu

### Sur téléphone

```
┌─────────────────────────────────────┐
│ ←  Rapport de stage       ↶ ↷   ⋯  │  ← retour, annuler/rétablir
├─────────────────────────────────────┤
│ ┌─────────────────────────────────┐ │
│ │                                 │ │
│ │   (la vraie page A4, zoomable,  │ │
│ │    on fait défiler les pages)   │ │
│ │                                 │ │
│ │   CHAPITRE I : PRÉSENTATION     │ │  ← on touche un bloc
│ │   ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔  │ │     = il s'entoure en bleu
│ │   Lorem ipsum…                  │ │
│ └─────────────────────────────────┘ │
│              page 7 / 32            │
├─────────────────────────────────────┤
│ ✨ Dis ce que tu veux changer…    ➤ │  ← assistant IA, toujours là
├─────────────────────────────────────┤
│  🎨 Style   📑 Plan   🖼 Garde   ⬇  │  ← 4 boutons seulement
└─────────────────────────────────────┘
```

**Toucher un bloc** ouvre un petit panneau en bas de l'écran :

```
┌─────────────────────────────────────┐
│ Ce bloc est un :  [Titre ▾] niveau 2 │
│  ↑ Monter d'un niveau  ↓ Descendre   │
│  ✏️ Corriger le texte                │
│  ✨ Transformer : Liste · Tableau ·  │
│              Citation · Encadré      │
│  ⇅ Déplacer    🗑 Supprimer           │
└─────────────────────────────────────┘
```

**Les 4 boutons du bas :**
- **🎨 Style** : thèmes en pastilles (Académique, Moderne, Pro, Simple…), palette de couleurs, police, taille, interligne, marges, numérotation des titres (I/A/1 ou 1.1.1). Le **préréglage « Normes de mon école »** remplit tout d'un coup. Champ libre « Consignes de ton école » (texte ou photo de la feuille de consignes).
- **📑 Plan** : l'arbre des titres. On glisse pour réordonner et on touche pour changer de niveau. C'est aussi là qu'on active ou désactive sommaire, table des matières, listes des figures et tableaux, sigles, résumé/abstract.
- **🖼 Garde** : ouvre le studio de pages de garde (section 2), déjà rempli.
- **⬇ Télécharger** : aperçu final fidèle, puis paiement.

**Sur PC** (cybercafé), c'est la même chose en 2 colonnes : le plan à gauche, les pages au centre, le style à droite.

### Modification en continu : 2 niveaux d'aperçu

| Aperçu | Moteur | Délai | Rôle |
|---|---|---|---|
| **Instantané** | Rendu HTML/CSS paginé dans le navigateur (Paged.js, gratuit), à partir du même JSON et des mêmes réglages de thème que le rendu Word | < 100 ms | Chaque changement se voit tout de suite |
| **Fidèle** | Serveur : Word → LibreOffice → PDF → images | environ 2-3 s, en arrière-plan, 2 s après la dernière modification | Numéros de page exacts du sommaire. C'est ce qui est montré juste avant le paiement |

- Les deux moteurs lisent le **même fichier de thème** (couleurs, polices, tailles, espacements), ce qui garde l'écart minimal.
- Avant de payer, l'utilisateur voit toujours le **vrai PDF** (avec filigrane) : aucune surprise.
- **Annuler/rétablir illimité** et sauvegarde automatique : on ne perd jamais rien, on peut essayer sans peur.

## 5. L'IA : ce qu'elle fait (bien utilisée)

### À l'analyse (automatique)
1. **Deviner le type de document** et **extraire les informations** (titre, auteur, école, dates) pour préremplir les questions.
2. **Détecter la structure**, même dans un texte sans aucune mise en forme (règles d'abord, IA pour les cas incertains, voir PLAN.md §5.1) :
   - titres et niveaux ; parties et chapitres ;
   - **listes** : repère les fausses listes tapées à la main (`-`, `*`, `1)`, `a.`, retours à la ligne) et les transforme en vraies listes à puces ou numérotées, **avec les sous-niveaux** ;
   - **tableaux** : texte aligné avec des espaces ou des tabulations, lignes `col1 | col2`, ou énumération répétitive (« Nom : … Âge : … ») transformés en vrai tableau, avec proposition à l'utilisateur ;
   - **figures et images** : elles sont gardées, centrées et redimensionnées, avec une **légende « Figure n : … » en dessous** (tableaux : légende **au-dessus**) et la ligne « Source : … » si elle est présente ;
   - **liens** : les URL et adresses e-mail deviennent cliquables ; « voir tableau 2 » devient un **renvoi cliquable** vers le tableau ;
   - citations longues, notes, encadrés (« NB : », « Remarque : »), définitions ;
   - bibliographie (entrées triées et formatées), sigles (liste générée automatiquement) ;
   - blocs de signature, lieu et date (lettres).
3. **Vérifier l'intégrité** : aucun mot perdu, aucun mot inventé.

### À la demande (assistant ✨)
- Instructions globales : « mets les titres en bleu marine », « interligne 1,5 », « ajoute une liste des figures », « numérote les chapitres en chiffres romains ».
- Instructions sur un bloc sélectionné : « fais un tableau avec ça », « mets en liste », « c'est un sous-titre ».
- Options qui modifient le texte (**toujours signalées et annulables**) : corriger l'orthographe, traduire le résumé en abstract, rédiger un résumé proposé à partir de l'introduction et de la conclusion.
- Techniquement, l'IA ne manipule jamais le document directement. Elle choisit parmi une **liste d'opérations autorisées** (changer un style, changer le type d'un bloc, transformer en tableau…). L'application exécute l'opération, et l'utilisateur peut toujours faire « annuler ».

### Pourquoi c'est fiable
- Ce qui est **sûr** est fait par des règles : typographie, pagination, sommaire, numérotation, légendes.
- Ce qui demande du **jugement** est fait par l'IA : « ce paragraphe est-il un titre ? », « ces lignes forment-elles un tableau ? ».
- L'**humain valide d'un coup d'œil** : questions préremplies, plan, aperçu.

## 6. Les écrans à dessiner (maquettes)

1. Accueil (2 portes)
2. Studio de pages de garde : type → infos → carrousel de styles → palettes
3. Import (coller, fichier, photos + recadrage)
4. Analyse animée
5. Questions intelligentes
6. Éditeur-aperçu + panneau de bloc + assistant ✨
7. Panneaux Style / Plan
8. Aperçu final + paiement (MoMo/OM) + téléchargement
9. Mes documents

Principes visuels : fond clair, beaucoup d'espace, une seule couleur d'accent, gros boutons pour le pouce, aucun menu à la Word, textes en français simple (« Ta page de garde », pas « Configuration de la couverture »).

## 7. Impact sur le planning (remplace le §9 de PLAN.md)

| Semaine | Livrable |
|---|---|
| 1 | Socle : format JSON du document, fichier de thème partagé, rendu Word/PDF serveur (prototype) |
| 2-3 | **Studio de pages de garde** : moteur SVG, 10 designs (Officiel Cameroun + Moderne + Minimal) × palettes, export Word/PDF, paiement Fapshi → **mise en ligne** |
| 4-5 | Import texte/Word, analyse (règles + IA), questions intelligentes, éditeur-aperçu instantané (Paged.js) |
| 6 | Listes, tableaux, figures et légendes, liens et renvois, sommaire et listes ; 6 recettes (stage, mémoire, exposé, rapport pro, lettre/demande, épreuve) → **mise en ligne** |
| 7 | Assistant ✨ (opérations autorisées), panneaux Style et Plan, annuler/rétablir |
| 8-9 | Photos (redressement + OCR + relecture), import PDF, 20 designs de garde supplémentaires |
| 10+ | Nouvelles recettes selon les demandes, modèles par établissement, application Play Store (TWA) |
