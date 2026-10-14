import { inks } from "../palettes";
import { fit, textBlock, wrap, type FontSpec } from "../text";
import type { CoverModel, RenderOptions } from "../types";
import { H, W, close, logos, open, people } from "./common";
import { columns, footer } from "./extra";

const INK = "#111827";
const OFFICIAL = /RÉPUBLIQUE|Paix|MINISTÈRE|REPUBLIC|Peace|MINISTRY/i;

/** Mentions and speciality, centred; returns the y below. */
function mentions(out: string[], m: CoverModel, y: number, f: FontSpec, color: string, width: number, x = W / 2, anchor: "start" | "middle" = "middle"): number {
  for (const line of [...m.mention, m.specialty].filter(Boolean)) y = textBlock(out, wrap(line, f, width), x, y, f, color, { anchor }) + 3;
  return y;
}

/**
 * "Classique": what a careful typist would do. Bilingual header, a thin double rule, the title between two
 * rules, everything centred, the palette used only for the rules and the label. Prints well in black and white.
 */
export function classique(m: CoverModel, o: RenderOptions): string {
  const c = inks(o);
  const out = open();
  const colW = 205;
  let y = Math.max(columns(out, m, colW, 40 + colW / 2, W - 40 - colW / 2, 50, INK, c.primary, 9.5), 126);
  logos(out, m, W / 2, 46, 70, 6);
  y += 14;
  out.push(`<line x1="60" y1="${y}" x2="${W - 60}" y2="${y}" stroke="${c.primary}" stroke-width="1.6"/>`);
  out.push(`<line x1="60" y1="${y + 4}" x2="${W - 60}" y2="${y + 4}" stroke="${c.primary}" stroke-width="0.5"/>`);

  y += 84;
  y = textBlock(out, [m.docLabel.toUpperCase()], W / 2, y, { family: "Tinos", weight: 700, size: 20, letterSpacing: 3 }, c.primary, { anchor: "middle" }) + 22;
  const t = fit(m.title.toUpperCase(), { family: "Tinos", weight: 700, size: 21 }, W - 150, 5, 13);
  const lh = t.size * 1.32;
  out.push(`<line x1="${W / 2 - 150}" y1="${y}" x2="${W / 2 + 150}" y2="${y}" stroke="${INK}" stroke-width="0.8"/>`);
  y = textBlock(out, t.lines, W / 2, y + 12 + t.size, { family: "Tinos", weight: 700, size: t.size }, INK, { anchor: "middle", lineHeight: lh });
  out.push(`<line x1="${W / 2 - 150}" y1="${y - lh + 14}" x2="${W / 2 + 150}" y2="${y - lh + 14}" stroke="${INK}" stroke-width="0.8"/>`);
  y += 14 - lh + t.size;
  y = mentions(out, m, y + 30, { family: "Tinos", size: 12.5, italic: true }, "#1F2937", W - 150);
  y = people(out, m, Math.max(y + 38, 560), {
    x: 50, width: W - 100, anchor: "middle",
    label: { family: "Tinos", size: 11.5, italic: true },
    name: { family: "Tinos", weight: 700, size: 13.5 },
    info: { family: "Tinos", size: 11 },
    labelColor: INK, nameColor: INK, infoColor: "#374151",
  });
  if (m.jury.length) {
    y = textBlock(out, [m.juryLabel], W / 2, y + 8, { family: "Tinos", weight: 700, size: 11.5 }, INK, { anchor: "middle" });
    textBlock(out, m.jury.slice(0, 4), W / 2, y + 2, { family: "Tinos", size: 11 }, INK, { anchor: "middle" });
  }
  out.push(`<line x1="60" y1="${H - 78}" x2="${W - 60}" y2="${H - 78}" stroke="${c.primary}" stroke-width="0.5"/>`);
  out.push(`<line x1="60" y1="${H - 74}" x2="${W - 60}" y2="${H - 74}" stroke="${c.primary}" stroke-width="1.6"/>`);
  footer(out, m, H - 52, { family: "Tinos", weight: 700, size: 12 }, INK);
  return close(out);
}

/** "Bloc couleur": the title in white on a large coloured block, the school above, the names below. */
export function bloc(m: CoverModel, o: RenderOptions): string {
  const c = inks(o);
  const out = open();
  const orgF: FontSpec = { family: "Poppins", weight: 600, size: 9.5, letterSpacing: 0.6 };
  const org = m.headerFr.flat().filter((l) => !OFFICIAL.test(l));
  const hasLogo = !!(m.logo || m.logo2);
  if (hasLogo) logos(out, m, W / 2, 40, 70, 10);
  let y = textBlock(out, org.flatMap((l) => wrap(l, orgF, W - 120)).slice(0, 4), W / 2, hasLogo ? 134 : 64, orgF, "#334155", { anchor: "middle", lineHeight: 13 });

  const top = Math.max(y + 22, 210);
  const t = fit(m.title, { family: "Poppins", weight: 800, size: 28 }, W - 150, 6, 15);
  const blockH = Math.max(250, t.lines.length * t.size * 1.22 + 130);
  out.push(`<rect x="34" y="${top}" width="${W - 68}" height="${blockH}" rx="10" fill="${c.primary}"/>`);
  out.push(`<rect x="34" y="${top + blockH - 10}" width="${W - 68}" height="10" fill="${c.accent}"/>`);
  out.push(`<circle cx="${W - 80}" cy="${top + 46}" r="70" fill="#ffffff" opacity="0.07"/>`);
  out.push(`<circle cx="74" cy="${top + blockH - 30}" r="46" fill="#ffffff" opacity="0.06"/>`);
  y = textBlock(out, [m.docLabel.toUpperCase()], W / 2, top + 50, { family: "Poppins", weight: 600, size: 12, letterSpacing: 4 }, "#FFFFFF", { anchor: "middle" });
  out.push(`<rect x="${W / 2 - 26}" y="${y - 4}" width="52" height="3" rx="1.5" fill="${c.accent}"/>`);
  const ty = top + 50 + (blockH - 50 - t.lines.length * t.size * 1.22) / 2 + t.size * 0.6;
  textBlock(out, t.lines, W / 2, ty, { family: "Poppins", weight: 800, size: t.size }, "#FFFFFF", { anchor: "middle", lineHeight: t.size * 1.22 });

  y = mentions(out, m, top + blockH + 36, { family: "Poppins", size: 10.5 }, "#475569", W - 150);
  people(out, m, Math.max(y + 30, top + blockH + 78), {
    x: 54, width: W - 108, anchor: "middle",
    label: { family: "Poppins", weight: 600, size: 8.5, letterSpacing: 0.8 },
    name: { family: "Poppins", weight: 700, size: 12.5 },
    info: { family: "Poppins", size: 9.5 },
    labelColor: c.primary, nameColor: "#0F172A", infoColor: "#64748B",
  });
  footer(out, m, H - 44, { family: "Poppins", weight: 700, size: 11 }, c.primary);
  return close(out);
}

/** "Rubans": two coloured corners cut on the diagonal, a lively cover for exposés and projects. */
export function ruban(m: CoverModel, o: RenderOptions): string {
  const c = inks(o);
  const out = open();
  out.push(`<path d="M0 0H250L0 250Z" fill="${c.primary}"/>`);
  out.push(`<path d="M250 0H290L0 290V250Z" fill="${c.accent}"/>`);
  out.push(`<path d="M${W} ${H}H${W - 250}L${W} ${H - 250}Z" fill="${c.primary}"/>`);
  out.push(`<path d="M${W - 250} ${H}H${W - 290}L${W} ${H - 290}V${H - 250}Z" fill="${c.accent}"/>`);

  const X = W - 54;
  const orgF: FontSpec = { family: "Poppins", weight: 600, size: 9, letterSpacing: 0.6 };
  const org = m.headerFr.flat().filter((l) => !OFFICIAL.test(l));
  let y = 62;
  if (m.logo || m.logo2) {
    logos(out, m, W - 54 - 60, 44, 64, 8);
    y = 128;
  }
  y = textBlock(out, org.flatMap((l) => wrap(l, orgF, 300)).slice(0, 4), X, y, orgF, "#334155", { anchor: "end", lineHeight: 12.5 });

  y = Math.max(y + 110, 320);
  const L = 70;
  y = textBlock(out, [m.docLabel.toUpperCase()], L, y, { family: "Poppins", weight: 600, size: 12.5, letterSpacing: 3.5 }, c.primary) + 14;
  const t = fit(m.title, { family: "Poppins", weight: 800, size: 30 }, W - 2 * L, 6, 15);
  y = textBlock(out, t.lines, L, y + t.size * 0.6, { family: "Poppins", weight: 800, size: t.size }, "#0F172A", { lineHeight: t.size * 1.2 });
  out.push(`<rect x="${L}" y="${y - 6}" width="70" height="5" rx="2.5" fill="${c.accent}"/>`);
  y = mentions(out, m, y + 26, { family: "Poppins", size: 10.5 }, "#475569", W - 2 * L, L, "start");
  people(out, m, Math.max(y + 34, 560), {
    x: L, width: W - 2 * L - 60, anchor: "start",
    label: { family: "Poppins", weight: 600, size: 8.5, letterSpacing: 0.8 },
    name: { family: "Poppins", weight: 700, size: 12.5 },
    info: { family: "Poppins", size: 9.5 },
    labelColor: c.primary, nameColor: "#0F172A", infoColor: "#64748B",
  });
  footer(out, m, H - 40, { family: "Poppins", weight: 700, size: 10.5 }, "#334155", L);
  return close(out);
}

/** "Deux tons": the official header on a pale band, the names on a dark foot, the title in between. */
export function duo(m: CoverModel, o: RenderOptions): string {
  const c = inks(o);
  const out = open();
  const two = !!(m.logo && m.logo2);
  const colW = two ? 180 : 205;
  const scratch: string[] = [];
  const headBottom = Math.max(columns(scratch, m, colW, 36 + colW / 2, W - 36 - colW / 2, 46, INK, c.primary), 126);
  out.push(`<rect width="${W}" height="${headBottom + 20}" fill="${o.mono ? "#F3F4F6" : c.light}"/>`);
  out.push(`<rect y="${headBottom + 20}" width="${W}" height="3" fill="${c.primary}"/>`);
  columns(out, m, colW, 36 + colW / 2, W - 36 - colW / 2, 46, INK, c.primary);
  logos(out, m, W / 2, 44, 68, 6);

  const footH = 210;
  const fy = H - footH;
  out.push(`<rect y="${fy}" width="${W}" height="${footH}" fill="${c.secondary}"/>`);
  out.push(`<rect y="${fy}" width="${W}" height="5" fill="${c.accent}"/>`);

  const mid = (headBottom + 23 + fy) / 2;
  const t = fit(m.title, { family: "Playfair Display", weight: 700, size: 27 }, W - 130, 5, 15);
  const blockH = 40 + t.lines.length * t.size * 1.28 + (m.mention.length + (m.specialty ? 1 : 0)) * 18;
  let y = mid - blockH / 2;
  y = textBlock(out, [m.docLabel.toUpperCase()], W / 2, y, { family: "Poppins", weight: 600, size: 12, letterSpacing: 4 }, c.primary, { anchor: "middle" }) + 26;
  y = textBlock(out, t.lines, W / 2, y + t.size * 0.4, { family: "Playfair Display", weight: 700, size: t.size }, INK, { anchor: "middle", lineHeight: t.size * 1.28 });
  out.push(`<rect x="${W / 2 - 34}" y="${y - 4}" width="68" height="3" fill="${c.accent}"/>`);
  mentions(out, m, y + 24, { family: "Playfair Display", size: 11.5, italic: true }, "#374151", W - 150);

  people(out, m, fy + 44, {
    x: 50, width: W - 100, anchor: "middle",
    label: { family: "Poppins", weight: 600, size: 8.5, letterSpacing: 0.8 },
    name: { family: "Poppins", weight: 700, size: 12.5 },
    info: { family: "Poppins", size: 9.5 },
    labelColor: c.accent, nameColor: "#FFFFFF", infoColor: "#E5E7EB",
  });
  footer(out, m, H - 26, { family: "Poppins", weight: 600, size: 10.5 }, "#FFFFFF");
  return close(out);
}
