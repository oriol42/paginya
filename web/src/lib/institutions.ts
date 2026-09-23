/**
 * Official bilingual headers, as printed on real covers (see docs/NORMES-CAMEROUN.md).
 * One line per level; the editor lets users fix/extend them.
 */
export type Institution = {
  id: string;
  short: string;
  fr: string[];
  en: string[];
};

export const INSTITUTIONS: Institution[] = [
  {
    id: "uy1-fs", short: "UY1 · Faculté des Sciences",
    fr: ["UNIVERSITÉ DE YAOUNDÉ I", "FACULTÉ DES SCIENCES"],
    en: ["THE UNIVERSITY OF YAOUNDE I", "FACULTY OF SCIENCE"],
  },
  {
    id: "uy1-falsh", short: "UY1 · FALSH",
    fr: ["UNIVERSITÉ DE YAOUNDÉ I", "FACULTÉ DES ARTS, LETTRES ET SCIENCES HUMAINES"],
    en: ["THE UNIVERSITY OF YAOUNDE I", "FACULTY OF ARTS, LETTERS AND SOCIAL SCIENCES"],
  },
  {
    id: "uy1-fse", short: "UY1 · Sciences de l'Éducation",
    fr: ["UNIVERSITÉ DE YAOUNDÉ I", "FACULTÉ DES SCIENCES DE L'ÉDUCATION"],
    en: ["THE UNIVERSITY OF YAOUNDE I", "FACULTY OF EDUCATION"],
  },
  {
    id: "uy1-fmsb", short: "UY1 · FMSB (Médecine)",
    fr: ["UNIVERSITÉ DE YAOUNDÉ I", "FACULTÉ DE MÉDECINE ET DES SCIENCES BIOMÉDICALES"],
    en: ["THE UNIVERSITY OF YAOUNDE I", "FACULTY OF MEDICINE AND BIOMEDICAL SCIENCES"],
  },
  {
    id: "uy1-ens", short: "ENS Yaoundé",
    fr: ["UNIVERSITÉ DE YAOUNDÉ I", "ÉCOLE NORMALE SUPÉRIEURE"],
    en: ["THE UNIVERSITY OF YAOUNDE I", "HIGHER TEACHER TRAINING COLLEGE"],
  },
  {
    id: "uy1-ensp", short: "Polytechnique Yaoundé (ENSP)",
    fr: ["UNIVERSITÉ DE YAOUNDÉ I", "ÉCOLE NATIONALE SUPÉRIEURE POLYTECHNIQUE"],
    en: ["THE UNIVERSITY OF YAOUNDE I", "NATIONAL ADVANCED SCHOOL OF ENGINEERING"],
  },
  {
    id: "uy2-esstic", short: "UY2 · ESSTIC",
    fr: ["UNIVERSITÉ DE YAOUNDÉ II – SOA", "ÉCOLE SUPÉRIEURE DES SCIENCES ET TECHNIQUES DE L'INFORMATION ET DE LA COMMUNICATION (ESSTIC)"],
    en: ["THE UNIVERSITY OF YAOUNDE II – SOA", "ADVANCED SCHOOL OF MASS COMMUNICATION (ASMAC)"],
  },
  {
    id: "uy2-fsjp", short: "UY2 · Sciences Juridiques et Politiques",
    fr: ["UNIVERSITÉ DE YAOUNDÉ II – SOA", "FACULTÉ DES SCIENCES JURIDIQUES ET POLITIQUES"],
    en: ["THE UNIVERSITY OF YAOUNDE II – SOA", "FACULTY OF LAWS AND POLITICAL SCIENCE"],
  },
  {
    id: "udo-iut", short: "IUT de Douala",
    fr: ["UNIVERSITÉ DE DOUALA", "INSTITUT UNIVERSITAIRE DE TECHNOLOGIE"],
    en: ["THE UNIVERSITY OF DOUALA", "UNIVERSITY INSTITUTE OF TECHNOLOGY"],
  },
  {
    id: "udo-enspd", short: "ENSP Douala",
    fr: ["UNIVERSITÉ DE DOUALA", "ÉCOLE NATIONALE SUPÉRIEURE POLYTECHNIQUE DE DOUALA"],
    en: ["THE UNIVERSITY OF DOUALA", "NATIONAL HIGHER POLYTECHNIC SCHOOL OF DOUALA"],
  },
  {
    id: "uds", short: "Université de Dschang",
    fr: ["UNIVERSITÉ DE DSCHANG"],
    en: ["UNIVERSITY OF DSCHANG"],
  },
  {
    id: "ub", short: "University of Buea",
    fr: ["UNIVERSITÉ DE BUEA"],
    en: ["UNIVERSITY OF BUEA"],
  },
  {
    id: "un", short: "Université de Ngaoundéré",
    fr: ["UNIVERSITÉ DE NGAOUNDÉRÉ"],
    en: ["THE UNIVERSITY OF NGAOUNDERE"],
  },
  {
    id: "autre", short: "Autre établissement / entreprise",
    fr: ["NOM DE L'ÉTABLISSEMENT"],
    en: ["NAME OF THE INSTITUTION"],
  },
];

export const REPUBLIC_FR = ["RÉPUBLIQUE DU CAMEROUN", "Paix – Travail – Patrie"];
export const REPUBLIC_EN = ["REPUBLIC OF CAMEROON", "Peace – Work – Fatherland"];
export const MINISTRY_FR = ["MINISTÈRE DE L'ENSEIGNEMENT SUPÉRIEUR"];
export const MINISTRY_EN = ["MINISTRY OF HIGHER EDUCATION"];

export function institution(id: string): Institution {
  return INSTITUTIONS.find((i) => i.id === id) ?? INSTITUTIONS[INSTITUTIONS.length - 1];
}
