/**
 * Text helpers for SVG covers. SVG has no automatic line wrapping, so we
 * measure words with a canvas (same font files as the server renderer) and
 * emit explicit <text> lines.
 */

export type FontSpec = {
  family: string;
  weight?: number;
  size: number;
  italic?: boolean;
  letterSpacing?: number;
};

let ctx: CanvasRenderingContext2D | null = null;

// Weights each family really ships (same files in web/public/fonts and api/fonts).
const WEIGHTS: Record<string, number[]> = { Tinos: [400, 700], Poppins: [400, 600, 800], "Playfair Display": [400, 700], Inter: [400, 600] };
let override: string | null = null;

/** Draw every text with this family (null = the fonts each design was drawn with). */
export function setCoverFont(family: string | null): void {
  override = family;
}

/** The font actually used: the chosen family, at the nearest weight it has. */
function resolved(f: FontSpec): FontSpec {
  if (!override || override === f.family) return f;
  const have = WEIGHTS[override] ?? [400, 700];
  const want = f.weight ?? 400;
  const weight = have.reduce((best, w) => (Math.abs(w - want) < Math.abs(best - want) ? w : best), have[0]);
  const italic = f.italic && override !== "Poppins" && override !== "Inter"; // no italic files for these two
  return { ...f, family: override, weight, italic };
}

export function measure(text: string, f0: FontSpec): number {
  const f = resolved(f0);
  if (typeof document !== "undefined") {
    ctx ??= document.createElement("canvas").getContext("2d");
  }
  const spacing = (f.letterSpacing ?? 0) * Math.max(0, text.length - 1);
  if (!ctx) return text.length * f.size * 0.55 + spacing; // SSR fallback
  ctx.font = `${f.italic ? "italic " : ""}${f.weight ?? 400} ${f.size}px "${f.family}"`;
  return ctx.measureText(text).width + spacing;
}

export function wrap(text: string, f: FontSpec, maxWidth: number): string[] {
  const lines: string[] = [];
  for (const paragraph of text.split("\n")) {
    const words = paragraph.split(/\s+/).filter(Boolean);
    let line = "";
    for (const word of words) {
      const candidate = line ? `${line} ${word}` : word;
      if (measure(candidate, f) <= maxWidth || !line) {
        line = candidate;
      } else {
        lines.push(line);
        line = word;
      }
    }
    if (line) lines.push(line);
  }
  return lines;
}

/** Shrinks the font until the text fits in maxLines (down to minSize). */
export function fit(
  text: string,
  f: FontSpec,
  maxWidth: number,
  maxLines: number,
  minSize: number,
): { lines: string[]; size: number } {
  let size = f.size;
  let lines = wrap(text, { ...f, size }, maxWidth);
  while (lines.length > maxLines && size > minSize) {
    size -= 1;
    lines = wrap(text, { ...f, size }, maxWidth);
  }
  return { lines, size };
}

export function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

type Anchor = "start" | "middle" | "end";

/** Draws wrapped lines; returns the y just below the block. */
export function textBlock(
  out: string[],
  lines: string[],
  x: number,
  y: number,
  f0: FontSpec,
  color: string,
  opts: { anchor?: Anchor; lineHeight?: number } = {},
): number {
  const f = resolved(f0);
  const lh = opts.lineHeight ?? f.size * 1.25;
  lines.forEach((line, i) => {
    out.push(
      `<text x="${x.toFixed(1)}" y="${(y + i * lh).toFixed(1)}" font-family="${f.family}" ` +
        `font-size="${f.size}" font-weight="${f.weight ?? 400}"` +
        (f.italic ? ` font-style="italic"` : "") +
        (f.letterSpacing ? ` letter-spacing="${f.letterSpacing}"` : "") +
        ` text-anchor="${opts.anchor ?? "start"}" fill="${color}">${esc(line)}</text>`,
    );
  });
  return y + lines.length * lh;
}
