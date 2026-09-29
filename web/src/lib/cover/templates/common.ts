import { esc, textBlock, wrap, type FontSpec } from "../text";
import type { CoverModel, Person } from "../types";
import { PAGE_H, PAGE_W } from "../types";

export const W = PAGE_W;
export const H = PAGE_H;

export function open(): string[] {
  return [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">`,
    `<rect width="${W}" height="${H}" fill="#ffffff"/>`,
  ];
}

export function close(out: string[]): string {
  out.push("</svg>");
  return out.join("");
}

export function logo(out: string[], href: string | undefined, x: number, y: number, size: number): void {
  if (!href) return;
  out.push(
    `<image href="${esc(href)}" x="${x}" y="${y}" width="${size}" height="${size}" preserveAspectRatio="xMidYMid meet"/>`,
  );
}

/** One logo centred on cx, or two side by side (university + faculty). Returns the drawn width. */
export function logos(out: string[], m: CoverModel, cx: number, y: number, size: number, gap = 10): number {
  const list = [m.logo, m.logo2].filter(Boolean) as string[];
  if (!list.length) return 0;
  const s = list.length === 2 ? size * 0.78 : size;
  const total = list.length * s + (list.length - 1) * gap;
  list.forEach((href, i) => logo(out, href, cx - total / 2 + i * (s + gap), y + (size - s) / 2, s));
  return total;
}

/** Authors and supervisors laid out side by side (or stacked when alone). */
export function people(
  out: string[],
  m: CoverModel,
  y: number,
  opts: {
    x: number; width: number; anchor: "start" | "middle";
    label: FontSpec; name: FontSpec; info: FontSpec;
    labelColor: string; nameColor: string; infoColor: string;
  },
): number {
  const columns: { label: string; persons: Person[] }[] = [];
  if (m.authors.length) columns.push({ label: m.authorsLabel, persons: m.authors });
  for (const s of m.supervisors) columns.push({ label: `${s.role ?? "Encadreur"} :`, persons: [{ name: s.name, info: s.info }] });

  const perRow = columns.length > 1 ? 2 : 1;
  const colW = opts.width / perRow;
  let rowY = y;
  for (let i = 0; i < columns.length; i += perRow) {
    let rowBottom = rowY;
    const row = columns.slice(i, i + perRow);
    // A lone column on a centered layout is centered on the whole width.
    const w = opts.anchor === "middle" ? opts.width / row.length : colW;
    row.forEach((col, j) => {
      const cx = opts.anchor === "middle" ? opts.x + w * j + w / 2 : opts.x + colW * j;
      let cy = textBlock(out, [col.label], cx, rowY, opts.label, opts.labelColor, { anchor: opts.anchor });
      cy += 4;
      for (const p of col.persons) {
        cy = textBlock(out, wrap(p.name, opts.name, colW - 12), cx, cy, opts.name, opts.nameColor, { anchor: opts.anchor });
        if (p.info) cy = textBlock(out, wrap(p.info, opts.info, colW - 12), cx, cy, opts.info, opts.infoColor, { anchor: opts.anchor });
        cy += 4;
      }
      rowBottom = Math.max(rowBottom, cy);
    });
    rowY = rowBottom + 10;
  }
  return rowY;
}

/** Live preview only: fill empty fields with examples so the cover looks finished. */
export function withPlaceholders(m: CoverModel): CoverModel {
  const namedSupervisors = new Set(m.supervisors.map((s) => s.role));
  return {
    ...m,
    headerFr: m.headerMissing ? [...m.headerFr, ["NOM DE TON ÉTABLISSEMENT"]] : m.headerFr,
    headerEn: m.headerMissing ? [...m.headerEn, ["NAME OF YOUR INSTITUTION"]] : m.headerEn,
    org: m.org || (m.headerMissing ? "NOM DE TON ÉTABLISSEMENT" : m.org),
    title: m.title || "Titre de ton document",
    authors: m.authors.length ? m.authors : [{ name: "NOM Prénom", info: "Matricule : 00X000" }],
    mention: m.mention.length ? m.mention : m.sample.mention,
    supervisors: [...m.supervisors, ...m.sample.supervisors.filter((s) => !namedSupervisors.has(s.role))],
    footerLeft: m.footerLeft || "Année académique 2025-2026",
  };
}
