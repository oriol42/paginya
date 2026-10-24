"use client";

import { useState } from "react";
import { docs, type Block, type SpellFix } from "@/lib/documents";
import { Icon } from "../Icon";
import { Toggle } from "../ui";

/** Word-level difference: [text, "same" | "del" | "ins"] (longest common subsequence, paragraphs are short). */
function diffWords(a: string, b: string): [string, "same" | "del" | "ins"][] {
  const x = a.split(/(\s+)/), y = b.split(/(\s+)/);
  const m = x.length, n = y.length;
  const L: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = m - 1; i >= 0; i--) for (let j = n - 1; j >= 0; j--) L[i][j] = x[i] === y[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  const out: [string, "same" | "del" | "ins"][] = [];
  let i = 0, j = 0;
  while (i < m && j < n) {
    if (x[i] === y[j]) { out.push([x[i], "same"]); i++; j++; }
    else if (L[i + 1][j] >= L[i][j + 1]) out.push([x[i++], "del"]);
    else out.push([y[j++], "ins"]);
  }
  while (i < m) out.push([x[i++], "del"]);
  while (j < n) out.push([y[j++], "ins"]);
  return out;
}

/** Spelling fixes proposed by an AI: nothing changes until the user applies the ones they keep. */
export function SpellPanel({ docId, blocks, onChange }: { docId: string; blocks: Block[]; onChange: (blocks: Block[]) => void }) {
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [fixes, setFixes] = useState<SpellFix[] | null>(null);
  const [kept, setKept] = useState<Set<number>>(new Set());
  const [applied, setApplied] = useState(0);

  async function search() {
    setError("");
    setBusy(true);
    setApplied(0);
    try {
      const found = (await docs.spelling(docId)).fixes;
      setFixes(found);
      setKept(new Set(found.map((_, k) => k)));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function apply() {
    if (!fixes) return;
    let n = 0;
    const next = blocks.map((b, i) => {
      const k = fixes.findIndex((f) => f.block === i);
      if (k < 0 || !kept.has(k) || b.text !== fixes[k].before) return b; // edited since: left as it is
      n++;
      return { ...b, text: fixes[k].after };
    });
    onChange(next);
    setApplied(n);
    setFixes(null);
  }

  return (
    <div className="space-y-4">
      <p className="text-[15px] leading-relaxed text-ink/75">
        Paginya ne change jamais tes mots tout seul. Ici, une IA te <b>propose</b> des corrections d&apos;orthographe, d&apos;accords, d&apos;accents et de ponctuation, en français ou en anglais. Tu gardes celles que tu veux.
      </p>
      {!fixes && (
        <>
          <Toggle checked={consent} onChange={setConsent} label="J'accepte d'envoyer mon texte au service de correction (Google Gemini ou Groq). Il n'est pas gardé." />
          {error && <p className="flex gap-1.5 text-[14px] text-pin"><Icon name="triangle-alert" size={16} className="mt-0.5 shrink-0" />{error}</p>}
          <button type="button" disabled={!consent || busy} onClick={search}
            className="press inline-flex w-full items-center justify-center gap-2 rounded-md bg-board px-4 py-3.5 text-[16px] font-bold text-white hover:bg-board-2 disabled:opacity-50">
            {busy ? <><Icon name="loader-circle" size={18} className="animate-spin" /> Je relis ton texte…</> : <><Icon name="pen-line" size={18} /> Chercher les fautes</>}
          </button>
          {applied > 0 && <p className="flex items-center gap-2 text-[15px] font-semibold text-board"><Icon name="circle-check" size={18} /> {applied} correction{applied > 1 ? "s" : ""} appliquée{applied > 1 ? "s" : ""}. Les pages se mettent à jour.</p>}
        </>
      )}
      {fixes && fixes.length === 0 && (
        <div className="space-y-3">
          <p className="flex items-center gap-2 text-[15px] font-semibold text-board"><Icon name="circle-check" size={18} /> Aucune faute trouvée.</p>
          <button type="button" onClick={() => setFixes(null)} className="text-[14px] font-semibold text-ink/60 underline">Retour</button>
        </div>
      )}
      {fixes && fixes.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-[15px] font-bold">{fixes.length} correction{fixes.length > 1 ? "s" : ""} proposée{fixes.length > 1 ? "s" : ""}</p>
            <button type="button" className="text-[13px] font-semibold text-ink/60 underline"
              onClick={() => setKept(kept.size === fixes.length ? new Set() : new Set(fixes.map((_, k) => k)))}>
              {kept.size === fixes.length ? "Tout décocher" : "Tout cocher"}
            </button>
          </div>
          <ul className="divide-y divide-ink/10 border-y border-ink/10">
            {fixes.map((f, k) => (
              <li key={k}>
                <label className="flex cursor-pointer gap-3 py-3">
                  <input type="checkbox" className="mt-1 h-4 w-4 shrink-0 accent-[var(--color-board)]" checked={kept.has(k)}
                    onChange={() => { const s = new Set(kept); if (s.has(k)) s.delete(k); else s.add(k); setKept(s); }} />
                  <span className="text-[14px] leading-relaxed">
                    {diffWords(f.before, f.after).map(([t, kind], i) =>
                      kind === "same" ? <span key={i}>{t}</span>
                        : kind === "del" ? <del key={i} className="text-pin decoration-2">{t}</del>
                          : <ins key={i} className="rounded-sm bg-hi/50 px-0.5 font-semibold no-underline">{t}</ins>)}
                  </span>
                </label>
              </li>
            ))}
          </ul>
          <button type="button" disabled={!kept.size} onClick={apply}
            className="press inline-flex w-full items-center justify-center gap-2 rounded-md bg-board px-4 py-3.5 text-[16px] font-bold text-white hover:bg-board-2 disabled:opacity-50">
            <Icon name="check" size={18} stroke={2.6} /> Appliquer {kept.size} correction{kept.size > 1 ? "s" : ""}
          </button>
          <button type="button" onClick={() => setFixes(null)} className="w-full text-[14px] font-semibold text-ink/60 underline">Ne rien changer</button>
        </div>
      )}
    </div>
  );
}
