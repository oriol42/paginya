"use client";

import { useState } from "react";
import type { Letterhead } from "@/lib/documents";
import {
  ARMOIRIES, INSTITUTIONS, MINESEC_EN, MINESEC_FR, MINISTRY_EN, MINISTRY_FR, REPUBLIC_EN, REPUBLIC_FR, institution, logoData,
} from "@/lib/institutions";
import { LogoPicker } from "../studio/Steps";
import { Select, TextArea, Toggle } from "../ui";

type Props = { enabled: boolean; value: Letterhead | null; onChange: (value: Letterhead, enabled: boolean) => void };

type Form = { institutionId: string; republic: boolean; ministry: boolean; fr: string; en: string; logo?: string };

/** Groups as stored: Republic, Ministry, then one group per institution line. */
function build(f: Form): Letterhead {
  const inst = institution(f.institutionId);
  const fr: string[][] = [];
  const en: string[][] = [];
  if (f.republic) { fr.push(REPUBLIC_FR); en.push(REPUBLIC_EN); }
  if (f.ministry) { fr.push(inst.secondary ? MINESEC_FR : MINISTRY_FR); en.push(inst.secondary ? MINESEC_EN : MINISTRY_EN); }
  const lines = (s: string) => s.split("\n").map((l) => l.trim()).filter(Boolean).map((l) => [l]);
  fr.push(...lines(f.fr));
  en.push(...lines(f.en));
  return { fr, en, logo: f.logo ?? null, institutionId: f.institutionId };
}

function fromValue(v: Letterhead | null): Form {
  if (!v) return { institutionId: "autre", republic: true, ministry: true, fr: "", en: "" };
  const isRep = (g: string[]) => g[0] === REPUBLIC_FR[0];
  const isMin = (g: string[]) => g[0] === MINISTRY_FR[0] || g[0] === MINESEC_FR[0];
  const rest = (gs: string[][]) => gs.filter((g) => !isRep(g) && !isMin(g)).map((g) => g.join("\n")).join("\n");
  return {
    institutionId: v.institutionId || "autre", republic: v.fr.some(isRep), ministry: v.fr.some(isMin),
    fr: rest(v.fr), en: rest(v.en), logo: v.logo ?? undefined,
  };
}

/** Official Cameroonian header on page 1 (French | logo | English), for documents without a cover page. */
export function LetterheadPanel({ enabled, value, onChange }: Props) {
  const [form, setForm] = useState<Form>(() => fromValue(value));
  const save = (patch: Partial<Form>, on = enabled) => {
    const next = { ...form, ...patch };
    setForm(next);
    onChange(build(next), on);
  };

  return (
    <div>
      <Toggle label="En-tête officiel (République du Cameroun, école, logo)" checked={enabled} onChange={(on) => save({}, on)} />
      {enabled && (
        <div className="mt-3 grid gap-3">
          <Select
            value={form.institutionId}
            onChange={async (e) => {
              const inst = institution(e.target.value);
              const logo = inst.logo ? await logoData(inst.logo) : form.logo;
              save({ institutionId: inst.id, fr: inst.id === "autre" ? "" : inst.fr.join("\n"), en: inst.id === "autre" ? "" : inst.en.join("\n"), logo });
            }}
            aria-label="Établissement"
          >
            {INSTITUTIONS.map((i) => <option key={i.id} value={i.id}>{i.id === "autre" ? "Autre (je tape le nom)" : i.short}</option>)}
          </Select>
          <label className="grid gap-1 text-xs font-semibold text-ink/60">
            Français (une ligne par niveau)
            <TextArea rows={2} value={form.fr} placeholder={"UNIVERSITÉ DE …\nFACULTÉ DE …"} onChange={(e) => save({ fr: e.target.value })} />
          </label>
          <label className="grid gap-1 text-xs font-semibold text-ink/60">
            Anglais
            <TextArea rows={2} value={form.en} placeholder={"UNIVERSITY OF …\nFACULTY OF …"} onChange={(e) => save({ en: e.target.value })} />
          </label>
          <Toggle label="République du Cameroun · Paix – Travail – Patrie" checked={form.republic} onChange={(republic) => save({ republic })} />
          <Toggle label="Ministère" checked={form.ministry} onChange={(ministry) => save({ ministry })} />
          <LogoPicker logo={form.logo} onChange={(logo) => save({ logo })} />
          {!form.logo && (
            <button type="button" onClick={async () => save({ logo: await logoData(ARMOIRIES) })} className="text-left text-xs font-semibold text-pen underline">
              Mettre les armoiries du Cameroun au centre
            </button>
          )}
        </div>
      )}
    </div>
  );
}
