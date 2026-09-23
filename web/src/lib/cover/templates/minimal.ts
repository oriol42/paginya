import { inks } from "../palettes";
import { fit, textBlock, wrap, type FontSpec } from "../text";
import type { CoverModel, RenderOptions } from "../types";
import { H, W, close, logo, open, people } from "./common";

/** "Minimal / Élégant": serif title, hairlines, generous white space. */
export function minimal(m: CoverModel, o: RenderOptions): string {
  const c = inks(o);
  const out = open();
  const X = 72;
  const ink = "#1A1A1A";

  logo(out, m.logo, X, 56, 44);
  const orgF: FontSpec = { family: "Inter", weight: 600, size: 8.5, letterSpacing: 1.6 };
  textBlock(out, wrap(m.org.toUpperCase(), orgF, W - 2 * X - 60).slice(0, 2), m.logo ? X + 58 : X, 74, orgF, "#6B7280", { lineHeight: 12 });

  let y = 250;
  out.push(`<line x1="${X}" y1="${y}" x2="${X + 60}" y2="${y}" stroke="${c.primary}" stroke-width="2"/>`);
  y += 34;
  const lf: FontSpec = { family: "Inter", weight: 600, size: 10, letterSpacing: 3 };
  y = textBlock(out, [m.docLabel.toUpperCase()], X, y, lf, c.primary) + 22;
  const t = fit(m.title, { family: "Playfair Display", weight: 700, size: 34 }, W - 2 * X, 5, 20);
  y = textBlock(out, t.lines, X, y + t.size * 0.4, { family: "Playfair Display", weight: 700, size: t.size }, ink, { lineHeight: t.size * 1.2 });
  y += 10;
  const mf: FontSpec = { family: "Playfair Display", size: 12.5, italic: true };
  for (const line of [...m.mention, m.specialty].filter(Boolean)) {
    y = textBlock(out, wrap(line, mf, W - 2 * X), X, y, mf, "#4B5563") + 4;
  }
  y += 16;
  out.push(`<line x1="${X}" y1="${y}" x2="${W - X}" y2="${y}" stroke="#D1D5DB" stroke-width="0.8"/>`);

  people(out, m, Math.max(y + 40, 600), {
    x: X, width: W - 2 * X, anchor: "start",
    label: { family: "Inter", weight: 600, size: 8, letterSpacing: 1.2 },
    name: { family: "Playfair Display", weight: 700, size: 13 },
    info: { family: "Inter", size: 9 },
    labelColor: "#6B7280", nameColor: ink, infoColor: "#6B7280",
  });

  const foot: FontSpec = { family: "Inter", size: 9.5, letterSpacing: 0.5 };
  textBlock(out, [m.footerLeft], X, H - 58, foot, ink);
  if (m.footerRight) textBlock(out, [m.footerRight], W - X, H - 58, foot, "#6B7280", { anchor: "end" });
  out.push(`<rect x="${W - X - 8}" y="56" width="8" height="8" fill="${c.primary}"/>`);
  return close(out);
}
