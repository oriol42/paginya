"use client";

import { useState } from "react";
import { API_URL } from "@/lib/api";
import { docs, type Block } from "@/lib/documents";
import { Icon } from "@/components/Icon";

type Props = {
  docId: string;
  blocks: Block[];
  /** Pictures made by the AI can be added (a document Paginya lays out itself). */
  canDraw?: boolean;
  onChange: (blocks: Block[]) => void;
};

type Target = { label: string; apply: (b: Block) => Block; active: (b: Block) => boolean };

const TARGETS: Target[] = [
  { label: "Titre 1", apply: (b) => ({ ...b, type: "heading", level: 1, special: undefined }), active: (b) => b.type === "heading" && b.level === 1 },
  { label: "Titre 2", apply: (b) => ({ ...b, type: "heading", level: 2, special: undefined, part: false }), active: (b) => b.type === "heading" && b.level === 2 },
  { label: "Titre 3", apply: (b) => ({ ...b, type: "heading", level: 3, special: undefined, part: false }), active: (b) => b.type === "heading" && b.level === 3 },
  { label: "Texte", apply: (b) => ({ ...b, type: "paragraph", level: undefined, role: undefined, special: undefined, part: false }), active: (b) => b.type === "paragraph" },
  { label: "• Puce", apply: (b) => ({ ...b, type: "list", ordered: false, level: 0 }), active: (b) => b.type === "list" && !b.ordered },
  { label: "1. Liste", apply: (b) => ({ ...b, type: "list", ordered: true, level: 0 }), active: (b) => b.type === "list" && !!b.ordered },
];

const EDITABLE = new Set(["heading", "paragraph", "list", "quote"]);

export function PlanPanel({ docId, blocks, canDraw, onChange }: Props) {
  const [onlyHeadings, setOnlyHeadings] = useState(blocks.length > 40);
  const [open, setOpen] = useState<number | null>(null);
  const visible = onlyHeadings ? blocks.filter((b) => b.type === "heading") : blocks;

  const update = (id: number, fn: (b: Block) => Block) => onChange(blocks.map((b) => (b.id === id ? fn(b) : b)));
  /** The new picture goes right after the element, with its caption (the server numbers the blocks again). */
  const insertAfter = (id: number, image: string, caption: string) => {
    const at = blocks.findIndex((b) => b.id === id);
    const top = Math.max(0, ...blocks.map((b) => b.id));
    const added: Block[] = [{ id: top + 1, type: "figure", image }, { id: top + 2, type: "caption", of: "figure", text: caption }];
    onChange([...blocks.slice(0, at + 1), ...added, ...blocks.slice(at + 1)]);
    setOpen(null);
  };

  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-2">
        <p className="text-sm text-ink/60">Touche un élément pour changer son type.</p>
        <button
          type="button"
          onClick={() => setOnlyHeadings((v) => !v)}
          className="shrink-0 rounded-full bg-paper px-3 py-1.5 text-xs font-bold text-ink/70 ring-1 ring-black/10"
        >
          {onlyHeadings ? "Tout afficher" : "Titres seulement"}
        </button>
      </div>
      <ul className="space-y-1.5">
        {visible.map((b) => {
          const isOpen = open === b.id;
          const indent = b.type === "heading" ? Math.max(0, (b.level ?? 1) - 1) * 14 : 0;
          return (
            <li key={b.id} style={{ marginLeft: indent }}>
              <button
                type="button"
                onClick={() => setOpen(isOpen ? null : b.id)}
                className={`flex w-full items-start gap-2.5 rounded-md px-3 py-2.5 text-left transition ${
                  isOpen ? "bg-paper ring-2 ring-brand-500" : "bg-paper ring-1 ring-black/5 hover:ring-black/10"
                } ${b.hidden ? "opacity-45" : ""}`}
              >
                <BlockBadge b={b} />
                <span className={`min-w-0 flex-1 ${b.hidden ? "line-through" : ""}`}>
                  <BlockText docId={docId} b={b} />
                </span>
              </button>
              {isOpen && (
                <div className="sheet-in mt-1.5 mb-2 rounded-md bg-brand-50/70 p-2.5 ring-1 ring-brand-100">
                  {EDITABLE.has(b.type) && (
                    <div className="flex flex-wrap gap-1.5">
                      {TARGETS.map((t) => (
                        <button
                          key={t.label}
                          type="button"
                          onClick={() => update(b.id, t.apply)}
                          className={`rounded-full px-3 py-1.5 text-[13px] font-semibold transition ${
                            t.active(b) ? "bg-ink text-white" : "bg-paper text-ink/80 ring-1 ring-black/10 hover:ring-brand-300"
                          }`}
                        >
                          {t.label}
                        </button>
                      ))}
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={() => update(b.id, (x) => ({ ...x, hidden: !x.hidden }))}
                    className="mt-2 text-[13px] font-semibold text-ink/70"
                  >
                    <span className="inline-flex items-center gap-1.5"><Icon name={b.hidden ? "undo-2" : "trash-2"} size={15} />{b.hidden ? "Remettre dans le document" : "Retirer du document"}</span>
                  </button>
                  {canDraw && <DrawImage docId={docId} onDone={(image, caption) => insertAfter(b.id, image, caption)} />}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** A picture made by the AI from the user's words, added after the element. Its caption says it was generated. */
function DrawImage({ docId, onDone }: { docId: string; onDone: (image: string, caption: string) => void }) {
  const [asking, setAsking] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (!asking) {
    return (
      <button type="button" onClick={() => setAsking(true)} className="mt-2 block text-[13px] font-semibold text-ink/70 hover:text-ink">
        <span className="inline-flex items-center gap-1.5"><Icon name="image" size={15} />Ajouter une image créée par l&apos;IA</span>
      </button>
    );
  }
  async function create() {
    if (prompt.trim().length < 3) {
      setError("Décris l'image en quelques mots.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const made = await docs.draw(docId, prompt);
      onDone(made.image, made.caption);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="mt-2.5 space-y-2 border-t border-brand-100 pt-2.5">
      <label className="block">
        <span className="text-[13px] font-semibold">Décris l&apos;image</span>
        <textarea name="description-image" autoComplete="off" rows={2} maxLength={400} value={prompt} disabled={busy} onChange={(e) => setPrompt(e.target.value)}
          placeholder="Par exemple : un entrepôt rempli de cartons, vu de haut…"
          className="mt-1 w-full rounded-md bg-white px-2.5 py-2 text-[14px] ring-1 ring-black/15 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500" />
      </label>
      <p className="text-[12px] text-ink/60">L&apos;image est ajoutée après cet élément, avec une légende qui indique qu&apos;elle a été créée par l&apos;IA.</p>
      {error && <p role="alert" className="text-[13px] font-semibold text-pin">{error}</p>}
      <div className="flex items-center gap-3">
        <button type="button" disabled={busy} onClick={create}
          className="press inline-flex min-h-11 items-center gap-2 rounded-md bg-ink px-4 text-[14px] font-bold text-white hover:bg-ink/85 disabled:opacity-50">
          {busy && <Icon name="loader-circle" size={16} className="animate-spin" />}
          {busy ? "Création de l'image…" : "Créer l'image"}
        </button>
        <button type="button" disabled={busy} onClick={() => { setAsking(false); setError(""); }} className="min-h-11 text-[13px] font-semibold text-ink/60 hover:text-ink">Annuler</button>
      </div>
    </div>
  );
}

function BlockBadge({ b }: { b: Block }) {
  const map: Record<string, [string, string]> = {
    heading: [b.special ? "S" : `T${b.level ?? 1}`, "bg-ink text-white"],
    paragraph: ["¶", "bg-ink/5 text-ink/60"],
    list: [b.ordered ? "1." : "•", "bg-sky-100 text-sky-700"],
    table: ["▦", "bg-amber-100 text-amber-700"],
    figure: ["Img", "bg-violet-100 text-violet-700"],
    caption: ["Lég", "bg-amber-50 text-amber-700"],
    source: ["Src", "bg-ink/5 text-ink/60"],
    quote: ["« »", "bg-ink/5 text-ink/70"],
    code: ["</>", "bg-slate-800 text-white"],
    title: ["Tt", "bg-brand-500 text-white"],
  };
  const [label, cls] = map[b.type] ?? ["?", "bg-ink/5"];
  return <span className={`mt-0.5 grid h-6 min-w-6 shrink-0 place-items-center rounded-lg px-1 text-[11px] font-bold ${cls}`}>{label}</span>;
}

function BlockText({ docId, b }: { docId: string; b: Block }) {
  if (b.type === "table") {
    const rows = b.rows ?? [];
    return <span className="text-sm text-ink/70">Tableau · {rows.length} lignes × {rows[0]?.length ?? 0} colonnes</span>;
  }
  if (b.type === "figure") {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={`${API_URL}/documents/${docId}/images/${b.image}`} alt="" className="max-h-16 rounded-lg" />;
  }
  if (b.role === "sigle") return <span className="line-clamp-1 text-sm text-ink/70"><b>{b.term}</b> : {b.definition}</span>;
  if (b.type === "title") return <span className={`line-clamp-2 text-ink ${b.sub ? "text-sm italic" : "text-[15px] font-bold"}`}>{b.text}</span>;
  if (b.type === "code") return <code className="line-clamp-2 whitespace-pre rounded bg-ink/5 px-1.5 text-xs text-ink/80">{b.text}</code>;
  if (b.type === "heading") return <span className={`line-clamp-2 font-semibold text-ink ${b.level === 1 ? "text-[15px]" : "text-sm"}`}>{b.text}</span>;
  if (b.type === "caption") return <span className="line-clamp-1 text-sm text-amber-800">{b.of === "table" ? "Tableau" : "Figure"} : {b.text}</span>;
  return <span className="line-clamp-1 text-sm text-ink/60">{b.text}</span>;
}
