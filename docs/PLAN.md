# Plan produit et technique : plateforme de mise en forme automatique de documents (Cameroun)

Version 1, 22/09/2026. Voir aussi `NORMES-CAMEROUN.md` (normes relevées sur de vrais documents) et `prototype/` (test technique qui fonctionne).

## 1. Le produit en une phrase

**« Tu écris ton texte, même sans rien savoir de Word : on te rend un document aux normes de ton école, prêt à imprimer, en Word et en PDF. »**

- 100 % automatique : aucun opérateur humain.
- L'utilisateur fait tout lui-même depuis son téléphone : importer, remplir la page de garde, voir l'aperçu, payer, télécharger.
- Promesse clé : **on ne modifie pas tes mots**. On ne fait que la présentation (le texte d'origine est vérifié automatiquement avant la livraison).

## 2. Web ou mobile ? → **Web mobile (PWA) d'abord**

| Critère | PWA web | Application Android native |
|---|---|---|
| Installation | Aucune : un lien suffit (partage WhatsApp) | Téléchargement depuis le Play Store, frein important |
| Coût | 0 | 25 $ de compte Play Store, publication plus lente |
| Import de fichiers et de photos depuis le téléphone | ✅ via le navigateur | ✅ |
| Utilisable sur PC au cybercafé | ✅ | ❌ |
| Mises à jour | Instantanées | Passage par la validation du Play Store |
| Référencement Google (« page de garde rapport de stage ») | ✅ source de clients gratuite | ❌ |

→ On fait une **PWA** installable (« Ajouter à l'écran d'accueil »). Plus tard, on l'emballe en application Play Store (TWA, sans réécrire le code) si les utilisateurs le demandent.

## 3. Parcours utilisateur (5 écrans)

1. **Accueil** : « Quel document ? » → Rapport de stage / Mémoire / Rapport de projet / Exposé-devoir / Document simple / Page de garde seule / Lettre-demande.
2. **Ton contenu** : importer un Word, un PDF ou des photos, ou coller le texte. Le brouillon est sauvegardé automatiquement.
3. **Ta page de garde** : choix de l'établissement dans une liste (les en-têtes FR/EN et le logo se remplissent automatiquement), puis nom, matricule, encadreur, structure de stage, dates, année. Aperçu en direct.
4. **Ton style** : « Normes de mon école » (préréglage) ou Universitaire / Professionnel / Simple, plus un champ libre pour les consignes (« Times 12, interligne 1,5, marges 2,5 »).
5. **Aperçu → corriger → payer → télécharger** : aperçu page par page avec filigrane, bouton « Demander une modification » (texte libre), paiement Mobile Money, puis téléchargement DOCX + PDF et lien WhatsApp.

## 4. Fonctionnalités par version

### V1 : vendable (objectif : semaines 1 à 5)
- **Générateur de page de garde** (produit d'appel, 300 FCFA), avec 10 à 15 établissements préremplis (UY1 et ses facultés, UY2, Douala, Dschang, Buea, Ngaoundéré, ENS, ENSP, IUT, et un modèle générique pour les instituts privés BTS/HND et les lycées).
- **Mise en forme complète** depuis un Word ou un texte collé :
  - détection automatique de la structure (titres, parties, chapitres, sections, listes, tableaux, légendes, bibliographie), **même sans aucun gras ni style** ;
  - pages préliminaires dans l'ordre camerounais : sommaire, dédicace, remerciements, sigles, listes, résumé, abstract ;
  - sommaire et table des matières automatiques, listes des tableaux et figures, légendes numérotées ;
  - pagination i, ii… puis 1, 2…, en-têtes et pieds de page, chaque chapitre sur une nouvelle page ;
  - nettoyage typographique : espaces doubles, espace insécable avant « : ; ! ? », guillemets « », majuscules des titres, polices et tailles incohérentes.
- Aperçu avec filigrane, **paiement Fapshi**, téléchargement DOCX + PDF.
- Liste des sigles générée automatiquement (détection des « SIGLE : définition » et des « (SIGLE) » dans le texte).

### V2 : semaines 6 à 8
- **Photos et PDF scannés** : redressement des pages, puis lecture du texte (y compris manuscrit) et reconstruction de la structure.
- **Import de PDF numérique** (reconstitution des paragraphes).
- **Corrections par instruction** (« mets les titres en bleu », « supprime la partie 2 », « ajoute une liste des figures »).
- **Consignes personnalisées** en texte libre, ou import du document de consignes de l'école.

### V3 : ensuite, selon les demandes réelles
- Lettres et demandes administratives (formulaire, puis document au format camerounais).
- « Dossier de concours » : photos des pièces transformées en PDF redressé, compressé et assemblé (gratuit, pour attirer du trafic).
- Nouveaux modèles d'établissements, ajoutés au fur et à mesure des demandes.
- Correction orthographique en option, avec LanguageTool auto-hébergé (gratuit et open source).
- Application Play Store (TWA), mode anglais complet pour les anglophones (HND, Buea, Bamenda).

## 5. Architecture

```
 Téléphone / PC (PWA)                 Serveur (VM Oracle gratuite)                Services externes
┌───────────────────────┐          ┌───────────────────────────────────────┐    ┌──────────────────┐
│ Front React/Next      │  HTTPS   │ API FastAPI (Python)                  │    │ Fapshi (paiement)│
│ – formulaires         │────────▶│ – commandes, prix, webhooks paiement  │◀──│  webhook         │
│ – upload + compression│          │ File d'attente (Redis ou Postgres)    │    └──────────────────┘
│   des photos          │          │ Worker Python :                        │    ┌──────────────────┐
│ – aperçu des pages    │◀────────│  1. extraction (docx, pdf, photos)     │──▶│ IA gratuite :    │
└───────────────────────┘          │  2. détection de structure             │    │ Gemini Flash     │
                                    │  3. document interne (JSON)            │    │ (vision + texte),│
                                    │  4. rendu DOCX (python-docx)           │    │ Groq en secours  │
                                    │  5. LibreOffice : index + PDF          │    └──────────────────┘
                                    │  6. aperçu PNG avec filigrane          │
                                    │ Fichiers sur disque (supprimés à J+7)  │
                                    │ Postgres (commandes, établissements)   │
                                    └───────────────────────────────────────┘
```

### Le cœur : le document interne (JSON)

Toute la plateforme tourne autour d'une représentation unique :

```json
{
  "type": "rapport_stage",
  "garde": { "etablissement_id": "uy2-esstic", "titre": "...", "auteur": "...", "matricule": "...", "encadreurs": [...], "annee": "2025-2026" },
  "style": { "preset": "uy2-esstic", "police": "Times New Roman", "taille": 12, "interligne": 1.5, "marges": [2.5, 2.5, 3, 2.5], "numerotation": "francaise" },
  "prelim": ["sommaire", "dedicace", "remerciements", "sigles", "liste_tableaux"],
  "blocs": [
    { "id": 1, "role": "titre", "niveau": 1, "texte": "INTRODUCTION", "source": [0] },
    { "id": 2, "role": "paragraphe", "texte": "...", "source": [1] },
    { "id": 3, "role": "tableau", "cellules": [[...]], "legende": "Moyens humains", "source": [5, 6] }
  ]
}
```

- L'**extraction** remplit `blocs`. La **détection** remplit `role` et `niveau`. Le **formulaire** remplit `garde` et `style`.
- Le **rendu** est 100 % déterministe (sans IA) : un même JSON donne toujours le même document.
- Les **corrections** sont de petites modifications du JSON (voir 5.4). Rien ne se casse puisqu'on régénère tout.

### 5.1 Détection de la structure quand l'utilisateur n'a rien formaté

C'est la partie la plus importante. Elle se fait en 3 étages, du moins cher au plus cher :

**Étage 1 : règles (gratuit, instantané, environ 80 % des cas)**
- Mots-clés connus (FR/EN) : dédicace, remerciements, avant-propos, sommaire, sigles, résumé, abstract, introduction (générale), première partie, chapitre, section, conclusion (générale), recommandations, bibliographie, références, webographie, annexes…
- Motifs de numérotation : `I.`, `II-`, `A.`, `1.`, `1.1`, `1.1.1`, `a)`, `i.`, `CHAPITRE 2`, `PARTIE I`, et puces écrites à la main (`-`, `*`, `•`, `➢`, `o`).
- Indices de forme : ligne courte sans point final, MAJUSCULES, ligne isolée entre deux lignes vides, gras ou taille plus grande (si c'est un Word), position (au début du document, juste après un titre de partie).
- Légendes : `Tableau 3 :`, `Figure 2 -`, `Source :`, `Graphique`.
- Bibliographie : lignes qui commencent par `NOM, P.` ou contiennent une année entre parenthèses.
- Chaque bloc reçoit une étiquette avec un **score de confiance**.

**Étage 2 : IA, uniquement sur les cas incertains (gratuit dans les limites des offres)**
- On n'envoie **pas tout le texte**, seulement une liste compacte des blocs, par exemple `id | 120 premiers caractères | indices | étiquette proposée | confiance`. Ça coûte environ 20 fois moins de tokens, et l'IA ne peut pas réécrire le contenu.
- L'IA renvoie du JSON validé par un schéma : `[{id, role, niveau}]`, le type de document détecté et les sections manquantes.
- Les documents longs (100 pages et plus) sont découpés en morceaux d'environ 300 blocs avec un contexte des titres précédents.

**Étage 3 : cohérence (gratuit)**
- La hiérarchie est vérifiée : Partie > Chapitre > Section > Sous-section, sans saut de niveau.
- La numérotation est harmonisée selon le style choisi (français I/A/1/a ou décimal 1/1.1/1.1.1). L'ancienne numérotation tapée à la main est retirée pour éviter les doublons.
- **Contrôle d'intégrité** : 100 % des mots du document source doivent se retrouver dans la sortie. Sinon, on bloque et on ne livre pas.

L'utilisateur voit un écran « Plan détecté » (l'arbre des titres) et peut monter ou descendre un titre d'un tap avant la génération. C'est simple et évite l'essentiel des erreurs.

### 5.2 Photos et écriture manuscrite

1. **Dans le téléphone** : compression de l'image (environ 1 600 px, JPEG) pour économiser les données mobiles.
2. **Sur le serveur (OpenCV, gratuit)** : détection des bords de la feuille, correction de la perspective, redressement, contraste. On obtient une « page scannée » propre.
3. **Lecture du texte (OCR)** :
   - Texte imprimé : Tesseract (gratuit, local, aucune donnée envoyée ailleurs) en premier essai.
   - Texte manuscrit ou résultat de mauvaise qualité : Gemini Flash (vision, offre gratuite). Consigne donnée à l'IA : « transcris fidèlement, sans corriger ni reformuler ; marque les titres ; tableaux en Markdown ; `[illisible]` si tu ne peux pas lire ».
4. Le texte obtenu passe ensuite par la même détection de structure (5.1).
5. **Écran de relecture obligatoire** avant la mise en page : l'utilisateur voit le texte lu à côté de la photo et corrige les mots mal lus. C'est ce qui garantit la qualité sans opérateur humain.

### 5.3 Rendu Word et PDF (validé par le prototype)

- `python-docx` génère le fichier Word :
  - vrais styles de titres, sections séparées (préliminaires en chiffres romains, corps en chiffres arabes) ;
  - page de garde sous forme de tableau à 2 ou 3 colonnes (FR | logo | EN) ;
  - légendes numérotées automatiquement (champs `SEQ`) ;
  - marqueurs aux endroits où iront le sommaire, la table des matières et les listes.
- LibreOffice sans interface, piloté par un script, **insère les vrais index, calcule les numéros de page et exporte le PDF**. Test réel : **1,65 seconde** (voir `prototype/`).
- Le fichier Word livré garde de vraies tables des matières, que l'étudiant peut encore mettre à jour dans Word.
- Aperçu : `pdftoppm` transforme les pages en PNG, avec un filigrane incrusté côté serveur. Le PDF propre n'est jamais envoyé avant paiement.

### 5.4 Corrections par instruction

L'IA traduit la phrase de l'utilisateur en **opérations autorisées uniquement** :
`set_style(param, valeur)`, `set_role(bloc, role, niveau)`, `supprimer(blocs)`, `deplacer(bloc, apres)`, `ajouter_prelim(type, texte)`, `changer_numerotation(style)`, `modifier_garde(champ, valeur)`.
On applique l'opération, on régénère et on montre le nouvel aperçu. Si la demande est impossible, on répond : « Je n'ai pas compris, essaie : … ».

## 6. Technologies (coût 0, sauf le nom de domaine)

| Couche | Choix | Pourquoi | Coût |
|---|---|---|---|
| Front | **Next.js (export statique) ou React + Vite, PWA**, Tailwind | Tu connais déjà Next.js (chess-trainer) et les PWA (nkul) | 0 |
| Hébergement du front | **Cloudflare Pages** | Gratuit et usage commercial autorisé (l'offre gratuite de Vercel, Hobby, interdit l'usage commercial) | 0 |
| API + worker | **Python 3.12, FastAPI**, python-docx, PyMuPDF, OpenCV, Tesseract | Les meilleures bibliothèques pour Word, PDF et images sont en Python | 0 |
| Conversion | **LibreOffice sans interface + script UNO** | Index, pagination, export PDF (prouvé) | 0 |
| Serveur | **Oracle Cloud Always Free** (ARM, 2 cœurs et 12 Go de RAM depuis juin 2026, 200 Go de disque), avec Docker | Assez pour LibreOffice, OpenCV et la file d'attente | 0 |
| Base de données | Postgres sur la VM (ou Supabase gratuit) | Commandes, établissements, paiements | 0 |
| File d'attente | Redis + RQ (ou une simple table Postgres) | Traitements longs en arrière-plan | 0 |
| IA texte | **Gemini Flash (offre gratuite)**, Groq `gpt-oss-120b` en secours (1 000 requêtes par jour) | Le fournisseur doit rester interchangeable : les offres gratuites changent souvent | 0 |
| IA vision | Gemini Flash (offre gratuite) | Lecture de l'écriture manuscrite | 0 |
| Paiement | **Fapshi** (3 %, démarrage possible sans registre de commerce), CamPay plus tard (2 %) | Mobile Money MTN et Orange | Commission seulement |
| Comptes | Aucun compte obligatoire : chaque commande a un lien secret. Option : connexion Google | Pas de frein à l'entrée | 0 |
| Suivi | Sentry (gratuit), Cloudflare Web Analytics | Erreurs et trafic | 0 |
| Domaine | Un .com | Crédibilité | Environ 10 $ par an (seul coût) |

⚠️ **Données personnelles** : l'offre gratuite de Gemini peut utiliser les données envoyées pour entraîner les modèles. Il faut donc : (1) l'écrire clairement dans les CGU, (2) préférer Tesseract et les règles quand c'est possible, (3) passer à l'offre payante de l'IA dès les premiers revenus (quelques FCFA par document). Les fichiers sont supprimés automatiquement après 7 jours.

## 7. Prix (à tester)

| Produit | Prix |
|---|---|
| Page de garde seule (Word + PDF) | 300 FCFA |
| Document simple ou exposé (jusqu'à 15 pages) | 1 000 FCFA |
| Rapport de stage ou de projet | 2 000 FCFA |
| Mémoire (plus de 40 pages) | 3 000 FCFA |
| Photos → texte (en plus) | +50 FCFA par page |
| Pass 30 jours en illimité (pour les cybercafés et les étudiants qui modifient souvent) | 5 000 FCFA |

- Les corrections sont gratuites pendant 48 heures après le paiement, ce qui rassure le client.
- L'aperçu est toujours gratuit.

## 8. Qualité sans humain : comment on s'en assure

- **Corpus de test** : 40 vrais documents mal formatés (demandés à des étudiants, avec leur accord), annotés à la main (le rôle de chaque paragraphe).
- **Indicateurs automatiques à chaque modification du code** :
  - 100 % du texte conservé ;
  - précision de la détection des titres ≥ 95 % avant d'ouvrir une fonctionnalité au public ;
  - document généré sans erreur et index remplis.
- Garde-fous côté utilisateur : l'écran « Plan détecté », l'écran de relecture de l'OCR, et l'aperçu avant paiement.
- Bouton « Signaler un problème » sur l'aperçu. Les documents signalés rejoignent le corpus de test.

## 9. Planning (seul, en visant un lancement rapide)

| Semaine | Livrable |
|---|---|
| 1 | Dépôt Git, VM Oracle + Docker (LibreOffice, Python), document interne JSON, rendu de base (à partir du prototype) |
| 2 | **Générateur de page de garde** : 5 établissements, formulaire, aperçu, paiement Fapshi (sandbox puis réel) → **mise en ligne, premiers revenus** |
| 3 | Import DOCX et texte collé → blocs ; détection par règles (étage 1) ; écran « Plan détecté » |
| 4 | Pages préliminaires, sommaire et table des matières, listes, légendes, en-têtes et pieds de page ; modèles Rapport de stage, Mémoire, Simple |
| 5 | Étage IA (Gemini/Groq), contrôle d'intégrité, corpus de test → **mise en ligne de la mise en forme complète** |
| 6 | Corrections par instruction ; consignes personnalisées |
| 7-8 | Photos (OpenCV + OCR + relecture), import PDF |
| 9+ | Lettres et demandes, dossier concours, nouveaux établissements, TWA Play Store |

## 10. Premiers clients (sans budget)

- **Maintenant (saison des rapports de stage)** : publier dans les groupes WhatsApp et Facebook d'étudiants (ESSTIC, FSE, FALSH, IUT, instituts BTS) le message : « Ta page de garde aux normes de ton école en 2 minutes, 300 FCFA ».
- **Vidéos TikTok « avant / après »** : un texte brut collé devient un rapport propre avec sommaire et page de garde.
- **Délégués de classe ambassadeurs** : un code promo qui leur rapporte 20 % par vente (payé via Fapshi).
- **Référencement Google** : une page par établissement (« Page de garde rapport de stage ESSTIC », « Canevas mémoire FSE UY1 »…). Ce sont les recherches que les étudiants font déjà.
- **Cybercafés** : le pass de 30 jours leur permet de traiter les documents de leurs propres clients plus vite.

## 11. Risques principaux et réponses

| Risque | Réponse |
|---|---|
| Structure mal détectée sur un texte très brouillon | Écran « Plan détecté » modifiable + aperçu gratuit avant paiement |
| Limites des offres d'IA gratuites | Les règles d'abord (l'IA ne sert que pour les cas incertains), deux fournisseurs, passage à l'offre payante financé par les premières ventes |
| Normes différentes selon l'école | Modèles paramétrables + champ de consignes libre ; chaque établissement demandé devient un modèle |
| Capacité de la VM Oracle (2 cœurs) | File d'attente, environ 2 secondes par rendu, soit des milliers de documents par jour : largement suffisant au début |
| Fraude académique | On ne rédige jamais : on présente seulement le texte de l'étudiant (c'est inscrit dans les CGU) |
