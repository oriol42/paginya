import { inks } from "../palettes";
import { fit, textBlock, wrap, type FontSpec } from "../text";
import type { CoverModel, RenderOptions } from "../types";
import { H, W, close, logo, open, people } from "./common";

/** "Moderne géométrique": corner triangles, big bold type, left aligned. */
export function moderne(m: CoverModel, o: RenderOptions): string {
  const c = inks(o);
  const out = open();
  const X = 62;
  const dark = "#0F172A";

  // Geometry (top-left + bottom-right)
  out.push(`<polygon points="0,0 250,0 0,300" fill="${c.primary}"/>`);
  out.push(`<polygon points="0,0 150,0 0,180" fill="${c.secondary}" opacity="0.9"/>`);
  out.push(`<circle cx="232" cy="118" r="16" fill="${c.accent}"/>`);
  out.push(`<polygon points="${W},${H} ${W - 230},${H} ${W},${H - 260}" fill="${c.primary}"/>`);
  out.push(`<polygon points="${W},${H} ${W - 120},${H} ${W},${H - 140}" fill="${c.secondary}" opacity="0.9"/>`);
  out.push(`<rect x="${W - 170}" y="${H - 70}" width="10" height="10" fill="${c.accent}" transform="rotate(45 ${W - 165} ${H - 65})"/>`);

  // Institution (top right)
  logo(out, m.logo, W - 62 - 58, 40, 58);
  if (m.logo2) logo(out, m.logo2, W - 62 - 58 - 66, 40, 58);
  const orgF: FontSpec = { family: "Poppins", weight: 600, size: 9, letterSpacing: 1 };
  const orgLines = wrap(m.org.toUpperCase(), orgF, 230);
  textBlock(out, orgLines.slice(0, 3), W - 62, m.logo ? 118 : 60, orgF, "#475569", { anchor: "end", lineHeight: 12 });

  // Type label + title
  let y = 340;
  const labelFit = fit(m.docLabel.toUpperCase(), { family: "Poppins", weight: 800, size: 38 }, W - 2 * X, 2, 24);
  y = textBlock(out, labelFit.lines, X, y, { family: "Poppins", weight: 800, size: labelFit.size }, c.primary, { lineHeight: labelFit.size * 1.1 });
  out.push(`<rect x="${X}" y="${y - 6}" width="70" height="6" rx="3" fill="${c.accent}"/>`);
  y += 36;
  const t = fit(m.title, { family: "Poppins", weight: 600, size: 22 }, W - 2 * X - 20, 4, 14);
  y = textBlock(out, t.lines, X, y, { family: "Poppins", weight: 600, size: t.size }, dark, { lineHeight: t.size * 1.3 });
  const mf: FontSpec = { family: "Poppins", size: 10.5 };
  y += 8;
  for (const line of [...m.mention, m.specialty].filter(Boolean)) {
    y = textBlock(out, wrap(line, mf, W - 2 * X - 40), X, y, mf, "#475569") + 2;
  }

  // People block
  y = Math.max(y + 34, 560);
  people(out, m, y, {
    x: X, width: W - 2 * X - 60, anchor: "start",
    label: { family: "Poppins", weight: 600, size: 8.5, letterSpacing: 0.8 },
    name: { family: "Poppins", weight: 600, size: 12 },
    info: { family: "Poppins", size: 9.5 },
    labelColor: c.primary, nameColor: dark, infoColor: "#64748B",
  });

  // Footer
  const foot: FontSpec = { family: "Poppins", weight: 600, size: 10 };
  textBlock(out, [m.footerLeft], X, H - 60, foot, dark);
  if (m.footerRight) textBlock(out, [m.footerRight], X, H - 45, { ...foot, weight: 400 }, "#64748B");
  return close(out);
}
