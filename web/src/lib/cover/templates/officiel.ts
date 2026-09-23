import { inks } from "../palettes";
import { fit, textBlock, wrap, type FontSpec } from "../text";
import type { CoverModel, RenderOptions } from "../types";
import { H, W, close, logo, open, people } from "./common";

/** A block is drawn at y=0 into its own buffer; returns its height. */
type Block = { out: string[]; height: number };

function block(draw: (out: string[]) => number): Block {
  const out: string[] = [];
  return { out, height: draw(out) };
}

/**
 * "Officiel Cameroun": bilingual FR | logo | EN header with star separators,
 * framed title, centered academic mentions (as on UY1/UY2/ENS covers).
 * Middle blocks are spread evenly between the header and the footer.
 */
export function officiel(m: CoverModel, o: RenderOptions): string {
  const c = inks(o);
  const out = open();
  const ink = "#111111";
  const M = 40;

  if (o.frame) {
    out.push(`<rect x="18" y="18" width="${W - 36}" height="${H - 36}" fill="none" stroke="${c.primary}" stroke-width="3"/>`);
    out.push(`<rect x="24" y="24" width="${W - 48}" height="${H - 48}" fill="none" stroke="${c.primary}" stroke-width="0.8"/>`);
  }

  // --- Bilingual header -------------------------------------------------
  const colW = 212;
  const head: FontSpec = { family: "Tinos", weight: 700, size: 9.5 };
  const motto: FontSpec = { family: "Tinos", weight: 400, size: 9.5, italic: true };
  const star: FontSpec = { family: "Tinos", size: 8 };
  const drawColumn = (groups: string[][], x: number): number => {
    let y = 54;
    groups.forEach((g, gi) => {
      for (const line of g) {
        const f = /Paix|Peace/.test(line) ? motto : head;
        y = textBlock(out, wrap(line, f, colW), x, y, f, ink, { anchor: "middle", lineHeight: 11.5 });
      }
      if (gi < groups.length - 1) {
        y = textBlock(out, ["**********"], x, y + 1, star, c.primary, { anchor: "middle", lineHeight: 11.5 });
      }
    });
    return y;
  };
  const yL = drawColumn(m.headerFr, M + colW / 2);
  const yR = drawColumn(m.headerEn, W - M - colW / 2);
  logo(out, m.logo, W / 2 - 36, 46, 72);
  const top = Math.max(yL, yR, 130) + 10;

  // --- Footer -----------------------------------------------------------
  const foot: FontSpec = { family: "Tinos", weight: 700, size: 11.5 };
  const fy = H - 58;
  const bottom = fy - 30;
  out.push(`<line x1="${M + 10}" y1="${fy - 18}" x2="${W - M - 10}" y2="${fy - 18}" stroke="${c.primary}" stroke-width="0.8"/>`);
  if (m.footerRight) {
    textBlock(out, [m.footerLeft], M + 16, fy, foot, ink);
    textBlock(out, [m.footerRight], W - M - 16, fy, foot, ink, { anchor: "end" });
  } else {
    textBlock(out, [m.footerLeft], W / 2, fy, foot, ink, { anchor: "middle" });
  }

  // --- Middle blocks ----------------------------------------------------
  const blocks: Block[] = [];

  blocks.push(block((b) => {
    const label: FontSpec = { family: "Tinos", weight: 700, size: 21, letterSpacing: 1.5 };
    let y = textBlock(b, [m.docLabel], W / 2, 21, label, c.primary, { anchor: "middle" }) + 12;
    const boxW = W - 2 * M - 40;
    const titleFit = fit(m.title.toUpperCase(), { family: "Tinos", weight: 700, size: 19 }, boxW - 40, 4, 12);
    const lh = titleFit.size * 1.3;
    const boxH = titleFit.lines.length * lh + 32;
    const boxX = (W - boxW) / 2;
    b.push(`<rect x="${boxX}" y="${y}" width="${boxW}" height="${boxH}" rx="6" fill="${o.mono ? "#ffffff" : c.light}" stroke="${c.primary}" stroke-width="1.6"/>`);
    b.push(`<rect x="${boxX + 4}" y="${y + 4}" width="${boxW - 8}" height="${boxH - 8}" rx="4" fill="none" stroke="${c.primary}" stroke-width="0.6"/>`);
    textBlock(b, titleFit.lines, W / 2, y + 16 + titleFit.size, { family: "Tinos", weight: 700, size: titleFit.size }, ink, { anchor: "middle", lineHeight: lh });
    y += boxH;
    return y;
  }));

  if (m.mention.length || m.specialty) {
    blocks.push(block((b) => {
      const mentionF: FontSpec = { family: "Tinos", size: 12.5, italic: true };
      let y = 12;
      for (const line of m.mention) {
        y = textBlock(b, wrap(line, mentionF, W - 2 * M - 50), W / 2, y, mentionF, ink, { anchor: "middle" }) + 4;
      }
      if (m.specialty) {
        const f: FontSpec = { family: "Tinos", weight: 700, size: 12.5 };
        y = textBlock(b, wrap(m.specialty, f, W - 2 * M - 50), W / 2, y + 4, f, ink, { anchor: "middle" });
      }
      return y;
    }));
  }

  blocks.push(block((b) =>
    people(b, m, 12, {
      x: M, width: W - 2 * M, anchor: "middle",
      label: { family: "Tinos", size: 11.5, italic: true },
      name: { family: "Tinos", weight: 700, size: 13.5 },
      info: { family: "Tinos", size: 11 },
      labelColor: ink, nameColor: ink, infoColor: "#333333",
    }),
  ));

  if (m.jury.length) {
    blocks.push(block((b) => {
      let y = textBlock(b, ["Membres du jury"], W / 2, 12, { family: "Tinos", weight: 700, size: 11.5 }, ink, { anchor: "middle" });
      y = textBlock(b, m.jury.slice(0, 5), W / 2, y + 2, { family: "Tinos", size: 11 }, ink, { anchor: "middle" });
      return y;
    }));
  }

  // Even spacing, but never cramped nor absurdly loose.
  const used = blocks.reduce((sum, b) => sum + b.height, 0);
  const gap = Math.max(14, Math.min(70, (bottom - top - used) / (blocks.length + 1)));
  let y = top + gap;
  for (const b of blocks) {
    out.push(`<g transform="translate(0 ${y.toFixed(1)})">`, ...b.out, "</g>");
    y += b.height + gap;
  }
  return close(out);
}
