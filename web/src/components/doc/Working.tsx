"use client";

import { useEffect, useState } from "react";
import type { DocMeta } from "@/lib/documents";
import { Icon } from "../Icon";

export type Sending = { name: string; size: number; sent: number };

const kb = (n: number) => (n >= 1e6 ? `${(n / 1e6).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} Mo` : `${Math.max(1, Math.round(n / 1e3))} Ko`);

/** Ring that fills with the real share sent; without a share it turns (the server is working). */
function Ring({ value }: { value?: number }) {
  const c = 2 * Math.PI * 11;
  return (
    <svg viewBox="0 0 28 28" className={`h-7 w-7 shrink-0 -rotate-90 text-board ${value === undefined ? "animate-spin" : ""}`} aria-hidden>
      <circle cx="14" cy="14" r="11" fill="none" stroke="currentColor" strokeOpacity=".15" strokeWidth="3" />
      <circle
        cx="14" cy="14" r="11" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={c * (1 - (value ?? 0.3))} className="transition-[stroke-dashoffset] duration-300"
      />
    </svg>
  );
}

type Props = { meta: DocMeta | null; rendering: boolean; sending?: Sending | null };

/** Loading screen: each step says what is really happening, the upload fills as it is sent. */
export function Working(props: Props) {
  const uploading = !!props.sending && props.sending.sent < 1 && !props.meta;
  const stage = uploading ? "upload" : props.meta ? "layout" : "read";
  // keyed by stage: the clock starts again at each step (the hints speak of the step that is slow)
  return <Steps key={stage} {...props} uploading={uploading} reading={stage === "read"} />;
}

function Steps({ meta, rendering, sending, uploading, reading }: Props & { uploading: boolean; reading: boolean }) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const steps = [
    ...(sending ? [{
      label: uploading ? `Envoi de ton fichier · ${Math.round(sending.sent * 100)} %` : "Fichier envoyé",
      detail: uploading ? `${kb(sending.size * sending.sent)} sur ${kb(sending.size)}` : sending.name,
      state: uploading ? "progress" : "done",
    }] : []),
    {
      label: meta ? `${meta.words.toLocaleString("fr-FR")} mots lus` : "Lecture du texte, des images et des tableaux",
      detail: reading && seconds > 6 ? "Un long document prend un peu plus de temps" : "",
      state: meta ? "done" : reading ? "active" : "todo",
    },
    { label: meta ? `${meta.headings} titres détectés` : "Détection des titres et des chapitres", detail: "", state: meta ? "done" : "todo" },
    {
      label: meta ? `${meta.lists} éléments de liste · ${meta.tables} tableau${meta.tables > 1 ? "x" : ""} · ${meta.figures} image${meta.figures > 1 ? "s" : ""}` : "Listes, tableaux et images",
      detail: "",
      state: meta ? "done" : "todo",
    },
    { label: "Mise en page et pagination", detail: rendering && seconds > 8 ? "On calcule le sommaire et les numéros de page" : "", state: rendering || meta ? "active" : "todo" },
  ];
  const hint = uploading && seconds > 10
    ? "Ta connexion est lente : l'envoi peut prendre une minute. Ne ferme pas la page."
    : "Quelques secondes, même pour un mémoire.";

  return (
    <div className="board flex flex-1 flex-col items-center justify-center px-6 py-14">
      <div className="paper pin-in relative w-full max-w-sm rounded-[2px] px-6 pt-10 pb-6" style={{ ["--tilt" as string]: "-1.5deg" }}>
        <span className="pin top-3 left-1/2 -translate-x-1/2" aria-hidden />
        <h1 className="font-display text-[30px] leading-[0.95] font-black uppercase">On met ton document au propre</h1>
        <ul className="mt-6 space-y-3.5" aria-live="polite">
          {steps.map((s, i) => (
            <li key={i} className="flex items-start gap-3">
              {s.state === "done" ? (
                <span className="rise grid h-7 w-7 shrink-0 place-items-center rounded-full bg-board text-white">
                  <Icon name="check" size={16} stroke={3} />
                </span>
              ) : s.state === "progress" ? (
                <Ring value={sending!.sent} />
              ) : s.state === "active" ? (
                <Ring />
              ) : (
                <span className="h-7 w-7 shrink-0 rounded-full border-2 border-dashed border-ink/25" />
              )}
              <span className="min-w-0 pt-0.5">
                <span className={`block text-[16px] leading-snug ${s.state === "done" || s.state === "progress" || s.state === "active" ? "font-bold" : "text-ink/60"}`}>{s.label}</span>
                {s.detail && <span className="block truncate text-[13px] text-ink/60 tabular">{s.detail}</span>}
              </span>
            </li>
          ))}
        </ul>
      </div>
      <p className="mt-6 max-w-sm text-center text-[15px] text-white/70">{hint}</p>
    </div>
  );
}
