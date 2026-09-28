"use client";

import { useState } from "react";
import { API_URL } from "@/lib/api";
import type { Block } from "@/lib/documents";
import { Icon } from "@/components/Icon";

type Props = {
  docId: string;
  blocks: Block[];
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

export function PlanPanel({ docId, blocks, onChange }: Props) {
  const [onlyHeadings, setOnlyHeadings] = useState(blocks.length > 40);
  const [open, setOpen] = useState<number | null>(null);
  const visible = onlyHeadings ? blocks.filter((b) => b.type === "heading") : blocks;

  const update = (id: number, fn: (b: Block) => Block) => onChange(blocks.map((b) => (b.id === id ? fn(b) : b)));

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
                </div>
              )}
            </li>
          );
        })}
      </ul>
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
