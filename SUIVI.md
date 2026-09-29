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
