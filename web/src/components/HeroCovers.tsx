"use client";

import { useEffect, useState } from "react";
import { loadCoverFonts, renderCover } from "@/lib/cover";
import { emptyForm } from "@/lib/cover/kinds";
import { PALETTES } from "@/lib/cover/palettes";
import type { CoverForm, StyleId } from "@/lib/cover/types";
import { CoverView } from "./CoverView";

const SAMPLES: { style: StyleId; palette: number; form: Partial<CoverForm> }[] = [
  {
    style: "officiel", palette: 1,
    form: {
      kind: "memoire", docLabel: "MÉMOIRE",
      title: "Intégration des TIC et efficacité pédagogique des enseignants",
      degree: "Master en Sciences de l'Éducation",
      authors: [{ name: "NGANDO Modestine", info: "Matricule : 20V3543" }],
      supervisors: [{ name: "Pr BELINGA Simon", role: "Sous la direction de", info: "Professeur" }],
    },
  },
  {
    style: "moderne", palette: 0,
    form: {
      kind: "rapport_stage", docLabel: "RAPPORT DE STAGE",
      title: "Digitalisation du service client d'une microfinance",
      structure: "ADVANS Cameroun", period: "du 4 juillet au 4 octobre 2026",
      authors: [{ name: "MBALLA Junior", info: "Licence 3 · Marketing" }],
      supervisors: [{ name: "Dr ESSOMBA Claire", role: "Encadreur académique", info: "Chargée de cours" }, { name: "M. NGUELE Paul", role: "Encadreur professionnel", info: "Chef d'agence" }],
    },
  },
  {
    style: "corporate", palette: 3,
    form: {
      kind: "rapport_pro", docLabel: "RAPPORT D'ACTIVITÉ", institutionId: "autre",
      headerFr: "KAMER AGRO SARL", title: "Bilan des activités 2026",
      authors: [{ name: "Direction générale" }], place: "Douala", date: "Janvier 2027", year: "",
    },
  },
];

export function HeroCovers() {
  const [svgs, setSvgs] = useState<string[] | null>(null);

  useEffect(() => {
    loadCoverFonts().then(() =>
      setSvgs(
        SAMPLES.map((s) =>
          renderCover({ ...emptyForm(s.form.kind), ...s.form } as CoverForm, s.style, {
            palette: PALETTES[s.palette], mono: false, frame: s.style === "officiel",
          }),
        ),
      ),
    );
  }, []);

  const pose = [
    "-rotate-[8deg] -translate-x-[58%] translate-y-4",
    "z-10 -translate-y-2",
    "rotate-[8deg] translate-x-[58%] translate-y-4",
  ];

  return (
    <div className="relative mx-auto flex h-[340px] w-full max-w-md items-center justify-center sm:h-[420px]">
      <div className="absolute inset-x-6 bottom-6 top-10 rounded-full bg-brand-200/50 blur-3xl" />
      {SAMPLES.map((_, i) => (
        <div key={i} className={`absolute w-[46%] max-w-[210px] transition-transform duration-700 ${pose[i]}`}>
          {svgs ? <CoverView svg={svgs[i]} /> : <div className="aspect-[595/842] rounded bg-white/70 shadow" />}
        </div>
      ))}
    </div>
  );
}
