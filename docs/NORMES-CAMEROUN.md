# Base de normes — documents académiques et administratifs camerounais

Relevé fait le 22/09/2026 sur de vrais documents publiés (archive ouverte DICAMES du CAMES) et sur le guide officiel de l'Université de Buea. Ce fichier sert de référence pour construire les modèles (templates) de la plateforme.

## Corpus analysé

| # | Établissement | Type | Source |
|---|---|---|---|
| 1 | UY2 – ESSTIC | Rapport de stage licence (2022) | [DICAMES 11020](https://dicames.online/jspui/bitstream/20.500.12177/11020/1/Ngnichang%20Tandi%20Honorine.%20Rapport%20de%20stage.pdf) |
| 2 | UY2 – ESSTIC | Rapport de stage licence (2022) | [DICAMES 9887](https://dicames.online/jspui/bitstream/20.500.12177/9887/5/Mekounthe%20A%20Ndio%20Larissa.pdf) |
| 3 | UY2 – ESSTIC | Rapport de stage licence (2022) | [DICAMES 11018](https://dicames.online/jspui/bitstream/20.500.12177/11018/1/Ndongo%20Yannick.%20Rapport%20de%20stage.pdf) |
| 4 | UY2 – ESSTIC | Rapport de stage licence (2022) | [DICAMES 10380](https://dicames.online/jspui/bitstream/20.500.12177/10380/1/Floriane%20Tchouala%20Fouometio.pdf) |
| 5 | UY1 – ENS Yaoundé | Mémoire DIPES II Maths (2019) | [DICAMES 5179](https://dicames.online/jspui/bitstream/20.500.12177/5179/1/ENS_20_0614.pdf) |
| 6 | UY1 – ENS Yaoundé | Mémoire DIPES II Histoire (2016) | [DICAMES 5140](https://dicames.online/jspui/bitstream/20.500.12177/5140/1/ENS_20_0532.pdf) |
| 7 | UY1 – FSE | Mémoire Master II (2017) | [DICAMES 7646](https://dicames.online/jspui/bitstream/20.500.12177/7646/1/ENSET_EBO_BC_21_0490.pdf) |
| 8 | UY1 – FSE | Mémoire Master (2024) | [DICAMES 13236](https://dicames.online/jspui/bitstream/20.500.12177/13236/1/FSE_MEM_BC_26_%200097.PDF) |
| 9 | UY1 – FALSH | Mémoire Master Histoire (2022) | [DICAMES 10738](https://dicames.online/jspui/bitstream/20.500.12177/10738/1/FASLH_MEM_BC_23_0055.pdf) |
| 10 | UY1 – FMSB | Mémoire Master II Santé publique (2023) | [DICAMES 11370](https://dicames.online/jspui/bitstream/20.500.12177/11370/1/UYI_Memoire-MPH.pdf) |
| 11 | University of Buea | Guide officiel thèses et dissertations (2021) | [UB Thesis Guide](https://ubuea.cm/wp-content/uploads/2021/12/UB_Thesis_Guide_2021.pdf) |

À compléter : Université de Douala, Dschang, Ngaoundéré, Maroua, Bamenda, ENSP/Polytech, IUT, instituts privés (BTS/HND), lycées techniques (MINESEC).

## 1. Constantes observées (10 documents sur 10 sauf mention)

- **Format A4**, papier portrait.
- **Police : Times New Roman** partout (9 documents sur 10 ; l'un utilise Cambria pour les titres).
- **Marges : environ 2,5 cm**, souvent **3 cm à gauche** pour la reliure (mesuré sur 6 documents). Buea impose **3,5 cm à gauche et 2,5 cm ailleurs**.
- **Pages préliminaires en chiffres romains minuscules** (i, ii, iii…), **corps en chiffres arabes à partir de l'Introduction** (1, 2, 3…).
- **Page de garde bilingue** FR à gauche / EN à droite (8 documents sur 10).
- **Résumé + Abstract** obligatoires pour les mémoires (tous les mémoires du corpus). Absents des rapports de stage de licence.
- **Sommaire au début + Table des matières à la fin** : pratique très courante (rapports ESSTIC, FALSH, FSE). Le sommaire ne liste que les niveaux 1-2 ; la table des matières est complète.

## 2. Page de garde — structure type

### En-tête (bloc bilingue sur 2 colonnes, logo au centre facultatif)

```
RÉPUBLIQUE DU CAMEROUN                    REPUBLIC OF CAMEROON
  Paix – Travail – Patrie                  Peace – Work – Fatherland
        ********                                  ********
MINISTÈRE DE L'ENSEIGNEMENT        [LOGO]   MINISTRY OF HIGHER EDUCATION
        SUPÉRIEUR                                 ********
        ********                           THE UNIVERSITY OF YAOUNDE I
  UNIVERSITÉ DE YAOUNDÉ I                          ********
        ********                           FACULTY OF ...
  FACULTÉ DE ...                                   ********
        ********                           DEPARTMENT OF ...
  DÉPARTEMENT DE ...
```

Règles observées :
- Chaque niveau est séparé par une ligne décorative : `********`, `*****`, `-----------` ou `.......` (varie selon l'établissement → **paramètre du modèle**).
- Texte centré dans chaque colonne, en MAJUSCULES, en gras le plus souvent, taille 10-11.
- Les lignes « République du Cameroun / Paix-Travail-Patrie » et « Ministère » sont **parfois omises** (FALSH, FSE, ENS 2016 et une partie de l'ESSTIC commencent directement par l'université) → **option à cocher**.
- Niveaux possibles : République → Ministère → Université → Faculté/École → Centre de recherche (CRFD) → Unité de recherche (URFD) → Département. Les mémoires de master de l'UY1 incluent le CRFD et l'URFD.
- Le sigle de l'école est ajouté entre parenthèses : « (ESSTIC) » / « (ASMAC) ».

### Corps de la page de garde (centré)

1. **Type de document** : « RAPPORT DE STAGE », « MÉMOIRE » (gras, majuscules, 16-20 pt), parfois encadré.
2. **Titre / thème** : gras, majuscules, 14-18 pt, souvent dans un cadre ou entre deux filets.
3. **Mention de diplôme** : « Mémoire présenté et soutenu (publiquement) en vue de l'obtention du [Master / DIPES II / Licence] en … » ou, pour un stage, « Stage effectué à [structure] du [date] au [date] » puis « Présenté en vue de l'obtention de la licence en … ».
4. **Spécialité / Option / Parcours / Filière / Niveau.**
5. **Auteur** : « Par : » / « Présenté par : » / « Rédigé et soutenu par : » → NOM en majuscules + prénoms ; diplôme déjà obtenu (« Licencié en Histoire ») ; **Matricule**.
6. **Encadrement** : « Sous la direction de : » (mémoire) ou « Sous l'encadrement professionnel de : » / « Encadreur académique » (stage) → nom + grade (Pr, Dr, MC, CC, PhD) + fonction ; parfois deux colonnes Directeur / Co-directeur.
7. **Jury** (facultatif, version finale d'un mémoire) : tableau Qualité / Nom et grade / Université (Président, Rapporteur, Examinateur/Membre).
8. **Pied de page** : « Année académique : 2021-2022 » en bas à gauche + date de soutenance (« Novembre 2022 ») en bas à droite, ou l'année seule centrée.

### Variante Buea (anglophone, guide officiel)

Ordre imposé : établissement → faculté et département → titre complet → diplôme (« A dissertation submitted in partial fulfilment of the requirements for the degree of … ») → auteur → superviseur(s) → mois et année. Page 2 blanche, page 3 = répétition de la page de titre.

## 3. Ordre des pages préliminaires

Ordre relevé le plus fréquent (mémoires UY1) :

1. Page de garde
2. (Avertissement : « L'Université de … n'entend donner aucune approbation ni improbation aux opinions émises… » — ESSTIC, FSE)
3. Sommaire *(tantôt ici, tantôt après l'abstract — option)*
4. Dédicace (« À mon père… », texte court, souvent aligné à droite ou centré en bas de page)
5. (Déclaration sur l'honneur / Certification — ENS, Buea)
6. Remerciements (1 page max à Buea)
7. (Liste du personnel administratif et enseignant — FMSB uniquement)
8. Liste des sigles, abréviations et acronymes (format « SIGLE : signification », triée alphabétiquement)
9. Liste des tableaux / Liste des figures / Liste des graphiques / Liste des illustrations
10. Résumé (≤ 300 mots à Buea) + mots-clés
11. Abstract + keywords
12. (Plan du mémoire — FSE)

Puis : **Introduction (générale)** → Parties / Chapitres → **Conclusion (générale)** → **Bibliographie** (ou Références) → **Annexes** → **Table des matières**.

Rapport de stage de licence (ESSTIC) : Page de garde → (Avertissement) → Sommaire → Dédicace → Remerciements → Sigles → Liste des tableaux → Introduction → Parties → Conclusion → Bibliographie → Annexes → Table des matières.

## 4. Structure du corps et numérotation des titres

Schémas relevés :
- **Rapport de stage (2 parties)** : « PREMIÈRE PARTIE : PRÉSENTATION DE LA STRUCTURE D'ACCUEIL » (historique, missions, organisation, organigramme, moyens matériels et humains) / « DEUXIÈME PARTIE : DÉROULEMENT DU STAGE » (accueil, tâches effectuées, évaluation : apports, difficultés, suggestions).
- **Rapport de stage (chapitres seuls)** : Chapitre I Présentation de la structure / Chapitre II Déroulement / Chapitre III Tâches effectuées.
- **Mémoire de recherche** : Partie I Cadre théorique (Ch.1 Problématique, Ch.2 Revue de littérature / insertion théorique, Ch.3 Méthodologie) / Partie II Cadre opératoire (Présentation et analyse des résultats, Interprétation et discussion).

Numérotations utilisées (à proposer comme choix) :
- Parties : PREMIÈRE PARTIE / DEUXIÈME PARTIE ou PARTIE I / PARTIE II.
- Chapitres : CHAPITRE I, CHAPITRE 1, « Chapitre Un ».
- Sous-niveaux style français : I. → A. → 1. → a) ; ou style décimal : 1.1 → 1.1.1.
- Un chapitre commence toujours sur une nouvelle page ; les titres de partie ont souvent une page à eux seuls (page intercalaire).

## 5. En-têtes et pieds de page

- Numéro de page en bas à droite ou centré (ESSTIC, UY1) ; **en haut à droite pour Buea**.
- En-tête courant fréquent : type de rapport (« Rapport de stage de participation ») ou titre complet du rapport.
- Pied de page courant (ESSTIC) : « Rédigé par NOM Prénom ».
- Pas de numéro affiché sur la page de garde.

## 6. Corps de texte

- Times New Roman 12, **texte justifié**, retrait de première ligne (~1,25 cm) fréquent.
- Interligne : 1,5 le plus courant dans les consignes ; **Buea : double interligne** (simple pour les citations longues et les notes).
- Citations de plus de 4 lignes : bloc en retrait de 1,5 cm, interligne simple, sans guillemets (Buea).
- Titres de section en gras ; titres de chapitre en majuscules, gras, centrés, 14-16 pt.

## 7. Tableaux et figures

- Légende de tableau **au-dessus** : « Tableau 1 : Titre » ; légende de figure **en dessous** : « Figure 1 : Titre » ; ligne « Source : … » sous l'élément.
- Numérotation continue dans tout le document (1, 2, 3…) dans le corpus ; numérotation par chapitre (1.1, 1.2) chez l'ENS Maths (LaTeX).
- Listes des tableaux/figures présentées parfois sous forme de tableau « N° | Intitulé | Page ».

## 8. Bibliographie

- Classement alphabétique par nom d'auteur (NOM en majuscules), sous-rubriques fréquentes : Ouvrages, Articles, Mémoires et thèses, Documents officiels, Webographie.
- Style variable (APA dominant en sciences de l'éducation et en santé) → option de style.

## 9. Lettres et demandes administratives (format camerounais courant)

```
NOM Prénom                                   Yaoundé, le 22 septembre 2026
Adresse / BP
Tél : 6XX XX XX XX

                                             À
                                             Monsieur le Directeur de …
                                             (s/c de …)

Objet : Demande de …
P.J : …

Monsieur le Directeur,

J'ai l'honneur de venir très respectueusement auprès de votre haute
bienveillance solliciter …

Dans l'attente d'une suite favorable, je vous prie d'agréer, Monsieur le
Directeur, l'expression de ma haute considération.

                                                         Signature
                                                         NOM Prénom
```

Éléments variables : « s/c » (sous couvert), timbre fiscal pour certaines demandes officielles, formule d'appel selon le destinataire.

## 10. Paramètres à exposer dans chaque modèle

`institution_lignes[] (FR/EN)`, `separateur`, `logo`, `afficher_republique`, `afficher_ministere`, `type_document`, `titre`, `mention_diplome`, `option/parcours/niveau`, `auteur`, `matricule`, `encadreurs[] (rôle, nom, grade, fonction)`, `jury[]`, `annee_academique`, `date_soutenance`, `police`, `taille`, `interligne`, `marges (h, b, g, d)`, `position_numero_page`, `entete_courant`, `pied_courant`, `style_numerotation_titres`, `position_sommaire`, `table_des_matieres_en_fin`, `pages_prelim[] ordonnées`, `style_bibliographie`.

## 7. Comment l'application applique la pagination (mode « garder mon document »)

- Page de garde : comptée comme « i » mais sans numéro affiché (section Word à part).
- Pages préliminaires (sommaire, dédicace, remerciements, sigles, listes…) : chiffres romains minuscules, la numérotation continue après la page de garde (ii, iii, iv…).
- Corps : chiffres arabes, la numérotation repart à 1 à l'Introduction.
- Sans page préliminaire, le corps commence à 1 juste après la page de garde.
- Un document déjà numéroté (même en chiffres arabes partout, page de garde comprise) est gardé tel quel par défaut ; l'écran d'analyse propose « Refaire aux normes » quand sa numérotation s'écarte de cette convention.
