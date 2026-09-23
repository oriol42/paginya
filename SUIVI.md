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

## Plan IA pour la détection du plan (validé le 23/09/2026, à faire après le moteur Affichya)
L'idée de l'utilisateur : fabriquer des documents « mal faits » à partir de documents bien faits. C'est la bonne méthode (données synthétiques). Elle donne des milliers d'exemples étiquetés gratuitement, sans attendre les utilisateurs.
1. **Documents « vérité »** (on connaît la vraie structure) :
   - DOCX et PDF en accès libre, avec de vrais styles de titres et une licence qui permet la réutilisation (ex. CC-BY) : dépôts de thèses et mémoires (HAL, DUMAS, dépôts universitaires) ;
   - plus des documents qu'on génère nous-mêmes à partir de nos modèles (rapport de stage, mémoire, lettre) et de textes libres.
   On ne garde que des caractéristiques, jamais le texte, et on ne redistribue rien.
2. **Dégradation automatique**, comme le font vraiment les étudiants :
   - styles supprimés et titres faits « à la main » (gras + taille) ;
   - numérotation tapée à la main (I., 1.1, A-) et puces « - » ou « • » tapées ;
   - sommaire tapé à la main avec des points, légendes au mauvais endroit ;
   - polices et tailles au hasard, retours à la ligne cassés (copier-coller d'un PDF ou de WhatsApp) ;
   - photos OCR (Tesseract) de pages imprimées.
   Chaque document donne des dizaines de variantes, ce qui fait des milliers de paires (mal fait → vérité).
3. **Modèle** : mieux que scikit-learn seul.
   - **LightGBM** (gratuit, rapide sur CPU) sur les caractéristiques du paragraphe **et de ses voisins** (contexte).
   - Puis une passe de **cohérence de la hiérarchie** (Viterbi / CRF) : pas de niveau 3 juste après un niveau 1, numérotation continue.
   - Plus tard, si besoin : un petit modèle de texte (MiniLM ou CamemBERT-small en ONNX, CPU) pour les cas où seule la phrase permet de décider.
4. **Évaluation** : un jeu de vrais documents camerounais mal faits, corrigés à la main une fois, sert de juge. Le modèle ne remplace les règles que s'il fait mieux (score par type : titre N1/N2/N3, légende, liste, corps). Les règles restent en secours.
5. **Bonus** : le même modèle devine le **type de document** (rapport de stage, mémoire, lettre, CV) pour choisir le style tout seul.
