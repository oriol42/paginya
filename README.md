# Propre

« C'est propre ! » : tu écris ton texte, Propre te rend un document impeccable (Word + PDF), aux normes de ton école, sans toucher à Word.

## Documents

| Fichier | Contenu |
|---|---|
| [docs/DECISIONS.md](docs/DECISIONS.md) | **Décisions validées** (nom, couleurs, prix, paiement, recettes). Ce fichier fait foi |
| [docs/FONCTIONNEMENT-APP.md](docs/FONCTIONNEMENT-APP.md) | Fonctionnement de l'app : écrans, studio de pages de garde, éditeur-aperçu, rôle de l'IA |
| [docs/PLAN.md](docs/PLAN.md) | Architecture technique, stack gratuite, qualité, risques |
| [docs/NORMES-CAMEROUN.md](docs/NORMES-CAMEROUN.md) | Normes relevées sur de vrais mémoires et rapports camerounais |
| [docs/RECHERCHES-PAIEMENT-STYLES.md](docs/RECHERCHES-PAIEMENT-STYLES.md) | Moment du paiement, intégration Fapshi, styles, Gamma |
| [prototype/](prototype/) | Test technique : Word généré + sommaire et pagination calculés par LibreOffice + PDF (1,65 s) |

## Lancer en local

```bash
./dev.sh
```

- Site : http://localhost:3000
  - `/garde` : studio de pages de garde (parcours guidé en 3 étapes)
  - `/document` : mise en forme automatique (Word, PDF, texte collé)
  - `/outils/video` : générateur de vidéos TikTok (MP4 1080×1920, 15 s) — outil interne, non référencé
  - `/dev/covers` : bac à sable des styles (seulement en développement)
- API : http://localhost:8000 (documentation auto : `/docs`)
- Paiements **simulés** par défaut (`FAPSHI_MODE=mock`) : un numéro finissant par **0** est payé, par **1** échoue.
- Pour la sandbox Fapshi : copier `api/.env.example` vers `api/.env`, mettre `FAPSHI_MODE=sandbox` et les clés du service.

Tests : `cd api && .venv/bin/python -m pytest` (17 tests, dont le parcours complet texte → paiement → téléchargement) · `cd web && npx tsc --noEmit && npx eslint src`

## Code

| Dossier | Contenu |
|---|---|
| `web/` | Next.js 16 (PWA) : accueil, studio de pages de garde, moteur SVG (`src/lib/cover/`) |
| `api/` | FastAPI : commandes, prix côté serveur, paiement Fapshi direct-pay (+ webhook et vérification régulière) |
| `api/app/doc/` | Moteur de mise en forme : `extract` (Word/PDF/texte) → `detect` (structure par règles) → `render` (Word via python-docx) → `uno_worker` (LibreOffice : sommaire, listes, PDF) → aperçus PNG avec filigrane |
| `api/fonts/` | Polices libres (OFL) identiques à celles du navigateur : Poppins, Tinos (≈ Times New Roman), Playfair Display, Inter |

## À faire tout de suite

- [ ] Créer le compte Fapshi, créer un service, **demander l'activation de la demande directe (direct-pay) en production**
- [ ] Vérifier le domaine (propre.cm, getpropre.com, propre.app…) et que le nom est libre à l'OAPI (office des marques pour le Cameroun et l'Afrique francophone)
- [ ] Récupérer 40 vrais documents mal formatés (avec accord) pour le corpus de test

## Prérequis serveur

LibreOffice (`soffice` + module Python `uno` du système), poppler (`pdftotext`, `pdftoppm`, `pdfinfo`). Sur Ubuntu : `sudo apt install libreoffice-writer python3-uno poppler-utils`.
