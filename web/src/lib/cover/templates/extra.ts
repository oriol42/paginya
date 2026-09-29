import { inks } from "../palettes";
import { fit, textBlock, wrap, type FontSpec } from "../text";
import type { CoverModel, RenderOptions } from "../types";
import { H, W, close, logo, logos, open, people } from "./common";

/** Bilingual header columns (FR left, EN right) with star separators; returns the y below. */
function columns(out: string[], m: CoverModel, colW: number, xL: number, xR: number, y0: number, color: string, starColor: string, size = 9): number {
  const head: FontSpec = { family: "Tinos", weight: 700, size };
  const motto: FontSpec = { family: "Tinos", size, italic: true };
  const draw = (groups: string[][], x: number): number => {
    let y = y0;
    groups.forEach((g, gi) => {
      for (const line of g) {
        const f = /Paix|Peace/.test(line) ? motto : head;
        y = textBlock(out, wrap(line, f, colW), x, y, f, color, { anchor: "middle", lineHeight: size * 1.2 });
      }
      if (gi < groups.length - 1) y = textBlock(out, ["* * * * *"], x, y + 1, { family: "Tinos", size: 7 }, starColor, { anchor: "middle", lineHeight: size * 1.2 });
    });
    return y;
  };
  return Math.max(draw(m.headerFr, xL), draw(m.headerEn, xR));
}

function footer(out: string[], m: CoverModel, y: number, f: FontSpec, color: string, x = W / 2): void {
  const text = [m.footerLeft, m.footerRight].filter(Boolean).join("  ·  ");
  textBlock(out, [text], x, y, f, color, { anchor: x === W / 2 ? "middle" : "start" });
}

/** "Bandeau": the whole official header on a coloured band, title large and centred below. */
export function bandeau(m: CoverModel, o: RenderOptions): string {
  const c = inks(o);
  const out = open();
  const two = !!(m.logo && m.logo2);
  const colW = two ? 180 : 205;
  // measure the header first (drawn on a scratch buffer) to size the band
  const scratch: string[] = [];
  const headBottom = Math.max(columns(scratch, m, colW, 36 + colW / 2, W - 36 - colW / 2, 44, "#fff", "#fff"), 128);
  const bandH = headBottom + 22;
  out.push(`<rect width="${W}" height="${bandH}" fill="${c.primary}"/>`);
  out.push(`<rect y="${bandH}" width="${W}" height="6" fill="${c.accent}"/>`);
  columns(out, m, colW, 36 + colW / 2, W - 36 - colW / 2, 44, "#FFFFFF", c.accent);
  if (m.logo || m.logo2) {
    out.push(`<circle cx="${W / 2}" cy="${44 + 34}" r="${two ? 0 : 44}" fill="#ffffff"/>`);
    if (two) out.push(`<rect x="${W / 2 - 62}" y="40" width="124" height="76" rx="12" fill="#ffffff"/>`);
    logos(out, m, W / 2, 44, 68, 6);
  }

  let y = bandH + 92;
  const lf: FontSpec = { family: "Poppins", weight: 600, size: 12, letterSpacing: 3 };
  y = textBlock(out, [m.docLabel.toUpperCase()], W / 2, y, lf, c.primary, { anchor: "middle" }) + 26;
  const t = fit(m.title.toUpperCase(), { family: "Poppins", weight: 800, size: 24 }, W - 120, 5, 14);
  y = textBlock(out, t.lines, W / 2, y, { family: "Poppins", weight: 800, size: t.size }, "#0F172A", { anchor: "middle", lineHeight: t.size * 1.25 });
  out.push(`<rect x="${W / 2 - 40}" y="${y + 4}" width="80" height="4" rx="2" fill="${c.accent}"/>`);
  y += 36;
  const mf: FontSpec = { family: "Tinos", size: 12, italic: true };
  for (const line of [...m.mention, m.specialty].filter(Boolean)) y = textBlock(out, wrap(line, mf, W - 140), W / 2, y, mf, "#334155", { anchor: "middle" }) + 3;
  people(out, m, Math.max(y + 40, 560), {
    x: 50, width: W - 100, anchor: "middle",
    label: { family: "Poppins", weight: 600, size: 9, letterSpacing: 0.8 },
    name: { family: "Poppins", weight: 700, size: 12.5 },
    info: { family: "Poppins", size: 9.5 },
    labelColor: c.primary, nameColor: "#0F172A", infoColor: "#475569",
  });
  out.push(`<rect y="${H - 46}" width="${W}" height="46" fill="${c.primary}"/>`);
  footer(out, m, H - 19, { family: "Poppins", weight: 600, size: 10.5 }, "#FFFFFF");
  return close(out);
}

/** "Cadre d'honneur": double ornamental frame with corner diamonds, everything centred, serif title. */
export function cadre(m: CoverModel, o: RenderOptions): string {
  const c = inks(o);
  const out = open();
  out.push(`<rect x="22" y="22" width="${W - 44}" height="${H - 44}" fill="none" stroke="${c.primary}" stroke-width="2.5"/>`);
  out.push(`<rect x="31" y="31" width="${W - 62}" height="${H - 62}" fill="none" stroke="${c.accent}" stroke-width="0.9"/>`);
  for (const [x, y] of [[22, 22], [W - 22, 22], [22, H - 22], [W - 22, H - 22]]) {
    out.push(`<rect x="${x - 9}" y="${y - 9}" width="18" height="18" fill="${c.primary}" transform="rotate(45 ${x} ${y})"/>`);
    out.push(`<rect x="${x - 4}" y="${y - 4}" width="8" height="8" fill="${c.accent}" transform="rotate(45 ${x} ${y})"/>`);
  }
  // Header: logos on each side of the French lines (English under a thin rule on academic covers)
  logo(out, m.logo, 52, 52, 62);
  if (m.logo2) logo(out, m.logo2, W - 52 - 62, 52, 62);
  const head: FontSpec = { family: "Tinos", weight: 700, size: 10 };
  let y = 60;
  for (const line of m.headerFr.flat()) {
    const f = /Paix/.test(line) ? { ...head, weight: 400, italic: true } : head;
    y = textBlock(out, wrap(line, f, W - 260), W / 2, y, f, "#111111", { anchor: "middle", lineHeight: 12.5 });
  }
  const en = m.headerEn.flat().filter((l) => !/Peace|REPUBLIC|MINISTRY/.test(l));
  if (en.length) {
    y = textBlock(out, en.slice(-2), W / 2, y + 2, { family: "Tinos", size: 9, italic: true }, "#444444", { anchor: "middle", lineHeight: 11 });
  }
  y = Math.max(y, 130) + 14;
  out.push(`<line x1="${W / 2 - 110}" y1="${y}" x2="${W / 2 + 110}" y2="${y}" stroke="${c.primary}" stroke-width="1"/>`);

  y += 70;
  const lf: FontSpec = { family: "Playfair Display", weight: 700, size: 22, letterSpacing: 2 };
  y = textBlock(out, [m.docLabel.toUpperCase()], W / 2, y, lf, c.primary, { anchor: "middle" }) + 30;
  const t = fit(m.title, { family: "Playfair Display", weight: 700, size: 25 }, W - 150, 5, 15);
  textBlock(out, ["“"], W / 2, y + 6, { family: "Playfair Display", weight: 700, size: 44 }, c.accent, { anchor: "middle" });
  y = textBlock(out, t.lines, W / 2, y + 30, { family: "Playfair Display", weight: 700, size: t.size }, "#111111", { anchor: "middle", lineHeight: t.size * 1.28 }) + 14;
  const mf: FontSpec = { family: "Playfair Display", size: 12, italic: true };
  for (const line of [...m.mention, m.specialty].filter(Boolean)) y = textBlock(out, wrap(line, mf, W - 150), W / 2, y, mf, "#374151", { anchor: "middle" }) + 3;
  people(out, m, Math.max(y + 36, 580), {
    x: 50, width: W - 100, anchor: "middle",
    label: { family: "Tinos", size: 11, italic: true },
    name: { family: "Tinos", weight: 700, size: 13.5 },
    info: { family: "Tinos", size: 10.5 },
    labelColor: "#111111", nameColor: "#111111", infoColor: "#374151",
  });
  footer(out, m, H - 56, { family: "Tinos", weight: 700, size: 11.5 }, c.primary);
  return close(out);
}

/** "Latéral": a tall coloured band on the left carrying the document type, content on the right. */
export function lateral(m: CoverModel, o: RenderOptions): string {
  const c = inks(o);
  const out = open();
  const band = 150;
  out.push(`<rect width="${band}" height="${H}" fill="${c.primary}"/>`);
  out.push(`<rect x="${band}" width="7" height="${H}" fill="${c.accent}"/>`);
  out.push(`<circle cx="${band / 2}" cy="${H - 140}" r="54" fill="${c.secondary}" opacity="0.5"/>`);
  const label = fit(m.docLabel.toUpperCase(), { family: "Poppins", weight: 800, size: 40 }, H - 260, 1, 20);
  out.push(`<g transform="translate(${band / 2 + label.size * 0.35} ${H - 90}) rotate(-90)">`);
  textBlock(out, label.lines, 0, 0, { family: "Poppins", weight: 800, size: label.size, letterSpacing: 2 }, "#FFFFFF");
  out.push("</g>");
  textBlock(out, [m.footerLeft.replace(/^Année académique\s*/, "")], band / 2, 70, { family: "Poppins", weight: 700, size: 12 }, "#FFFFFF", { anchor: "middle" });

  const X = band + 42;
  const R = W - 44;
  let lx = X;
  if (m.logo) { logo(out, m.logo, lx, 44, 58); lx += 66; }
  if (m.logo2) { logo(out, m.logo2, lx, 44, 58); lx += 66; }
  const orgF: FontSpec = { family: "Poppins", weight: 600, size: 8.5, letterSpacing: 0.6 };
  let y = m.logo || m.logo2 ? 124 : 60;
  const org = m.headerFr.flat().filter((l) => !/RÉPUBLIQUE|Paix|MINISTÈRE/i.test(l));
  y = textBlock(out, org.flatMap((l) => wrap(l, orgF, R - X)).slice(0, 4), X, y, orgF, "#475569", { lineHeight: 11.5 });

  y = Math.max(y + 110, 300);
  const t = fit(m.title, { family: "Poppins", weight: 800, size: 28 }, R - X, 6, 15);
  y = textBlock(out, t.lines, X, y, { family: "Poppins", weight: 800, size: t.size }, "#0F172A", { lineHeight: t.size * 1.2 });
  out.push(`<rect x="${X}" y="${y + 2}" width="56" height="5" fill="${c.accent}"/>`);
  y += 30;
  const mf: FontSpec = { family: "Poppins", size: 10.5 };
  for (const line of [...m.mention, m.specialty].filter(Boolean)) y = textBlock(out, wrap(line, mf, R - X), X, y, mf, "#475569") + 3;
  people(out, m, Math.max(y + 40, 580), {
    x: X, width: R - X, anchor: "start",
    label: { family: "Poppins", weight: 600, size: 8.5, letterSpacing: 0.8 },
    name: { family: "Poppins", weight: 700, size: 12 },
    info: { family: "Poppins", size: 9.5 },
    labelColor: c.primary, nameColor: "#0F172A", infoColor: "#64748B",
  });
  if (m.footerRight) textBlock(out, [m.footerRight], X, H - 50, { family: "Poppins", size: 10 }, "#64748B");
  return close(out);
}

/** "Vagues": soft waves top and bottom in the palette, centred modern layout. */
export function vague(m: CoverModel, o: RenderOptions): string {
  const c = inks(o);
  const out = open();
  out.push(`<path d="M0 0H${W}V120C${W * 0.75} 170 ${W * 0.45} 70 0 150Z" fill="${c.primary}"/>`);
  out.push(`<path d="M0 150C${W * 0.45} 70 ${W * 0.75} 170 ${W} 120V136C${W * 0.72} 190 ${W * 0.42} 92 0 170Z" fill="${c.accent}" opacity="0.9"/>`);
  out.push(`<path d="M0 ${H}H${W}V${H - 110}C${W * 0.7} ${H - 170} ${W * 0.35} ${H - 60} 0 ${H - 130}Z" fill="${c.primary}"/>`);
  out.push(`<path d="M0 ${H - 130}C${W * 0.35} ${H - 60} ${W * 0.7} ${H - 170} ${W} ${H - 110}V${H - 124}C${W * 0.68} ${H - 186} ${W * 0.33} ${H - 78} 0 ${H - 148}Z" fill="${c.accent}" opacity="0.6"/>`);

  const orgF: FontSpec = { family: "Poppins", weight: 600, size: 9, letterSpacing: 0.8 };
  const org = m.headerFr.flat().filter((l) => !/RÉPUBLIQUE|Paix|MINISTÈRE/i.test(l));
  textBlock(out, org.flatMap((l) => wrap(l, orgF, W - 120)).slice(0, 3), W / 2, 40, orgF, "#FFFFFF", { anchor: "middle", lineHeight: 12 });
  if (m.logo || m.logo2) {
    const w = logos(out, m, W / 2, 180, 74, 14);
    out.push(`<rect x="${W / 2 - w / 2 - 12}" y="172" width="${w + 24}" height="90" rx="16" fill="#ffffff" opacity="0"/>`);
  }
  let y = 330;
  const lf: FontSpec = { family: "Poppins", weight: 700, size: 13, letterSpacing: 4 };
  y = textBlock(out, [m.docLabel.toUpperCase()], W / 2, y, lf, c.primary, { anchor: "middle" }) + 24;
  const t = fit(m.title, { family: "Poppins", weight: 800, size: 27 }, W - 120, 5, 15);
  y = textBlock(out, t.lines, W / 2, y, { family: "Poppins", weight: 800, size: t.size }, "#0F172A", { anchor: "middle", lineHeight: t.size * 1.22 }) + 12;
  const mf: FontSpec = { family: "Poppins", size: 10.5 };
  for (const line of [...m.mention, m.specialty].filter(Boolean)) y = textBlock(out, wrap(line, mf, W - 140), W / 2, y, mf, "#475569", { anchor: "middle" }) + 3;
  people(out, m, Math.max(y + 34, 540), {
    x: 60, width: W - 120, anchor: "middle",
    label: { family: "Poppins", weight: 600, size: 8.5, letterSpacing: 0.8 },
    name: { family: "Poppins", weight: 700, size: 12.5 },
    info: { family: "Poppins", size: 9.5 },
    labelColor: c.primary, nameColor: "#0F172A", infoColor: "#64748B",
  });
  footer(out, m, H - 40, { family: "Poppins", weight: 700, size: 11 }, "#FFFFFF");
  return close(out);
}
