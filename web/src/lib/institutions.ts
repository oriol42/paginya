/**
 * Official bilingual headers, as printed on real covers (see docs/NORMES-CAMEROUN.md).
 * One line per level; the editor lets users fix/extend them.
 *
 * `logo`: file in /public/logos (collected from Wikipedia and the schools' own websites, see
 * docs/LOGOS.md). Logos belong to their institutions: they are offered so their students and staff
 * can put them on their own documents, and are removed on request.
 */
export type Institution = {
  id: string;
  short: string;
  fr: string[];
  en: string[];
  logo?: string; // university (or the school's only logo)
  logo2?: string; // the faculty / school's own logo, drawn on the other side of the cover
  secondary?: boolean; // secondary school: Ministry of Secondary Education
};

// [french, english, university logo]
const UY1 = ["UNIVERSITÉ DE YAOUNDÉ I", "THE UNIVERSITY OF YAOUNDE I", "uy1"];
const UY2 = ["UNIVERSITÉ DE YAOUNDÉ II – SOA", "THE UNIVERSITY OF YAOUNDE II – SOA", "uy2"];
const UDO = ["UNIVERSITÉ DE DOUALA", "THE UNIVERSITY OF DOUALA", "udo"];
const UDS = ["UNIVERSITÉ DE DSCHANG", "UNIVERSITY OF DSCHANG", "uds"];
const UN = ["UNIVERSITÉ DE NGAOUNDÉRÉ", "THE UNIVERSITY OF NGAOUNDERE", ""];
const UMA = ["UNIVERSITÉ DE MAROUA", "THE UNIVERSITY OF MAROUA", "uma"];

/** A faculty/school of a university carries both logos: the university's and its own (when we have it). */
function school(id: string, short: string, uni: string[] | null, fr: string, en: string, logo?: string): Institution {
  if (!uni) return { id, short, fr: [fr], en: [en], logo };
  const uniLogo = uni[2] || undefined;
  const own = logo && logo !== uniLogo ? logo : undefined;
  return { id, short, fr: [uni[0], fr], en: [uni[1], en], logo: uniLogo ?? own, logo2: uniLogo ? own : undefined };
}

export const INSTITUTIONS: Institution[] = [
  // --- Public universities
  school("uy1", "Université de Yaoundé I", null, UY1[0], UY1[1], "uy1"),
  school("uy1-fs", "UY1 · Faculté des Sciences", UY1, "FACULTÉ DES SCIENCES", "FACULTY OF SCIENCE", "uy1"),
  school("uy1-falsh", "UY1 · FALSH", UY1, "FACULTÉ DES ARTS, LETTRES ET SCIENCES HUMAINES", "FACULTY OF ARTS, LETTERS AND SOCIAL SCIENCES", "uy1"),
  school("uy1-fse", "UY1 · Sciences de l'Éducation", UY1, "FACULTÉ DES SCIENCES DE L'ÉDUCATION", "FACULTY OF EDUCATION", "uy1"),
  school("uy1-fmsb", "UY1 · FMSB (Médecine)", UY1, "FACULTÉ DE MÉDECINE ET DES SCIENCES BIOMÉDICALES", "FACULTY OF MEDICINE AND BIOMEDICAL SCIENCES", "uy1"),
  school("uy1-ens", "ENS Yaoundé", UY1, "ÉCOLE NORMALE SUPÉRIEURE", "HIGHER TEACHER TRAINING COLLEGE", "ens"),
  school("uy1-ensp", "Polytechnique Yaoundé (ENSPY)", UY1, "ÉCOLE NATIONALE SUPÉRIEURE POLYTECHNIQUE", "NATIONAL ADVANCED SCHOOL OF ENGINEERING", "ensp"),
  school("uy2", "Université de Yaoundé II – Soa", null, UY2[0], UY2[1], "uy2"),
  school("uy2-fsjp", "UY2 · Sciences Juridiques et Politiques", UY2, "FACULTÉ DES SCIENCES JURIDIQUES ET POLITIQUES", "FACULTY OF LAWS AND POLITICAL SCIENCE", "uy2"),
  school("uy2-fseg", "UY2 · Sciences Économiques et de Gestion", UY2, "FACULTÉ DES SCIENCES ÉCONOMIQUES ET DE GESTION", "FACULTY OF ECONOMICS AND MANAGEMENT", "uy2"),
  school("uy2-esstic", "UY2 · ESSTIC", UY2, "ÉCOLE SUPÉRIEURE DES SCIENCES ET TECHNIQUES DE L'INFORMATION ET DE LA COMMUNICATION (ESSTIC)", "ADVANCED SCHOOL OF MASS COMMUNICATION (ASMAC)", "esstic"),
  school("uy2-iric", "UY2 · IRIC", UY2, "INSTITUT DES RELATIONS INTERNATIONALES DU CAMEROUN", "INTERNATIONAL RELATIONS INSTITUTE OF CAMEROON", "iric"),
  school("udo", "Université de Douala", null, UDO[0], UDO[1], "udo"),
  school("udo-iut", "IUT de Douala", UDO, "INSTITUT UNIVERSITAIRE DE TECHNOLOGIE", "UNIVERSITY INSTITUTE OF TECHNOLOGY", "iutd"),
  school("udo-enspd", "ENSP Douala (ENSPD)", UDO, "ÉCOLE NATIONALE SUPÉRIEURE POLYTECHNIQUE DE DOUALA", "NATIONAL HIGHER POLYTECHNIC SCHOOL OF DOUALA", "enspd"),
  school("udo-essec", "ESSEC Douala", UDO, "ÉCOLE SUPÉRIEURE DES SCIENCES ÉCONOMIQUES ET COMMERCIALES", "HIGHER SCHOOL OF ECONOMICS AND COMMERCE", "udo"),
  school("udo-enset", "ENSET Douala", UDO, "ÉCOLE NORMALE SUPÉRIEURE D'ENSEIGNEMENT TECHNIQUE", "HIGHER TECHNICAL TEACHER TRAINING COLLEGE", "udo"),
  school("udo-fgi", "Faculté de Génie Industriel (Douala)", UDO, "FACULTÉ DE GÉNIE INDUSTRIEL", "FACULTY OF INDUSTRIAL ENGINEERING", "udo"),
  school("udo-fse", "UDo · Sciences Économiques et Gestion Appliquée", UDO, "FACULTÉ DES SCIENCES ÉCONOMIQUES ET DE GESTION APPLIQUÉE", "FACULTY OF ECONOMICS AND APPLIED MANAGEMENT", "udo"),
  school("uds", "Université de Dschang", null, UDS[0], UDS[1], "uds"),
  school("uds-fasa", "UDs · FASA (Agronomie)", UDS, "FACULTÉ D'AGRONOMIE ET DES SCIENCES AGRICOLES", "FACULTY OF AGRONOMY AND AGRICULTURAL SCIENCES", "uds"),
  school("uds-iutfv", "IUT Fotso Victor de Bandjoun", UDS, "INSTITUT UNIVERSITAIRE DE TECHNOLOGIE FOTSO VICTOR", "FOTSO VICTOR UNIVERSITY INSTITUTE OF TECHNOLOGY", "uds"),
  school("ub", "University of Buea", null, "UNIVERSITÉ DE BUEA", "UNIVERSITY OF BUEA", "ub"),
  school("uba", "University of Bamenda", null, "UNIVERSITÉ DE BAMENDA", "THE UNIVERSITY OF BAMENDA", "uba"),
  school("un", "Université de Ngaoundéré", null, UN[0], UN[1]),
  school("un-ensai", "ENSAI Ngaoundéré", UN, "ÉCOLE NATIONALE SUPÉRIEURE DES SCIENCES AGRO-INDUSTRIELLES", "NATIONAL SCHOOL OF AGRO-INDUSTRIAL SCIENCES"),
  school("uma", "Université de Maroua", null, UMA[0], UMA[1], "uma"),
  school("uma-enspm", "Polytechnique Maroua (ENSPM)", UMA, "ÉCOLE NATIONALE SUPÉRIEURE POLYTECHNIQUE DE MAROUA", "NATIONAL ADVANCED SCHOOL OF ENGINEERING OF MAROUA", "uma"),
  school("ug", "Université de Garoua", null, "UNIVERSITÉ DE GAROUA", "THE UNIVERSITY OF GAROUA", "ug"),
  school("ubt", "Université de Bertoua", null, "UNIVERSITÉ DE BERTOUA", "THE UNIVERSITY OF BERTOUA", "ubt"),
  school("ueb", "Université d'Ebolowa", null, "UNIVERSITÉ D'EBOLOWA", "THE UNIVERSITY OF EBOLOWA"),
  // --- Grandes écoles
  school("enam", "ENAM", null, "ÉCOLE NATIONALE D'ADMINISTRATION ET DE MAGISTRATURE", "NATIONAL SCHOOL OF ADMINISTRATION AND MAGISTRACY", "enam"),
  school("enstp", "ENSTP Yaoundé (Travaux Publics)", null, "ÉCOLE NATIONALE SUPÉRIEURE DES TRAVAUX PUBLICS", "NATIONAL ADVANCED SCHOOL OF PUBLIC WORKS", "enstp"),
  school("supptic", "SUP'PTIC", null, "ÉCOLE NATIONALE SUPÉRIEURE DES POSTES, DES TÉLÉCOMMUNICATIONS ET DES TIC", "NATIONAL ADVANCED SCHOOL OF POSTS, TELECOMMUNICATIONS AND ICT"),
  school("issea", "ISSEA", null, "INSTITUT SOUS-RÉGIONAL DE STATISTIQUE ET D'ÉCONOMIE APPLIQUÉE", "SUB-REGIONAL INSTITUTE OF STATISTICS AND APPLIED ECONOMICS"),
  school("iai", "IAI Cameroun", null, "INSTITUT AFRICAIN D'INFORMATIQUE – CAMEROUN", "AFRICAN INSTITUTE OF COMPUTER SCIENCES – CAMEROON", "iai"),
  // --- Private universities and institutes
  school("ucac", "UCAC (Université Catholique d'Afrique Centrale)", null, "UNIVERSITÉ CATHOLIQUE D'AFRIQUE CENTRALE", "CATHOLIC UNIVERSITY OF CENTRAL AFRICA", "ucac"),
  school("udm", "Université des Montagnes", null, "UNIVERSITÉ DES MONTAGNES", "UNIVERSITÉ DES MONTAGNES", "udm"),
  school("cosendai", "Université Adventiste Cosendai", null, "UNIVERSITÉ ADVENTISTE COSENDAI", "COSENDAI ADVENTIST UNIVERSITY", "cosendai"),
  school("ictu", "The ICT University", null, "THE ICT UNIVERSITY", "THE ICT UNIVERSITY", "ictu"),
  school("cuib", "Catholic University Institute of Buea", null, "INSTITUT UNIVERSITAIRE CATHOLIQUE DE BUEA", "CATHOLIC UNIVERSITY INSTITUTE OF BUEA", "cuib"),
  school("iujns", "Institut Universitaire Joseph Ndi Samba", null, "INSTITUT UNIVERSITAIRE JOSEPH NDI SAMBA", "JOSEPH NDI SAMBA UNIVERSITY INSTITUTE", "iujns"),
  school("iuc", "IUC Douala", null, "INSTITUT UNIVERSITAIRE DE LA CÔTE", "UNIVERSITY INSTITUTE OF THE COAST"),
  school("siantou", "Institut Universitaire Siantou", null, "INSTITUT UNIVERSITAIRE SIANTOU", "SIANTOU UNIVERSITY INSTITUTE"),
  school("upac", "UPAC (Université Protestante d'Afrique Centrale)", null, "UNIVERSITÉ PROTESTANTE D'AFRIQUE CENTRALE", "PROTESTANT UNIVERSITY OF CENTRAL AFRICA"),
  // --- Secondary
  { id: "lycee", short: "Lycée / collège", fr: ["LYCÉE DE …"], en: ["… HIGH SCHOOL"], secondary: true },
  { id: "autre", short: "Autre établissement / entreprise", fr: ["NOM DE L'ÉTABLISSEMENT"], en: ["NAME OF THE INSTITUTION"] },
];

export const REPUBLIC_FR = ["RÉPUBLIQUE DU CAMEROUN", "Paix – Travail – Patrie"];
export const REPUBLIC_EN = ["REPUBLIC OF CAMEROON", "Peace – Work – Fatherland"];
export const MINISTRY_FR = ["MINISTÈRE DE L'ENSEIGNEMENT SUPÉRIEUR"];
export const MINISTRY_EN = ["MINISTRY OF HIGHER EDUCATION"];
export const MINESEC_FR = ["MINISTÈRE DES ENSEIGNEMENTS SECONDAIRES"];
export const MINESEC_EN = ["MINISTRY OF SECONDARY EDUCATION"];
/** Coat of arms of Cameroon (public domain): the emblem used on State documents when there is no school logo. */
export const ARMOIRIES = "/logos/armoiries.png";

export function institution(id: string): Institution {
  return INSTITUTIONS.find((i) => i.id === id) ?? INSTITUTIONS[INSTITUTIONS.length - 1];
}

/** Logo as a data: URL (covers are SVG files sent to the server: images must be embedded). */
export async function logoData(name: string): Promise<string | undefined> {
  try {
    const blob = await (await fetch(name.startsWith("/") ? name : `/logos/${name}.png`)).blob();
    return await new Promise((res) => {
      const r = new FileReader();
      r.onload = () => res(String(r.result));
      r.onerror = () => res(undefined);
      r.readAsDataURL(blob);
    });
  } catch {
    return undefined;
  }
}
