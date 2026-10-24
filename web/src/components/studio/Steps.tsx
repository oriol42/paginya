"use client";

import { useState } from "react";
import { DEFAULT_LABELS, KINDS, type FieldKey } from "@/lib/cover/kinds";
import type { CoverForm, Person } from "@/lib/cover/types";
import { INSTITUTIONS, institution, logoData } from "@/lib/institutions";
import { DEPARTMENTS } from "@/lib/departments";
import { Field, Input, Select, TextArea, Toggle } from "../ui";
import { Icon } from "@/components/Icon";

type StepProps = { form: CoverForm; onChange: (patch: Partial<CoverForm>) => void };

export async function readLogo(file: File): Promise<string> {
  const url = URL.createObjectURL(file);
  try {
    const img = new Image();
    img.src = url;
    await img.decode();
    const scale = Math.min(1, 360 / Math.max(img.width, img.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(img.width * scale);
    canvas.height = Math.round(img.height * scale);
    canvas.getContext("2d")!.drawImage(img, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/png");
  } finally {
    URL.revokeObjectURL(url);
  }
}


/** The department under the faculty: picked in the list of this school, or typed. Rewrites the header's last line. */
function DepartmentPicker({ form, onChange }: StepProps) {
  const inst = institution(form.institutionId);
  const list = DEPARTMENTS[inst.id] ?? [];
  const lines = form.headerFr.split("\n");
  const extra = lines.length > inst.fr.length ? lines[lines.length - 1] : "";
  const known = list.findIndex(([fr]) => fr === extra);
  const [typing, setTyping] = useState(!!extra && known < 0);
  const set = (fr: string, en: string) =>
    onChange({ headerFr: [...inst.fr, ...(fr ? [fr] : [])].join("\n"), headerEn: [...inst.en, ...(en ? [en] : [])].join("\n") });

  return (
    <div className="mt-3 grid gap-2">
      <span className="text-[13px] font-bold tracking-wide text-ink/80">Département ou filière (facultatif)</span>
      <Select
        aria-label="Département ou filière"
        value={typing ? "autre" : known >= 0 ? String(known) : ""}
        onChange={(e) => {
          const v = e.target.value;
          setTyping(v === "autre");
          if (v === "" || v === "autre") set("", "");
          else set(...list[Number(v)]);
        }}
      >
        <option value="">Aucun (seulement la faculté ou l&apos;école)</option>
        {list.map(([fr], i) => <option key={fr} value={i}>{fr.replace(/^(DÉPARTEMENT (DE LA |DES |DE L'|DE |D')|FILIÈRE : )/, "").toLowerCase().replace(/^./, (c) => c.toUpperCase())}</option>)}
        <option value="autre">Autre : je l&apos;écris</option>
      </Select>
      {typing && (
        <Input
          value={extra}
          placeholder="Ex. : DÉPARTEMENT DE GÉOGRAPHIE"
          onChange={(e) => set(e.target.value.toUpperCase(), e.target.value.toUpperCase())}
        />
      )}
    </div>
  );
}


/** Step 1: only what every cover needs. */
export function EssentialsStep({ form, onChange }: StepProps) {
  const def = KINDS[form.kind];
  const [custom, setCustom] = useState(form.institutionId === "autre");
  const author = form.authors[0] ?? { name: "", info: "" };
  const setAuthor = (patch: Partial<Person>) => onChange({ authors: [{ ...author, ...patch }, ...form.authors.slice(1)] });

  return (
    <div className="space-y-5">
      {def.academic ? (
        <Field label="Ton établissement">
          <Select
            value={form.institutionId}
            onChange={async (e) => {
              const inst = institution(e.target.value);
              onChange({ institutionId: inst.id, headerFr: inst.fr.join("\n"), headerEn: inst.en.join("\n"), lang: inst.english ? "en" : "fr" });
              setCustom(inst.id === "autre" || inst.id === "lycee");
              // the school's logos come with it (the user can still change or remove them)
              const [logo, logo2] = await Promise.all([inst.logo ? logoData(inst.logo) : undefined, inst.logo2 ? logoData(inst.logo2) : undefined]);
              onChange({ logo, logo2 });
            }}
          >
            {INSTITUTIONS.map((i) => <option key={i.id} value={i.id}>{i.id === "autre" ? "Mon école n'est pas dans la liste" : i.short}</option>)}
          </Select>
          {custom && (
            <div className="mt-3 grid gap-3 border-l-2 border-board/30 pl-3">
              <TextArea rows={3} value={form.headerFr} placeholder={"UNIVERSITÉ DE …\nFACULTÉ DE …\nDÉPARTEMENT DE …"} onChange={(e) => onChange({ headerFr: e.target.value })} />
              <TextArea rows={3} value={form.headerEn} placeholder={"UNIVERSITY OF …\nFACULTY OF …\nDEPARTMENT OF …"} onChange={(e) => onChange({ headerEn: e.target.value })} />
              <p className="text-xs text-ink/60">Une ligne par niveau : français en haut, anglais en bas.</p>
            </div>
          )}
          {!custom && DEPARTMENTS[form.institutionId] && <DepartmentPicker form={form} onChange={onChange} />}
          <div className="mt-3 flex items-center gap-2 text-[14px]">
            <span className="text-ink/70">Langue de la page :</span>
            {(["fr", "en"] as const).map((l) => (
              <button
                key={l}
                type="button"
                aria-pressed={(form.lang ?? "fr") === l}
                onClick={() => onChange({ lang: l })}
                className={`press rounded-md px-3 py-1.5 font-bold ${(form.lang ?? "fr") === l ? "bg-ink text-white" : "bg-paper text-ink/80 ring-1 ring-black/10"}`}
              >
                {l === "fr" ? "Français d'abord" : "English first"}
              </button>
            ))}
          </div>
        </Field>
      ) : (
        <Field label="Entreprise, association ou école">
          <Input value={form.headerFr} placeholder="Ex. : KAMER AGRO SARL" onChange={(e) => onChange({ headerFr: e.target.value })} />
        </Field>
      )}

      <Field label={def.labels.title ?? "Titre"}>
        <TextArea rows={3} value={form.title} placeholder={def.placeholders.title} onChange={(e) => onChange({ title: e.target.value })} />
      </Field>

      <div className="grid grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] gap-3">
        <Field label={form.kind === "expose" ? "Ton nom (groupe : à l'étape suivante)" : "Ton nom"}>
          <Input value={author.name} placeholder="NOM Prénom" autoComplete="name" onChange={(e) => setAuthor({ name: e.target.value })} />
        </Field>
        <Field label={def.academic ? "Matricule" : "Fonction"}>
          <Input value={author.info ?? ""} placeholder={def.academic ? "20V3543" : "Facultatif"} onChange={(e) => setAuthor({ info: e.target.value })} />
        </Field>
      </div>
    </div>
  );
}

/** Step 2: everything optional, grouped. */
export function DetailsStep({ form, onChange }: StepProps) {
  const def = KINDS[form.kind];
  const has = (k: FieldKey) => def.fields.includes(k);
  const label = (k: FieldKey) => def.labels[k] ?? DEFAULT_LABELS[k];
  const text = (k: "structure" | "period" | "degree" | "specialty" | "place" | "year" | "date") =>
    has(k) && (
      <Field key={k} label={label(k)}>
        <Input value={form[k]} placeholder={def.placeholders[k] ?? ""} onChange={(e) => onChange({ [k]: e.target.value })} />
      </Field>
    );
  const setPerson = (list: "authors" | "supervisors", i: number, patch: Partial<Person>) =>
    onChange({ [list]: form[list].map((p, j) => (j === i ? { ...p, ...patch } : p)) });

  return (
    <div className="space-y-7">
      {(has("structure") || has("period") || has("degree") || has("specialty")) && (
        <Group title="Le cadre">
          {text("structure")}
          {text("period")}
          {text("degree")}
          {text("specialty")}
        </Group>
      )}

      {form.supervisors.length > 0 && (
        <Group title="Encadrement">
          {form.supervisors.map((s, i) => (
            <div key={i} className="grid gap-2 rounded-md bg-paper p-3 ring-1 ring-black/5">
              <p className="text-xs font-bold tracking-wide text-brand-700 uppercase">{s.role}</p>
              <Input value={s.name} placeholder="Ex. : Dr MBALLA Paul" onChange={(e) => setPerson("supervisors", i, { name: e.target.value })} />
              <Input value={s.info ?? ""} placeholder="Grade / fonction (facultatif)" onChange={(e) => setPerson("supervisors", i, { info: e.target.value })} />
            </div>
          ))}
        </Group>
      )}

      {(form.kind === "expose" || form.kind === "rapport_projet") && (
        <Group title="Membres du groupe">
          {form.authors.map((a, i) => (
            <div key={i} className="flex gap-2">
              <Input value={a.name} placeholder={`Membre ${i + 1}`} onChange={(e) => setPerson("authors", i, { name: e.target.value })} />
              {i > 0 && (
                <button type="button" onClick={() => onChange({ authors: form.authors.filter((_, j) => j !== i) })} className="shrink-0 rounded-md px-4 text-ink/45 ring-1 ring-black/10" aria-label="Retirer"><Icon name="x" size={16} /></button>
              )}
            </div>
          ))}
          {form.authors.length < 8 && (
            <button type="button" onClick={() => onChange({ authors: [...form.authors, { name: "", info: "" }] })} className="w-full rounded-md border border-dashed border-brand-300 py-3 text-sm font-bold text-brand-700">
              + Ajouter un membre
            </button>
          )}
        </Group>
      )}

      {has("jury") && (
        <Group title="Jury (facultatif)">
          <TextArea rows={3} value={form.jury} placeholder={def.placeholders.jury} onChange={(e) => onChange({ jury: e.target.value })} />
        </Group>
      )}

      <Group title="Date">
        <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-3">
          {has("year") ? text("year") : text("place")}
          {text("date")}
        </div>
      </Group>

      <Group title="Logos et en-tête">
        <LogoPicker logo={form.logo} onChange={(logo) => onChange({ logo })} label={def.academic ? "Logo de l'université" : "Logo"} />
        {def.academic && <LogoPicker logo={form.logo2} onChange={(logo2) => onChange({ logo2 })} label="Logo de la faculté / de l'école" />}
        {def.academic && (
          <div className="grid gap-2">
            <Toggle label="République du Cameroun · Paix-Travail-Patrie" checked={form.showRepublic} onChange={(v) => onChange({ showRepublic: v })} />
            <Toggle label="Ministère de l'Enseignement Supérieur" checked={form.showMinistry} onChange={(v) => onChange({ showMinistry: v })} />
          </div>
        )}
      </Group>
    </div>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h3 className="font-display text-[19px] leading-none font-black text-ink uppercase">{title}</h3>
      {children}
    </section>
  );
}

/** Every logo we have, once, named after the school that uses it (the faculty's own logo first). */
function logoChoices(): { file: string; name: string }[] {
  const seen = new Map<string, string>([["armoiries", "Armoiries du Cameroun"]]);
  for (const i of INSTITUTIONS) {
    if (i.logo2 && !seen.has(i.logo2)) seen.set(i.logo2, i.short);
    if (i.logo && !seen.has(i.logo)) seen.set(i.logo, i.logo2 ? i.short.split(" · ")[0] : i.short);
  }
  return [...seen].map(([file, name]) => ({ file, name }));
}

export function LogoPicker({ logo, onChange, label = "Logo de l'école" }: { logo?: string; onChange: (l?: string) => void; label?: string }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const plain = (t: string) => t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const choices = open ? logoChoices().filter((c) => plain(`${c.name} ${c.file}`).includes(plain(q))) : [];
  return (
    <div className="border-t border-ink/10 pt-3">
      <div className="flex flex-wrap items-center gap-3">
        {logo ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={logo} alt="Logo" className="h-14 w-14 rounded-md object-contain" />
        ) : (
          <span className="grid h-14 w-14 place-items-center rounded-md bg-ink/5 text-board"><Icon name="landmark" size={26} /></span>
        )}
        <div className="min-w-[9rem] flex-1">
          <p className="text-sm font-semibold text-ink">{label}</p>
          <p className="text-xs text-ink/60">{logo ? "Ajouté" : "Dans notre liste, ou ta propre image"}</p>
        </div>
        <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="press rounded-md bg-board px-3.5 py-2.5 text-sm font-bold text-white">
          {open ? "Fermer" : "Choisir"}
        </button>
        <label className="press cursor-pointer rounded-md px-3 py-2.5 text-sm font-bold text-ink ring-1 ring-black/15">
          Mon image
          <input type="file" accept="image/*" className="hidden" onChange={async (e) => { const f = e.target.files?.[0]; if (f) onChange(await readLogo(f)); }} />
        </label>
        {logo && <button type="button" onClick={() => onChange(undefined)} className="text-ink/45" aria-label="Retirer le logo"><Icon name="x" size={16} /></button>}
      </div>
      {open && (
        <div className="mt-3 rounded-md bg-ink/[0.04] p-3">
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cherche ton école : ENS, Dschang, FSEG…" aria-label="Chercher un logo" />
          <div className="mt-3 grid max-h-64 grid-cols-3 gap-2 overflow-y-auto sm:grid-cols-4">
            {choices.map((c) => (
              <button
                key={c.file}
                type="button"
                onClick={async () => { onChange(await logoData(c.file)); setOpen(false); }}
                className="press flex flex-col items-center gap-1 rounded-md bg-paper p-2 text-center ring-1 ring-black/10 hover:ring-ink/40"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={`/logos/${c.file}.png`} alt="" loading="lazy" className="h-12 w-12 object-contain" />
                <span className="line-clamp-2 text-[11px] leading-tight text-ink/75">{c.name}</span>
              </button>
            ))}
            {choices.length === 0 && <p className="col-span-full text-[13px] text-ink/60">Pas trouvé : ajoute ta propre image avec « Mon image ».</p>}
          </div>
        </div>
      )}
    </div>
  );
}
