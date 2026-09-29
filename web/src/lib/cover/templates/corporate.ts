import { inks } from "../palettes";
import { fit, textBlock, wrap, type FontSpec } from "../text";
import type { CoverModel, RenderOptions } from "../types";
import { H, W, close, logo, open, people } from "./common";

/** "Corporate": large color block on the top 45 %, white title, clean footer. */
export function corporate(m: CoverModel, o: RenderOptions): string {
  const c = inks(o);
  const out = open();
  const X = 58;
  const blockH = 400;
  const dark = "#0F172A";

  out.push(`<rect width="${W}" height="${blockH}" fill="${c.primary}"/>`);
  out.push(`<polygon points="${W - 220},0 ${W},0 ${W},${blockH} ${W - 90},${blockH}" fill="${c.secondary}" opacity="0.35"/>`);
  out.push(`<rect x="0" y="${blockH}" width="${W}" height="8" fill="${c.accent}"/>`);

  if (m.logo) {
    out.push(`<rect x="${X - 6}" y="46" width="76" height="76" rx="10" fill="#ffffff"/>`);
    logo(out, m.logo, X, 52, 64);
  }
  if (m.logo2) {
    out.push(`<rect x="${W - X - 70}" y="46" width="76" height="76" rx="10" fill="#ffffff"/>`);
    logo(out, m.logo2, W - X - 64, 52, 64);
  }
  const orgF: FontSpec = { family: "Poppins", weight: 600, size: 10, letterSpacing: 1.2 };
  textBlock(out, wrap(m.org.toUpperCase(), orgF, 300).slice(0, 2), m.logo ? X + 90 : X, m.logo ? 80 : 70, orgF, "#FFFFFF", { lineHeight: 13 });

  let y = 220;
  const lf: FontSpec = { family: "Poppins", weight: 600, size: 11, letterSpacing: 2 };
  y = textBlock(out, [m.docLabel.toUpperCase()], X, y, lf, "#FFFFFF") + 18;
  const t = fit(m.title, { family: "Poppins", weight: 800, size: 30 }, W - 2 * X - 40, 4, 18);
  textBlock(out, t.lines, X, y, { family: "Poppins", weight: 800, size: t.size }, "#FFFFFF", { lineHeight: t.size * 1.18 });

  y = blockH + 60;
  const mf: FontSpec = { family: "Poppins", size: 11 };
  for (const line of [...m.mention, m.specialty].filter(Boolean)) {
    y = textBlock(out, wrap(line, mf, W - 2 * X), X, y, mf, "#334155") + 4;
  }
  y += 24;
  people(out, m, y, {
    x: X, width: W - 2 * X, anchor: "start",
    label: { family: "Poppins", weight: 600, size: 8.5, letterSpacing: 1 },
    name: { family: "Poppins", weight: 600, size: 12.5 },
    info: { family: "Poppins", size: 9.5 },
    labelColor: c.primary, nameColor: dark, infoColor: "#64748B",
  });

  out.push(`<line x1="${X}" y1="${H - 84}" x2="${W - X}" y2="${H - 84}" stroke="#E2E8F0" stroke-width="1"/>`);
  const foot: FontSpec = { family: "Poppins", weight: 600, size: 10 };
  textBlock(out, [m.footerLeft], X, H - 60, foot, dark);
  if (m.footerRight) textBlock(out, [m.footerRight], W - X, H - 60, { ...foot, weight: 400 }, "#64748B", { anchor: "end" });
  out.push(`<rect x="0" y="${H - 14}" width="${W}" height="14" fill="${c.primary}"/>`);
  return close(out);
}
