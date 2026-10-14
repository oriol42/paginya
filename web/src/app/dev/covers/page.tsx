"use client";

// Design sandbox: every style rendered with realistic data (not linked from the app).
import { useEffect, useState } from "react";
import { CoverView } from "@/components/CoverView";
import { STYLES, loadCoverFonts, renderCover } from "@/lib/cover";
import { emptyForm } from "@/lib/cover/kinds";
import { PALETTES } from "@/lib/cover/palettes";
import type { CoverForm } from "@/lib/cover/types";

const FORM: CoverForm = {
  ...emptyForm("rapport_stage"),
  institutionId: "uy2-esstic",
  headerFr: "UNIVERSITÉ DE YAOUNDÉ II – SOA\nÉCOLE SUPÉRIEURE DES SCIENCES ET TECHNIQUES DE L'INFORMATION ET DE LA COMMUNICATION (ESSTIC)",
  headerEn: "THE UNIVERSITY OF YAOUNDE II – SOA\nADVANCED SCHOOL OF MASS COMMUNICATION (ASMAC)",
  title: "Gestion électronique des archives dans une institution de microfinance : cas d'ADVANS Cameroun",
  structure: "ADVANS Cameroun, agence de Messassi",
  period: "du 11 juillet au 11 octobre 2026",
  degree: "Licence en Sciences et Techniques de l'Information et de la Communication",
  specialty: "Option : Information documentaire · Parcours : Archivistique",
  authors: [{ name: "NGNICHANG TANDI Honorine", info: "Matricule : 18C0041" }],
  supervisors: [
    { name: "Dr OLEMBE Esther", role: "Encadreur académique", info: "Chargée de cours, ESSTIC" },
    { name: "M. NTI ELOI Pastichant", role: "Encadreur professionnel", info: "Chef du service des archives" },
  ],
  date: "Novembre 2026",
};

const ENGLISH: CoverForm = {
  ...emptyForm("rapport_stage"),
  lang: "en",
  institutionId: "ub-fet",
  headerFr: "UNIVERSITÉ DE BUEA\nFACULTÉ DE GÉNIE ET DE TECHNOLOGIE",
  headerEn: "UNIVERSITY OF BUEA\nFACULTY OF ENGINEERING AND TECHNOLOGY",
  title: "Design and implementation of a stock management system for a pharmacy",
  structure: "MTN Cameroon, Buea branch",
  period: "from 1 July to 30 September 2026",
  degree: "the Bachelor of Engineering (B.Eng) degree in Computer Engineering",
  specialty: "Option: Software Engineering",
  authors: [{ name: "NGWA Blessing Fru", info: "Matricule: FE21A256" }],
  supervisors: [
    { name: "Dr TABI Peter", role: "Encadreur académique", info: "Senior Lecturer" },
    { name: "Mr. EBAI John", role: "Encadreur professionnel", info: "IT Manager" },
  ],
  date: "October 2026",
};

export default function DevCovers() {
  const [ready, setReady] = useState(false);
  useEffect(() => { loadCoverFonts().then(() => setReady(true)); }, []);
  if (!ready || process.env.NODE_ENV === "production") return null;
  return (
    <div className="grid grid-cols-2 gap-6 bg-slate-100 p-6 lg:grid-cols-4">
      <textarea id="export-svg" readOnly hidden value={renderCover(FORM, "officiel", { palette: PALETTES[0], mono: false, frame: true }, false)} />
      {STYLES.map((s, i) => (
        <div key={s.id}>
          <p className="mb-2 font-bold">{s.name}</p>
          <CoverView svg={renderCover(FORM, s.id, { palette: PALETTES[i], mono: false, frame: true })} />
        </div>
      ))}
      {STYLES.map((s, i) => (
        <div key={`${s.id}-en`}>
          <p className="mb-2 font-bold">{s.name} · English · {["tinos", "poppins", "playfair", "inter"][i % 4]}</p>
          <CoverView svg={renderCover(ENGLISH, s.id, { palette: PALETTES[(i + 9) % PALETTES.length], mono: false, frame: true, font: (["tinos", "poppins", "playfair", "inter"] as const)[i % 4] }, false)} />
        </div>
      ))}
      {STYLES.map((s) => (
        <div key={`${s.id}-mono`}>
          <p className="mb-2 font-bold">{s.name} · N&amp;B · vide</p>
          <CoverView svg={renderCover(emptyForm("memoire"), s.id, { palette: PALETTES[0], mono: true, frame: true })} />
        </div>
      ))}
    </div>
  );
}
