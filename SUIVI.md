# SUIVI : où on en est (à lire en premier pour reprendre)

Dernière mise à jour : 23/09/2026 (soir). Tenir ce fichier à jour à la fin de chaque session de travail.

## 1. Le fondateur et les règles du jeu

- Fondateur solo, au Cameroun, **budget 0 FCFA** : que du gratuit ou du libre (offres gratuites acceptées, jamais de carte bancaire).
- **Aucune intervention manuelle** dans les produits : l'app fait tout toute seule.
- Paiement : **Fapshi** (compte existant, utilisé aussi par son autre app utiny), mode **demande directe** (`direct-pay`).
- Mise en ligne et vraies clés Fapshi : **à la fin**, quand les produits sont finis.
- Il communique en français familier, en tutoiement. Il veut du **moderne, stylé, simple, qui fait « waouh »**.
- Rôle attendu de Claude : **chef de projet**. Il fait les études, décide, code, teste, et documente.

## 2. Les projets

| Projet | Dossier | État |
|---|---|---|
| **Paginya** (ex-« Propre », renommage du code à faire) : mise en forme de documents + pages de garde | `Documents/propre/` | MVP bien avancé (voir §3) |
| **Affichya** : affiches + vidéos pub à partir de quelques mots | `Documents/affichya/` | Première version faite (affiches + vidéos MP4 avec musique), voir son `SUIVI.md`. Clients : utiny et Paginya |
| **utiny** (autre app du fondateur, déjà en ligne) | GitHub `oriol42/dotme` · `utiny-app.vercel.app` | « Buy Me a Coffee » camerounais : page créateur, mur de dons en direct, objectif, top supporters, MoMo/OM, 13 % de commission. React + Vite + Supabase + Fapshi. Identité : ambre `#f2a93b`, corail `#ff6b57`, crème `#fbf9f5`, texte `#1c1712`, polices Sora + Inter |

## 3. Propre : ce qui est fait

**Documents de référence (`docs/`)** : `DECISIONS.md` (fait foi), `PLAN.md`, `FONCTIONNEMENT-APP.md`, `NORMES-CAMEROUN.md` (normes relevées sur 10 vrais mémoires et rapports), `RECHERCHES-PAIEMENT-STYLES.md`, `ETUDE-UX.md`, `JURIDIQUE.md` (lois 2024/017 et 2010/021), `CHECKLIST-SAAS.md` (état détaillé ✅/🟡/⬜).

**Lancer :** `./dev.sh` → site http://localhost:3000 · API http://localhost:8000 (`/docs`). Paiement simulé : un numéro finissant par 0 est payé, par 1 échoue.

**Pages du site (`web/`, Next.js 16 + Tailwind 4, PWA) :**
- `/` : accueil (avant/après réel, fonctionnalités, FAQ, sans prix).
- `/garde` : studio de pages de garde, parcours en 3 étapes (L'essentiel → Détails facultatifs → Style). 4 styles (Officiel Cameroun, Moderne, Corporate, Élégant) × 5 palettes, noir et blanc, logo, 14 établissements préremplis (en-têtes FR/EN). Rendu SVG dans le navigateur (`src/lib/cover/`).
- `/document` : mise en forme. Import par **fichier** (docx/pdf/txt), **photos** ou **texte collé**, puis analyse animée, puis éditeur :
  - panneaux Style (6 thèmes avec vraies miniatures), Page de garde (incluse par défaut, en-tête bilingue) et Plan ;
  - vues Après / Avant / Côte à côte, carte « Ce que Propre a fait » ;
  - paiement, puis téléchargement Word + PDF.
- `/outils/video` : générateur de vidéos TikTok pour Propre (MP4 1080×1920, 15 s, enregistré par le navigateur). À déplacer vers le générateur de pubs.
- `/tarifs`, `/cgu`, `/confidentialite`, `/mentions-legales` : les infos de l'éditeur sont marquées **[À COMPLÉTER]** (aussi dans `web/src/components/Footer.tsx`).
- `/lettre` : lettres et demandes (formulaire à gauche, vrai document à droite, mis à jour en tapant).
- `/epreuve` : épreuves d'enseignants (même principe).
- `/dev/covers` : bac à sable des styles de pages de garde (en développement seulement).

**API (`api/`, FastAPI, Python 3.12) :**
- `app/main.py` : commandes, paiement Fapshi (`app/fapshi.py` : direct-pay, vérification de statut, webhook `x-wh-secret`, mode `mock`), téléchargements réservés aux commandes payées, nettoyage automatique toutes les heures.
- `app/doc/` : moteur de documents.
  - `extract.py` : docx (styles, gras, tailles, listes Word, tableaux, images), PDF (pdftotext), texte.
  - `detect.py` : structure par règles (parties, chapitres, I./A./1.1, listes tapées à la main, tableaux à tabulations, légendes remises au-dessus/au-dessous selon les normes, sigles, dédicace, bibliographie, ancien sommaire supprimé, niveaux relatifs, titre deviné, liste « changements »).
  - `render.py` : Word via python-docx, 6 thèmes, sections i/ii puis 1/2, légendes `SEQ`, liens cliquables, page de garde en image.
  - `uno_worker.py` + `office.py` : LibreOffice sans interface (lancé avec le **python du système**, qui a `uno`) insère les vrais sommaire, table des matières et listes des tableaux/figures, exporte le PDF, puis `pdftoppm` fait les aperçus avec filigrane.
  - `scan.py` : photos → redressement OpenCV (détection de la feuille + perspective + éclairage) → lecture du texte.
- `app/doc_routes.py` : `/documents` (créer, modifier, rendre, pages, avant, supprimer), `/scans`, nettoyage (contenus supprimés 7 jours après paiement ou création, photos 24 h, tout effacé après 12 mois).
- `app/forms/` + `app/forms_routes.py` : lettres (`letter.py`) et épreuves (`exam.py`), route `/forms`.
- Prix côté serveur (`pricing.py`) : page de garde 300, lettre 300, épreuve 500, document ≤ 15 pages 1 000, rapport 16-40 pages 2 000, mémoire > 40 pages 3 000.

**Tests :**
- `cd api && .venv/bin/python -m pytest` → **28 tests** (+ lettres, épreuves, Tesseract) (parcours complet texte → paiement → téléchargement, docx avec images, photo redressée, avant/après, suppression, nettoyage, thèmes).
- `cd web && npx tsc --noEmit && npx eslint src`.
- Tests navigateur scriptés : `web/e2e/*.mjs`. Ils pilotent Chrome sans interface via le protocole de débogage, avec Node 24 : `SCRATCH=/tmp node web/e2e/doc_flow.mjs`. Les serveurs doivent tourner.

## 4. Propre : reste à faire (dans l'ordre)

1. ✅ **Photos** : Tesseract local par défaut (installé, fra+eng), Gemini seulement pour le manuscrit, avec consentement ; lignes recollées en paragraphes.
2. ✅ **Lettres et demandes** (`/lettre`, 300 F) : 6 types avec modèles de texte administratif, timbre fiscal en option, s/c, P.J.
3. ✅ **Épreuves** (`/epreuve`, 500 F) : en-tête MINESEC, barème aligné à droite et total vérifié (20 pts), QCM, sous-questions, pagination x/y.
4. ✅ **Renommage visible en Paginya** (logo, textes, filigranes, fichiers). Restent internes : le nom du dossier `propre/`, les clés `propre:` du stockage navigateur, les variables `PROPRE_*`.
5. **Affichya : première version faite ✅** (voir `Documents/affichya/`).
6. Plus tard pour Paginya : assistant ✨, « Mes documents », ajustement manuel des coins des photos, CV.
6. À la mise en ligne : serveur (Oracle gratuit ou hébergeur local), Docker, domaine, clés Fapshi, activation de direct-pay, Sentry, autorisation de transfert auprès de l'Autorité de protection des données.

## 5. Pièges connus (pour Claude)

- **Ne jamais utiliser `pkill -f <motif>` quand le motif figure aussi dans la commande elle-même** : ça tue le propre shell (code 144). Utiliser `kill $(pgrep ...)` dans une commande à part, ou `pkill -x soffice.bin`.
- LibreOffice : le script UNO tourne avec `/usr/bin/python3` (pas le venv). Pipe nommé `propre_lo`, profil dans `api/data/lo-profile`.
- Next 16 : lire `web/node_modules/next/dist/docs/` avant d'utiliser une API (fichier `web/AGENTS.md`).
- Réseau lent : `npm install` et `pip install` peuvent échouer. Relancer avec des délais d'attente longs.
- Polices des pages de garde : Poppins, Tinos (≈ Times), Playfair, Inter dans `api/fonts/` **et** `web/public/fonts/` (identiques, pour que l'aperçu = le fichier).
- Rien n'est encore commité dans git (dépôt initialisé, 0 commit).

## 6. Générateur de pubs : prochaines étapes

Voir `Documents/affichya/PLAN.md` et son `SUIVI.md`. On démarre après avoir fini les points 1 à 3 de Propre. Premier livrable : les vidéos et affiches pour **utiny** et Propre.

## 7. Noms (décidés le 23/09/2026)

- **Paginya** (documents) et **Affichya** (pubs) : une famille de noms en « -ya », originaux et faciles à retenir.
- Domaines **libres** au 23/09/2026 (vérifiés par RDAP) : paginya.com, paginya.app, affichya.com, affichya.app. Le .cm est à vérifier chez un registraire camerounais.
- Noms écartés parce que déjà utilisés : Nyanga (Nyanga Pay), Kongoss (Kongoss Geek), Lokole (plusieurs apps), Buzzya (appli VoIP), Folyo, Repasso, Tamba.

## 8. Ordre de travail décidé

1. ✅ Finir Paginya : Tesseract, lettres/demandes, épreuves, renommage (fait le 23/09).
2. Affichya, en commençant par les pubs utiny et Paginya.
3. Mise en ligne des deux, puis Fapshi réel.

## IA de détection du plan (faite le 23/09/2026) ✅
- **Données synthétiques** (`api/ml/synth.py`) : on part de documents « bien faits », dont on connaît la vraie structure (spéciaux, parties, chapitres, sections jusqu'au niveau 4, listes, légendes, sommaire tapé).
  - Une « habitude d'auteur » aléatoire les abîme : styles Word, ou bien gras, taille et majuscules à la main, numérotations tapées (CHAPITRE I, I., A., 1., 1.1, « 1 » sans point, a)), puces tapées, paragraphes en gras, mise en forme oubliée, tailles 11/12/14.
  - Le document est produit en DOCX ou en texte collé, puis passe par la **vraie extraction** de Paginya.
- Mesure : `python -m ml.evaluate 300`. Entraînement : `python -m ml.train 2500` (~6 min CPU).
- **Résultats** (300 documents de validation, ~31 000 paragraphes) :
  - Règles d'origine : 91,4 % des paragraphes justes, niveau de titre juste 75 %.
  - **4 bugs de règles corrigés** : 97,4 % / 92,4 %. Les voici :
    1. Une partie ou un chapitre en style Word « Titre 1/2 » sortait un niveau trop bas après l'introduction.
    2. Les légendes « Tab. / Fig. / Graph. » n'étaient pas reconnues.
    3. Les titres « 1 Historique » (sans point) étaient ratés.
    4. « 2. Titre » en gras juste après une liste à puces était pris pour un élément de liste.
  - **Règles + modèle : 99,7 % / 99,1 %** (titres trouvés 99,9 %).
  - Vérification de généralisation (`SYNTH_SPLIT=train`) : entraîné sur la moitié du vocabulaire, testé sur l'autre moitié et sur de vraies phrases, on obtient 99,2 %. Le modèle a appris la mise en forme, pas les mots.
- **Modèle** (`app/doc/ml.py`, `structure_model.npz`, 84 Ko) : petit réseau de neurones en numpy (pas de scikit-learn, pas de GPU, <1 ms/doc).
  - Il voit le paragraphe, ses voisins, les habitudes du document et **la décision des règles** (empilement). Il ne corrige que s'il est sûr (seuil enregistré avec le modèle).
  - Garde-fous : les spéciaux, parties, chapitres et puces ne sont jamais modifiés par le modèle. Les titres promus depuis « 2. xxx » gardent leur numéro.
  - Sans le fichier modèle, Paginya marche comme avant (règles seules).
- Tests : `tests/test_ml.py` et les 28 tests d'avant, soit 31 au vert.
- **Nettoyage automatique** (`app/doc/clean.py`, 23/09/2026) :
  - paragraphes coupés par un « Entrée » recollés ;
  - **énumérations sans puces** (« … les suivantes : » + lignes courtes) transformées en listes. Ça se fait avant le modèle, qui ne peut plus les transformer en titres ;
  - listes harmonisées selon la règle française : fragments en minuscule avec « ; », le dernier avec « . » ; phrases avec majuscule et « . » ;
  - **majuscules** : début de phrase, après un point (sauf abréviations), textes et titres de section tout en CAPITALES remis normalement. Les sigles vus dans le document et les villes sont gardés, les accents perdus sont rétablis (PRESENTATION → Présentation, « A DOUALA » → « à Douala »). Les chapitres et parties restent en capitales, comme le demandent les normes ;
  - **typographie française** à l'écriture du Word : espaces, espace insécable avant « : ; ! ? », « guillemets », (parenthèses) ;
  - le texte justifié était déjà géré par les styles ;
  - chaque correction apparaît dans la carte « Ce qu'on a changé » ;
  - tests : `tests/test_clean.py`. Le générateur produit aussi des énumérations sans puces. Mesure : 99,5 %.
- À faire quand internet revient :
  - comparer avec **LightGBM** ;
  - ajouter de **vrais documents** en accès libre (thèses et mémoires HAL/DUMAS, licence CC-BY) comme source de documents « vérité » ;
  - constituer un petit jeu de vrais documents camerounais corrigés à la main, qui servira de juge final.
