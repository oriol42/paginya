# SUIVI : où on en est (à lire en premier pour reprendre)

Dernière mise à jour : 25/09/2026 (après-midi). Tenir ce fichier à jour à la fin de chaque session de travail.

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

## Refonte UI (23/09/2026)
- **Écran du document** (`components/doc/DocumentApp.tsx`), sur le modèle de Google Docs et Canva :
  - barre du haut : titre, Après / Avant / Côte à côte, pastille « ✨ N corrections » (liste façon Grammarly), bouton **Télécharger** en haut à droite ;
  - rail d'outils à gauche (Style, Garde, Plan, menu ⋯ avec « Nouveau » et « Supprimer ») et son panneau ;
  - pages centrées sur un fond gris « bureau », plus grandes (760 px) ;
  - sur téléphone : **une seule rangée en bas** (3 outils + Télécharger) et un tiroir qui laisse voir la page ;
  - la grosse carte verte des corrections a été retirée ;
  - style : miniatures en 2 colonnes, plus lisibles.
- **Lettre** (`forms/LetterForm.tsx`) : **4 étapes** (Type → Toi → Destinataire → La lettre). Le type fait passer à l'étape suivante, les champs facultatifs sont repliés (« + Plus de détails »), l'aperçu est toujours à portée.

## Hébergement sans carte bancaire (préparé le 24/09/2026)
Oracle refuse les cartes virtuelles, et l'utilisateur n'a pas de carte bancaire classique. Le plan retenu, 100 % gratuit :
- **Site** : export statique (`output: "export"` dans `next.config.ts`, dossier `out/`) sur **Vercel**. Vercel gratuit interdit en principe l'usage commercial : passer sur Cloudflare Pages quand les ventes démarrent (même dossier `out/`).
- **API** : **Hugging Face Spaces** (Docker, 16 Go). Le Space public ne contient qu'un `Dockerfile` qui récupère le code dans le dépôt GitHub **privé**, grâce au secret de build `GITHUB_TOKEN`. Kit dans `Documents/serveur/hf/`.
- **Données** : **Supabase**. Postgres via `DATABASE_URL` : un seul projet pour les deux applis, chacune dans son schéma (`DB_SCHEMA`). Les fichiers durables vont dans Supabase Storage (`app/storage.py`).
  - Le disque de Hugging Face est effacé à chaque redémarrage : c'est seulement un cache.
  - Ce qui ne peut pas être reconstruit (fichier d'origine, images, photos) est dans Storage. Le reste est reconstruit à la demande.
- **Code** : `app/sqlcompat.py` fait tourner le même SQL sur SQLite (local, tests) et Postgres (production).
- **Maintien en éveil** : `/health` touche la base toutes les 6 h, via GitHub Actions (`.github/workflows/keepalive.yml`) et via une tâche Supabase (pg_cron + pg_net). Hugging Face dort après 48 h sans visite, Supabase se met en pause après 7 jours.
- **Déployer** : remplir `Documents/serveur/.env` (modèle `env.example`), puis `./deploy_nocard.sh`.
- **Pas encore testé en vrai** avec Postgres/Supabase et Hugging Face (pas de réseau le 24/09). Premier test à faire dès que les comptes sont prêts.

## EN LIGNE depuis le 25/09/2026 ✅
- Site : **https://paginya.vercel.app** · Serveur : https://paginya-api.onrender.com (Render gratuit, Virginie) · Base et fichiers : Supabase (us-east-1).
- Hugging Face abandonné : les serveurs Docker gratuits y sont devenus payants (PRO 9 $/mois).
- Tout est décrit dans `Documents/serveur/README.md` : déployer une nouvelle version, test en ligne `check/prod_check.mjs`, limites du gratuit.
- Test en ligne réussi le 25/09/2026. Paginya : document mis en page en ~80 s, réveil compris. Affichya : boutique, pub gratuite, lien suivi, vitrine, WhatsApp et voix off OK.
- Corrections faites pendant la mise en ligne :
  - polices en WOFF2 (844 → 184 Ko) et affichage jamais bloqué par les polices ;
  - bibliothèque des personnages chargée à la demande (/app : 2,7 Mo → 0,7 Mo de JS) ;
  - chargements limités dans le temps ;
  - les boutons attendent les images au lieu de ne rien faire.
- Données de test supprimées : les applis démarrent vides.
- **À faire** : changer les clés passées dans la conversation (GitHub, Render, Supabase service_role, Hugging Face à supprimer) ; clés Fapshi réelles (mode `mock` pour l'instant) ; nom de domaine ; Cloudflare Pages dès les premières ventes.


## Vraie mise en page, types de document, en-tête officiel (25/09/2026) ✅

Point de départ : le fondateur a importé un cours en Markdown (`cours_module1_notions_faibles.md`). Résultat : `#` et `**` restés bruts, sommaire rempli de lignes SQL, 26 pages avec couverture et un chapitre par page.

- **Import Markdown fidèle** (`extract.from_markdown`). Un `.md`, ou un texte collé qui ressemble à du Markdown (`looks_like_markdown`), garde sa structure : titres `#`, listes, tableaux `|`, blocs de code (police à chasse fixe sur fond gris), citations `>`, `---` supprimé. Le gras, l'italique et le `code` deviennent de vrais styles Word (`render.inline_spans`, aussi dans les cellules de tableau). Un `# Titre` unique en tête devient le titre du document (et le titre juste en dessous, son sous-titre). Les blocs Markdown sont `explicit` : le modèle et les règles de devinette n'y touchent pas.
- **Type de document au choix** (panneau Style → « C'est quoi, ce document ? »). Types : document, cours, exposé, lettre/administratif, rapport, rapport de stage, mémoire. Chaque type n'ajoute que ses pages (`render.KINDS`, `options_for`) ; plus aucun sommaire imposé. L'API détecte un type par défaut (`detect._meta` : cours, administratif…) ; `PUT /documents/{id}` accepte `kind`.
- **Interrupteurs visibles** « Ce que Paginya ajoute » : sommaire, table des matières, chaque grand titre sur une nouvelle page (`chapter_pages`), listes des tableaux/figures, numéros de page.
- **En-tête officiel sur la 1re page** (`letterhead`) : colonne FR | logo | colonne EN, séparateurs `********`, devise en italique. Réglages : établissement, République, ministère (MINESUP, ou MINESEC pour un lycée), logo ou armoiries. Composant `LetterheadPanel.tsx`. Rendu Word : `Builder.letterhead`, tableau sans bordure. Nettoyage côté API : `_clean_letterhead`.
- **Logos** : 25 établissements + armoiries du Cameroun dans `web/public/logos/`, sources dans `docs/LOGOS.md` (retrait sur demande). `institutions.ts` passe de 14 à 49 établissements. Le logo se met tout seul quand on choisit l'école, sur la page de garde comme sur l'en-tête.
- **Étude de documents réels** : `docs/ETUDE-DOCUMENTS.md`, script `api/ml/study/real_reports.py`. Sur 13 rapports de Memoire Online, la précision des titres passe de 0,58 à 0,82 et le rappel de 0,83 à 0,93 ; le banc synthétique ne bouge pas (97,5 %). Correctifs : sommaires « P.03 », `SECTION I`, « 3. TERME : définition », éléments en « ; » jamais promus en titre.
- Tests : 52 (dont `tests/test_markdown.py`). Vérification navigateur : `serveur/check/md_check.mjs <fichier.md>` (API et site lancés en local).

**Reste (Paginya), dans l'ordre**
1. Notes de bas de page collées dans le texte, prises pour des titres.
2. Paragraphes coupés dont la suite commence par une majuscule.
3. Logos manquants : Ngaoundéré, ENSAI, Ebolowa, SUP'PTIC, ISSEA, IUC, Siantou, UPAC.
4. Retenter DICAMES (PDF de mémoires CAMES) pour élargir l'étude.

## Référencement Google (26/09/2026), en attente de mise en ligne
- Ajoutés : `robots.txt` et `sitemap.xml` (`src/app/robots.ts`, `sitemap.ts`), titres et descriptions, image de partage `public/og.png` (1200×630), fiche « WebApplication » (JSON-LD) dans `layout.tsx`. Idem pour Affichya.
- Adresse du site : `src/lib/site.ts` (`NEXT_PUBLIC_SITE_URL`, à changer le jour où on achète un nom de domaine).
- Google Search Console : mettre le code de la méthode « balise HTML » dans `NEXT_PUBLIC_GOOGLE_VERIFICATION` au moment du build, puis soumettre `/sitemap.xml`.
- Le jeton Vercel a expiré le 26/09 : il faut en créer un nouveau (sans date d'expiration) avant `python3 deploy_render.py web`.

## Déménagement sur Cloudflare (28/09/2026) ✅
- **Sites** : https://paginya.pages.dev et https://affichya.pages.dev (Cloudflare Pages : gratuit, usage commercial autorisé, trafic illimité). L'offre gratuite de Vercel interdit l'usage commercial.
- **Anciennes adresses** `*.vercel.app` : redirection permanente (308) vers les nouvelles, page par page. Script : `serveur/deploy_cloudflare.py redirect`.
- **Mise en ligne des sites** : `python3 deploy_render.py web`, qui appelle `deploy_cloudflare.py pages` quand `CLOUDFLARE_DEPLOY_TOKEN` est dans `.env`. Pour un seul site : `python3 deploy_cloudflare.py pages affichya`. Sur une connexion lente, le script réessaie, et les fichiers déjà envoyés ne sont pas renvoyés.
- **Réveil des serveurs** : tâche Cloudflare « keepalive » (`*/10 6-19 * * *` UTC). Affichya de 7h à 21h et Paginya de 9h à 19h, heure du Cameroun. Le workflow GitHub est supprimé : il dépassait les 2 000 min gratuites par mois.
- Les serveurs acceptent les deux adresses (CORS) pendant la transition.
- **Prix** : les petits montants sont passés à +50 F pour couvrir les 3 % de Fapshi. Paginya : page de garde et lettre 350 F, CV et épreuve 550 F. Affichya : affiche 250 F, vidéos 550 et 800 F. Les montants à partir de 1 000 F ne changent pas.
- À faire par le fondateur : ajouter les propriétés `*.pages.dev` dans Google Search Console (le code de vérification est déjà dans les pages), puis envoyer `sitemap.xml`.

## Nouvelle interface « Les valves » (29/09/2026) ✅ en ligne
- Refaite de zéro avec les skills Impeccable / Emil Kowalski / Taste. Univers : le tableau d'affichage de la fac (vert tableau, cadre bois, feuilles épinglées, tampon violet CONFORME / EN COURS / PAYÉ, surligneur jaune pour l'action principale, stylo bleu pour les notes).
- Règles écrites dans `web/DESIGN.md` (+ `web/.impeccable/design.json`, brief dans `web/.impeccable/surfaces/`). À lire avant toute nouvelle page.
- Plus aucun emoji : icônes Lucide embarquées dans `web/src/components/Icon.tsx` (ajouter un icône = coller son SVG dans PATHS).
- Polices : Sofia Sans + Sofia Sans Extra Condensed (woff2 locales). Tout le décor est en CSS (rien à télécharger).
- Composants : `PinLabel` (bouton jaune épinglé), `Stamp`, `Select` (chevron), `TextArea` qui grandit toute seule, dans `components/ui.tsx`.
- Relecture finale faite ; défauts corrigés (cadre bois, feuille « avant » froissée, boutons épinglés, rythme des sections, panneaux de l'éditeur sans cartes imbriquées).
- Piège : les classes maison de `globals.css` ne sont pas dans un `@layer` ; si une classe maison met `position`, elle écrase `absolute` de Tailwind.

## En cours (29/09/2026, nuit) — PAS encore déployé
Fait (local, tests API 49/49 OK, tsc OK) :
- Titre du document : placé en haut de la page 1 (ou sur la page de garde), plus après le sommaire (`render.py build_docx`).
- Lecture de la page de garde de l'étudiant (`api/app/doc/cover_info.py`) : école, titre, auteurs + matricule, encadreurs, structure, période, année → `meta.cover` ; les lignes de l'ancienne garde sont masquées (`hidden`).
- Éditeur : panneau Garde = studio complet (type, 8 modèles, 9 couleurs, détails, 2 logos), pré-rempli depuis `meta.cover`, école reconnue automatiquement (`CoverEditor.tsx`). Page 1 dessinée en direct dans le navigateur ; une modif de garde ne relance plus LibreOffice (`render.stale`, reconstruit au téléchargement).
- 4 nouveaux modèles (`lib/cover/templates/extra.ts` : bandeau, cadre, latéral, vagues), 4 palettes, second logo (`logo2`, faculté) ; logo IUT Douala ajouté.
- Vitesse : aperçus WebP 120 dpi (plus nets), rendus en PPM puis WebP (≈4× plus rapide), 3 premières pages tout de suite puis le reste en fond ; Word exporté seulement au téléchargement ; un seul passage d'index s'il n'y a pas de sommaire.
- Zoom « Agrandir » dans l'éditeur, transitions (panneaux, pages qui apparaissent en fondu).
Reste à faire, dans l'ordre :
1. Vérifier visuellement l'éditeur (capture `ed-cover.png` faite, pas encore regardée), puis commit + déploiement (API Render + web Cloudflare).
2. Logos de facultés manquants (Wikimedia n'en a presque pas) : sites officiels.
3. Étudier de vrais rapports/mémoires en ligne pour améliorer le moteur.
4. Affichya : récupération de boutique (lien WhatsApp + Google via Supabase), moteur de pub plus riche (idées : HyperFrames/GSAP, Lottie).

## Étude de vrais rapports (DICAMES, 29/09/2026) ✅
Rapports de stage réels d'étudiants camerounais (dépôt DICAMES du CAMES) passés dans le moteur. Corrigé :
- PDF : en-têtes/pieds de page répétés (« OCTOBRE 2022 », nom de l'entreprise) et numéros de page retirés ; ancien sommaire tapé à la main (lignes « ....... ») retiré ; « 2. » seul sur sa ligne recollé à son titre ; texte des organigrammes regroupé sur une ligne (plus de faux titres) ; phrases coupées en fin de ligne, autour d'une image ou avec « Sciences et / Techniques » recollées (`extract.pdf_cleanup`, `_cut`).
- Puces Word « ❖ ◆ ■ ● ➤ » reconnues.
- Page de garde : lignes coupées (« REPUBLIQUE DU / CAMEROUN »), « Rédigé et soutenu par », « Sous l'encadrement professionnel de », « Filière : » + valeur à la ligne, niveau, période/structure/diplôme sur plusieurs lignes, doublons ; titre laissé vide plutôt que faux.
- PDF abîmé : réparé par Ghostscript ; polices sans table (« 6WDJH ») décodées ; PDF scanné : OCR Tesseract (25 pages max).
Résultat sur un vrai rapport : 166 → 66 titres (le vrai plan), garde entièrement lue. Benchmark synthétique inchangé (97,6 %).
Téléchargement lent : les PDF DICAMES font 2-4 Mo (≈2 Ko/s ici) ; le serveur ne gère pas la reprise.

## Publier soi-même (sans Claude)
Depuis un terminal :
```
cd ~/Documents/serveur
./publier.sh paginya "ce que j'ai changé"     # ou affichya, ou tout
```
Le script lance les tests du serveur (s'ils échouent, rien n'est publié), enregistre les modifications (commit), les pousse sur GitHub (Render reconstruit le serveur tout seul en 5-10 min) puis construit et publie le site sur Cloudflare Pages. Les clés restent dans `serveur/.env`. Si la connexion coupe, relancer simplement la commande.

## Récents + nouveaux logos (29/09/2026) ✅ en ligne
- /document ne rouvre plus le dernier document : écran d'import neuf + liste « Reprendre un document » (`lib/recents.ts`, 8 derniers, sur ce téléphone). /garde : bouton « Reprendre ma dernière page de garde » (la commande payée revient avec).
- Logos ajoutés (sites officiels) : Ngaoundéré (+ ENSAI), Ebolowa, SUP'PTIC, ESSEC Douala (2e logo avec l'Université de Douala), IUC, Siantou, UPAC, IUT Douala. Sources dans `docs/LOGOS.md`.

## Déploiement automatique + sécurité (29/09/2026) ✅
- **Un simple `git push` publie tout** : Render reconstruit le serveur, GitHub Actions (`.github/workflows/site.yml`) construit le site et le publie sur Cloudflare Pages (secrets `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ACCOUNT_ID` enregistrés sur le dépôt GitHub). `serveur/publier.sh` fait tests + commit + push (option `--local` pour publier le site depuis l'ordinateur).
- Sécurité vérifiée : requêtes SQL paramétrées partout, textes échappés (vitrine), liens filtrés (pas de `javascript:`), photos ré-encodées, identifiants de documents aléatoires (128 bits), CORS limité aux sites, montants calculés par le serveur, webhook Fapshi signé, aucun secret dans le code.
- Ajouté : limites par adresse IP sur les actions coûteuses (`app/guard.py` : création de documents, OCR, rendu, paiements, boutiques) → erreur 429 ; en-têtes de sécurité sur l'API et sur les sites (`web/public/_headers` : CSP, anti-clickjacking, nosniff, HSTS).

## Vraies pages de garde (rapport PFE de l'utilisateur, 29/09/2026) ✅
- Lecture de garde : en-tête dans un tableau aplati par Word (« ******* »), tableaux lus colonne par colonne (encadreur principal / co-encadreur), titre « THÈME : » sur plusieurs lignes, adresses (B.P., TÉL.) ignorées, « THE UNIVERSITÉ … » rangé en anglais, faculté et département gardés dans l'en-tête même si l'école est reconnue.
- Modèle « Officiel Cameroun » par défaut quand la garde d'origine a un en-tête officiel ; deux logos empilés au centre (université en haut, faculté en dessous).
- Sans page de garde : en-tête + titre sur leur propre page, sommaire à la page suivante ; texte d'introduction sans titre placé au début du corps (plus sous le sommaire).
- Liste des figures : une liste tapée à la main (« Liste des figures & tableaux », sans numéros de page) est reconnue et remplacée, plus de doublons. La liste générée n'apparaît que si le document a des légendes « Figure 1 : … ».
- Dédicace : les lignes courtes du poème ne deviennent plus des titres. « Liste des abréviations, sigles et acronymes » reconnue dans n'importe quel ordre.
- Logos fournis par l'utilisateur : Yaoundé I, Yaoundé II, Dschang (blason), FSEG Yaoundé II, ISSEA.

## Vidéo de lancement (skill /brag-slim, 29/09/2026)
- `brag-output/brag.mp4` (vertical 1080×1920, 20 s, 5,5 Mo, pour statut WhatsApp / TikTok), `brag.jpg` (miniature), `share-copy.txt` (texte à publier), `brag-plan.md` (storyboard). Dossier exclu de Git (trop lourd).
- Fabriquée avec les vrais rendus de Paginya (page de garde du studio, sommaire et liste des figures du moteur, page « après » du site) ; composition HTML (`work/video.html`, une image = fonction du temps), 600 images capturées dans Chrome, musique et effets synthétisés (afro-pop 100 BPM en la mineur), encodage ffmpeg.
- Skill installée : `~/.claude/skills/brag-slim` (MIT). Pour une autre vidéo : « /brag-slim » dans Claude Code.

## Année académique automatique (14/10/2026) — local, PAS encore publié
- Test complet en local (texte collé → 16 pages → paiement simulé → PDF + Word) : OK.
- « 2025-2026 » était écrit en dur (page de garde, studio, épreuve). Remplacé par `academicYear()` (`web/src/lib/cover/year.ts`) : l'année commence en septembre.
- Réveil des serveurs laissé tel quel (9 h-19 h) : décision du fondateur, les étudiants travaillent surtout en journée pour l'instant.
- À faire avant la pub : vrai paiement Fapshi sur téléphone (le seul essai, le 28/09, a fini en FAILED).

## Banc d'essai sur 86 documents + corrections du moteur + pages de garde (14/10/2026) — local, PAS encore publié
**Corpus** (`api/data/corpus/`, non versionné, 34 Mo) : 8 rapports/mémoires PDF de DICAMES, 34 fichiers d'étudiants pris sur GitHub (.docx, .doc, .odt), 11 documents réels de l'ordinateur, 33 documents « mis en forme à la main » fabriqués par `handmade.py` (titres en gras/soulignés/majuscules sans styles Word, numérotations I- 1) a/ A/, sommaire tapé, pages poussées par des lignes vides, Maj+Entrée, avec ou sans page de garde, version collée en texte). Les 33 ont leur plan attendu (`*.truth.json`).
**Outils** (`api/ml/study/bench/`) : `bench.py <corpus> <sortie> [filtre]` (vraie API : création → validation → rendu, dans les deux modes), `report.py <sortie>`, `sheet.py` (planche d'images d'un PDF), `kinds.py` (tous les types sur 8 documents), `handmade.py <dossier>`. Lancer avec `PROPRE_DATA_DIR=<dossier temporaire>`.
**Mesure** sur les 31 documents à plan connu : titres retrouvés 95,2 % → 100 %, précision 95,0 % → 98,3 %, bons niveaux 81,0 % → 95,7 %. 86 documents, 0 échec.

Corrigé :
- Garde : un document dont le 1er titre n'est pas un mot connu (« A/ Objectif du TP ») était lu comme une longue page de garde et ses lignes courtes étaient cachées. La garde s'arrête maintenant au saut de page, à 6 lignes vides, après l'année académique, à un titre Word ou numéroté, à un vrai paragraphe (`cover_info._body_starts` ; `Raw.new_page` / `Raw.gap` remplis par `from_docx` et `from_text`). Garde sans noms (logo + « RAPPORT DE STAGE » + sujet) reconnue.
- Niveaux : le modèle ne change plus le niveau d'un titre numéroté (`ml.refine` + `detect._label_family`) ; titres tous en « Titre 1 » mais numérotés de 2 façons : la numérotation décide (`_unflatten_styles`) ; « 1/ » reconnu ; « 2. Matériel » suivi de puces = titre.
- Word « fait à la main » (moins de 60 % des titres avec un style Word, pas de sommaire automatique) : mode `rebuild` par défaut au lieu de `keep` (`existing.handmade`, calculé dans `doc_routes.create`), expliqué sur l'écran d'analyse avec le bouton « Plutôt garder mon fichier tel quel ».
- Mode `keep` : un sommaire tapé à la main sous « SOMMAIRE » est remplacé, plus doublé.
- Paragraphes à plusieurs lignes (Maj+Entrée) découpés ou recollés (`extract._split_breaks`). Lignes de tirets/astérisques et numéros de page seuls (PDF) retirés, pointillés d'un plan tapé retirés, chapitres annoncés dans l'introduction = liste.
- Majuscules : « DE, DES, LA… » ne sont plus pris pour des sigles ; pages spéciales, parties et chapitres harmonisés en capitales avec accents quand la majorité l'est (`clean.harmonise_tops`).
- Sections en anglais (Dedication, Acknowledgements…), glossaire ; type : lettre avec « Objet : demande de stage » = administratif, exposé, rapport de projet.
- `.doc`, `.odt`, `.rtf` acceptés : convertis en `.docx` par LibreOffice à l'arrivée (`office.to_docx`).
- Aperçus : relancer une mise en page pendant que les pages de la précédente se dessinaient mélangeait les pages et donnait des « page introuvable » (`office.previews`, un seul travail de fond par document).
- Changer de type de document : testé sur 8 documents × 7 types, rien ne casse.

Pages de garde : 12 modèles (+ Classique, Bloc couleur, Rubans, Deux tons), 17 couleurs + « Ma couleur », choix de police (Times, Poppins, Playfair, Inter), langue « English first » (colonne anglaise à gauche, libellés en anglais ; automatique pour Buea, Bamenda, ICT University, CUIB), 12 établissements ajoutés (facultés de Buea et Bamenda, lycée bilingue, GHS, collège). Épreuves : option « École anglophone ».

Reste, par ordre d'intérêt :
1. PDF : tableaux (liste des tableaux, sigles) aplatis en lignes, notes de bas de page prises pour des titres. Les PDF restent nettement moins bons que les Word.
2. Mode `keep` : il utilise son propre détecteur de titres (`keep.find_titles`), plus faible que `detect` (ex. 2 titres trouvés contre 47).
3. Garde lue : rôle des encadreurs parfois générique ; les nouveaux modèles n'ont pas été vérifiés avec deux logos.
4. Élargir le corpus avec de vrais Word camerounais (ceux des premiers utilisateurs, avec leur accord).

## Pages blanches (14/10/2026) — local, PAS encore publié
- Les sauts de page étaient des paragraphes vides avec un saut : quand la page d'avant était pleine, ils laissaient une page blanche. Remplacés par un paragraphe minuscule « saut de page avant » (`render.Builder.page_break`). Le paragraphe laissé par l'index LibreOffice ne prend plus de place (`uno_worker.insert_index`). Corpus : 17 pages blanches → 2 (les 2 viennent des fichiers d'origine).
- Reste : logos des facultés et écoles manquants (FS, FALSH, FSE, FMSB de UY1 ; FSJP UY2 ; ENSET, FGI Douala ; FASA, IUT Fotso Victor ; facultés de Buea et Bamenda ; ENSAI ; ENSPM) ; reprendre les logos présents sur la garde du document importé ; placement des logos.
- Logos (14/10/2026, suite) : sceau de l'Université de Buea (à la place de la bannière avec texte), emblème de l'ENSET Douala (`enset2.png`, à côté de celui de l'Université de Douala). Les sites officiels des autres facultés (FS, FALSH, FSE, FMSB, FSJP, FGI, FASA, facultés de Buea et Bamenda, ENSAI, ENSPM) ne publient que le logo de leur université ou sont injoignables : pour eux, c'est désormais le document de l'étudiant qui fournit le logo.
- Logos du document : les images de la page de garde de l'étudiant (y compris dans un tableau d'en-tête) sont lues (`meta.cover.logos`) et reprises sur la nouvelle garde, dans leur ordre, si elles ressemblent à des logos (`CoverEditor.ownLogo`). Vérifié sur le rapport PFE de l'utilisateur : logos de l'Université d'Ebolowa et de la Faculté des sciences.
- Aperçu de garde : plus d'encadreur d'exemple ajouté quand le document nomme déjà ses encadreurs.

## 17/10/2026 — Pass 30 jours de Paginya + comptes Google (local, PAS encore publié)
- Avant : le prix `pass_30j` (5 000 F) existait mais rien ne l'utilisait.
- **Comptes** (`api/app/accounts.py`, table `accounts`) : connexion Google → jeton signé (180 j, `ACCOUNT_SECRET`, sinon `ADMIN_SECRET`). Routes : `/account/config`, `/account/google`, `/account/me`, `/account/pass` (crée une commande `pass_30j` payée par `/orders/{id}/pay`), `/orders/{id}/unlock`.
- `db.settle` ajoute 30 jours au compte dans la même transaction que le paiement (crédité une seule fois). Une commande de pass ne se télécharge ni ne se modifie.
- **Équipe** : un compte dont le Gmail est dans `ADMIN_EMAILS` débloque tout sans payer (plus besoin de `/coulisses`, qui marche toujours).
- Site : `PaySheet` propose « Ce document » ou « Pass 30 jours » ; le pass demande Google avant le numéro ; « J'ai déjà un pass » pour un autre téléphone ; pass actif / équipe → « Télécharger sans payer ». `lib/account.ts`, `components/GoogleButton.tsx`.
- Confidentialité : adresse Gmail ajoutée (données + durée).
- Test : `test_pass_account_and_team`. À faire : afficher le pass sur la page Tarifs.

## 21/10/2026 — Suivi des visiteurs + Pixel Meta (local, PAS encore publié)
- Constat : depuis le boost (19/10, 64 visites), 0 document déposé par un visiteur ; 1 seul paiement réel depuis le début (épreuve, 05/10).
- API : table `events` (sid, step, src, day), `POST /events` (text/plain, sans preflight), `POST /admin/funnel` (équipe), purge à 12 mois. Test ajouté (93 au vert).
- Site : `lib/track.ts` (étapes visit, open_*, upload, pay_open, pay_start, paid + source facebook/tiktok/…), `components/Analytics.tsx` (Pixel si `NEXT_PUBLIC_META_PIXEL_ID`), stats visibles sur /coulisses (`FunnelStats.tsx`), CSP (connect.facebook.net), page confidentialité mise à jour.
- Testé en local de bout en bout : les 6 étapes enregistrées avec la source.
- Reste : créer le Pixel dans le Gestionnaire d'événements (compte pub 1542366527937017), mettre son ID dans `.github/workflows/site.yml` (`NEXT_PUBLIC_META_PIXEL_ID`), publier (`serveur/publier.sh paginya "suivi visiteurs + pixel"`), puis pub 1 000 F/jour × 8 jours objectif Ventes après le 24/10.

## 24/10/2026 — Nouveaux prix, pass Essentiel/Pro, support
- **Prix** (`api/app/pricing.py`, `web/src/lib/plans.ts`) : un document = **550 F**, quel que soit le type ou le nombre de pages, sans compte. **Pass Essentiel 3 000 F / 30 j** (10 documents/jour, mis en avant « Conseillé »), **Pass Pro 5 000 F / 30 j** (illimité, `per_day = 0`, imprimeries, entreprises). Les anciens pass 5 000 F (`plan` vide) comptent comme Pro.
- Pas de renouvellement automatique. Même formule rachetée = +30 j ; changement de formule = jours restants convertis à leur valeur (`db._extend_pass`).
- Limite du jour : compte des commandes débloquées par le pass depuis minuit heure du Cameroun (`trans_id = pass:<sub>`). Un retéléchargement ne compte pas.
- Garde-fou : un document payé qui grossit de plus de 2× (et +15 pages) doit être traité comme un nouveau.
- **Équipe** : `ADMIN_EMAILS` (sur Render) = les deux Gmail. Une seule connexion sur `/coulisses` connecte aussi le compte → tout se télécharge sans payer, sans limite.
- **Support** (`api/app/support.py`, tables `tickets`, `ticket_messages`) : page `/aide` (message + WhatsApp/e-mail, commande jointe depuis la fenêtre de paiement), réponses visibles sur `/aide` et `/compte`. Boîte commune sur `/coulisses` : statut À traiter / Répondu / Résolu, qui a répondu, commande et pass du client, « Débloquer ce document », « Offrir des jours », lien WhatsApp/e-mail prérempli. Notification sur les téléphones via l'appli **ntfy** (sujet secret `SUPPORT_NTFY_TOPIC`). Messages gardés 12 mois.
- Pages : `/tarifs` (3 offres), `/compte` (pass, compteur du jour, achat), accueil, CGU, confidentialité.
- Tests : `tests/test_plans_support.py` (101 au vert).

## 24-25/10/2026 — Tests sur de vrais documents camerounais + corrections
- **Corpus de test** (`api/data/corpus2/`, non versionné : dicames, epreuves, word, lettres, fixtures) : 60 mémoires/rapports DICAMES (UY1, UY2, ENS, ENSET, FALSH, FSE, FMSB, ESSTIC, Dschang, UCAC…), 30 épreuves (séquences, probatoire, épreuves zéro, sujetexa.com), 12 Word d'étudiants (GitHub), 3 lettres administratives tapées. Banc : `api/ml/study/bench/bench.py`.
- Corrigé :
  - **Équations Word** (OMML) : elles disparaissaient. Maintenant gardées (fichier `images/<id>.omml`, repère `⟦eq…⟧` dans le texte) et remises en vraies équations dans le Word refait (`render.add_text`) ; texte simple dans les titres et cellules.
  - Caractères de contrôle dans un PDF → plantage du Word (`render.xml_safe`).
  - Image avec 0 dpi → plantage (réenregistrée proprement) ; Word récent avec alignement « start » → import impossible.
  - PDF scanné à mauvaise couche de texte (« Comtnente~~ ») : relu par Tesseract si ≤ 8 pages et si c'est mieux (`extract.junk_rate`).
  - Garde scannée avec cadre décoratif : Tesseract voyait une page vide → 2e lecture en `--psm 4`.
  - Épreuves en anglais (marks, Section A, Task 1) reconnues.
  - Titres faux : fins de paragraphe coupées par un saut de page, titres en minuscule, charabia de police → paragraphes ; références « E. Tawil, …, 2013, p. 5 » ne sont plus des titres ; tiret seul sur sa ligne recollé.
  - Gemini 2.5 n'existe plus : secours `gemini-3.8-flash`, `gemini-3.5-flash-lite`.
- Ajouté :
  - **Lettres** tapées librement : reconnues (`forms/letter_parse.py`), « Oui, présenter ma lettre » ouvre /lettre déjà rempli (expéditeur, date, destinataire, objet, P.J., corps).
  - **Départements** proposés par établissement dans le studio (`web/src/lib/departments.ts`, sources : gardes DICAMES, listes publiées).
  - **Galerie de logos** (« Choisir ») partout où on met un logo ; logo **ENSET Ebolowa**.
  - **Compteur d'usage** (`usage` : IA, OCR, rendus) visible dans /coulisses → Visiteurs → Machine.
- Mesures : documents « faits à la main » avec plan connu : rappel 0,939, précision 0,925 (pas de régression). 59/60 PDF DICAMES sans erreur (le 60e est un scan, lu maintenant).
- **Envoi des fichiers sans base64** (`POST /documents/upload?filename=…`, corps = le fichier) : 33 % de données en moins. Mesuré : sur la connexion du fondateur (≈ 19 Ko/s), un mémoire PDF de 1,2 Mo prenait 80 s à l'envoi, le serveur 0,5 s.
- **Charge (serveur en ligne, 25/10/2026)** : 1 personne = 24 s (import + mise en page d'un court rapport) ; 5 en même temps = 31 s pour la dernière ; 10 en même temps = 55 s, aucune erreur. Mémoire de 82 pages : mise en page 21 s. LibreOffice traite un document à la fois : au-delà de ~15 mises en page simultanées, l'attente dépasse 1 min 30 → passer sur un serveur payant (Render Starter) quand ça arrive.

## 25/10/2026 — Correction des fautes (option) + pubs
- Outil **« Fautes »** dans l'éditeur (pas en mode « garder mon fichier ») : l'IA propose, l'utilisateur coche et applique (`api/app/doc/spelling.py`, `POST /documents/{id}/spelling`, `web/src/components/doc/SpellPanel.tsx`). Accord demandé avant l'envoi. Français et anglais, sans reformuler ni traduire.
- Garde-fous : correction refusée si elle change un nombre, une équation, plus de ~15 % du texte ou trop de mots.
- IA : `gemini-3.5-flash-lite` (≈ 3 s par tranche de ~1 000 mots), puis Groq `gpt-oss-120b`, puis `gemini-flash-latest` (≈ 1 min par tranche : dernier recours). 3 appels en parallèle, 8 corrections/heure par IP. Compté dans Coulisses → Machine (« Appels de correction des fautes »).
- Pubs : scripts publiés (5 pubs + version anglaise, consignes de voix, captures à filmer) ; essais de voix gratuites (Edge TTS) dans `~/Documents/pubs/paginya-2026-10/essais-voix/`.

## 25/10/2026 — PDF trouvés sur le net : images, tableaux, titres ; chargement détaillé
- **Constat** : un PDF ne donnait que son texte. Images, schémas, organigrammes et tableaux disparaissaient (le texte des schémas devenait du charabia « Hash · Block · Item ») ; titres sur plusieurs lignes coupés en 3 titres sur 3 pages ; sauts de page du PDF perdus ; listes « 1) 2) 3) » et tirets « - » séparés de leur texte.
- **`api/app/doc/pdf_layout.py`** : la page est dessinée sans son texte (Ghostscript `-dFILTERTEXT`, 72 dpi, PGM brut) ; chaque tache de dessin devient
  - une **image** découpée à 150 dpi au bon endroit (photos, cartes, schémas, organigrammes, formules), ses mots retirés du texte ;
  - un **vrai tableau** (lignes fines + mots de chaque cellule) ;
  - ou rien : cadre autour d'un titre, bandeau/parchemin de titre (« DÉDICACE »), fond coloré, filigrane, petite flèche, texte dessiné en formes (polices Type 3), page scannée (repérée par `pdfimages -list`, pas analysée).
  - Le texte reste celui de pdftotext ; seules les lignes dans les images/tableaux sont retirées.
- `extract.py` : sauts de page gardés (`\f`), phrase qui continue sur la page suivante recollée, titre en majuscules sur plusieurs lignes en haut de page = un titre, « 2. » en haut de page n'est plus un en-tête répété, colonnes de numéros/puces recollées à leurs éléments, « chapitres. » en début de ligne n'est plus un début de chapitre, PDF d'une seule ligne accepté.
- `detect.py` : dernière vérification des titres (citation entre guillemets, référence bibliographique, plus de 160 caractères → paragraphe). `exam_scan.py` : « 2021/2022 », « sous-évaluation », « Section I : » ne font plus prendre un rapport pour une épreuve.
- Sommaire (`uno_worker.tidy_index_styles`) : un titre long passe à la ligne en retrait sous son texte.
- `render.add_text` : un « ⟦ » tapé dans le texte faisait planter la mise en page (récursion infinie).
- **Mesures** (ancien → nouveau) : 60 mémoires DICAMES : 0 → 975 figures, 1 → 426 tableaux, alertes 131 → 121, aucune nouvelle erreur ; documents « tapés à la main » en Word/texte : identiques (rappel 0,939, précision 0,925) ; les mêmes en PDF : rappel 0,956 → 0,959, précision 0,93 → 0,94, 0 → 14 tableaux. Rapport ESSTIC 45 pages : 54 → 39 pages. Coût : ~1 à 3 s de plus par PDF de 100 pages (en local).
- Corpus de test « net » : `api/data/corpus3/` (non versionné : arXiv, Bitcoin, IRS, ONU, polycopiés, rapports ESSTIC, Word d'exemple).
- Web : onglet « Fautes » retiré de la barre du bas (Télécharger ne tenait plus sur téléphone) → section « Corriger les fautes » en bas de Style. **Chargement** : l'envoi passe par XMLHttpRequest pour suivre la progression ; cercle qui se remplit (« Envoi de ton fichier · 37 % · 460 Ko sur 1,3 Mo »), puis lecture, titres, tableaux/images, mise en page ; message « connexion lente » après 10 s.
- Reste : 5 pubs vidéo avec voix ElevenLabs (le fondateur crée le compte et se connecte dans Chrome).

## Session du 25/10/2026 : démo avant/après et corrections du moteur
- Démo pour réunion : `~/Documents/demo-paginya/` (vrai rapport GitHub `Halima-Najjari/Rappor-tStage-Digitalia`, 26 p. → 24 p. Paginya, parcours complet du site).
- Corrigé : zones de texte de la page de garde lues (`extract._cover_boxes`, nom/encadrants) ; titre en casse normale sous « RAPPORT DE STAGE » (`cover_info`) ; « Formation : » = spécialité ; plus de « NOM Prénom / [date] » dans le fichier payé quand la garde est complète (`coverSvgPreview`) ; plus d'école inventée (UY1) quand l'ancienne garde n'en a pas ; Markdown collé depuis ChatGPT (`**…**`, ```, `**` ≠ puce) dans `detect.py` + test.
- Banc 86 docs : 0 échec. Écarts restants (titre de cours compté en titre, lettre 0/0) présents aussi sans ces changements.
- Mémoire MENDOGO (Ebolowa, 61 p. → 68 p.) : « Promotion 2023/2026 » ne ferme plus la garde ni ne fait l'année (années consécutives seulement) ; sujet pris sous les noms si besoin ; en-tête « FR / EN » coupé en deux colonnes ; « diplôme de Diplôme » ; « Liste des symboles et unités » = page préliminaire (numérotation romaine juste) ; « [Emplacement de la figure …] » et « Nom : … » (formulaires d'annexes) ne sont plus des titres.
- Lot de 17 exposés réels (Ebolowa, RIM/SBM/SIN, PDF + Word, 25/10) → règles générales : plan tapé sans numéros reconnu (en tête de document, lignes numérotées, titres qui reviennent, le document « recommence » juste après) et remplacé par un vrai sommaire, même pour un exposé (`meta.typed_plan` → `options.toc`) ; puces orphelines des PDF recollées (`clean.orphan_bullets`) ; en-tête officiel sans nom = garde ; exposés de groupe reconnus (matricules, « Groupe 3 ») ; sans chapitres, « I. » au niveau de l'Introduction ; style Word « Titre » sans niveau → la numérotation décide ; « Iii- », « Iv- » ; titres coupés par le PDF recollés ; « PACS). », « Superviseur : … », en-têtes de garde modèle en annexe ne sont plus des titres ; Article/Alinéa ; matricule sous le nom ; image pleine page plus collée au titre suivant.
- Banc 86 docs : 0 échec, 5 exposés passent de 78 % à 100 % (niveaux), aucun score en baisse. Faux positifs du plan vérifiés (TP 1/TP 2 répétés, code SQL) : rien retiré.
- À faire : mémoire `sanatayeb/Rapport` (41 p.) mal rendu : garde en zones de texte/WordArt non reconnue, « Chapitre 1 : / Cadre générale / De projet » coupé en 3 pages, noms des remerciements pris pour des titres. Année de garde devinée (2026-2027) au lieu de celle du document.
