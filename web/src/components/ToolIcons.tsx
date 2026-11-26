/**
 * The tools on the home page, drawn as the files they give: a Word sheet, a PowerPoint deck, a PDF. Each format keeps
 * its well-known colour and letter (blue W, orange P, red PDF), as file icons do, without copying Microsoft's or
 * Adobe's own logos (their marks may not be used on a commercial site without their permission).
 */

import type { ReactNode } from "react";

export type ToolKind = "word" | "slides" | "cover" | "convert" | "letter" | "exam";

const SHEET = "M15 5H35L44 14V48A3 3 0 0 1 41 51H15A3 3 0 0 1 12 48V8A3 3 0 0 1 15 5Z";
const FOLD = "M35 5V11A3 3 0 0 0 38 14H44";

/** A white sheet with its folded corner and a soft shadow underneath. */
function Sheet({ children }: { children?: ReactNode }) {
  return (
    <g>
      <path d={SHEET} transform="translate(0 1.6)" className="fill-ink/10" />
      <path d={SHEET} className="fill-white stroke-ink/20" strokeWidth="1.2" />
      <path d={FOLD} className="fill-wall stroke-ink/20" strokeWidth="1.2" strokeLinejoin="round" />
      {children}
    </g>
  );
}

function Lines({ x = 18, y = 21, widths = [18, 20, 14, 19] }: { x?: number; y?: number; widths?: number[] }) {
  return (
    <g className="fill-ink/15">
      {widths.map((w, i) => (
        <rect key={i} x={x} y={y + i * 5} width={w} height="2.4" rx="1.2" />
      ))}
    </g>
  );
}

/** The format's badge: a coloured tile with its letter, on the lower left of the sheet. */
function Badge({ text, className, x = 4, y = 28 }: { text: string; className: string; x?: number; y?: number }) {
  const w = text.length > 1 ? 27 : 21;
  return (
    <g>
      <rect x={x} y={y + 1.2} width={w} height="19" rx="4.5" className="fill-ink/15" />
      <rect x={x} y={y} width={w} height="19" rx="4.5" className={className} />
      <text x={x + w / 2} y={y + 14} textAnchor="middle" fontFamily="'Segoe UI', Arial, sans-serif" fontWeight="700"
        fontSize={text.length > 1 ? 10 : 13.5} className="fill-white">{text}</text>
    </g>
  );
}

export function ToolIcon({ kind, className = "" }: { kind: ToolKind; className?: string }) {
  return (
    <svg viewBox="0 0 56 56" width="56" height="56" aria-hidden="true" focusable="false" className={`shrink-0 ${className}`}>
      {kind === "word" && (
        <>
          <Sheet>
            <rect x="18" y="17" width="16" height="3.2" rx="1.6" className="fill-word/70" />
            <Lines y={24} widths={[20, 17, 20, 12]} />
          </Sheet>
          <Badge text="W" className="fill-word" />
        </>
      )}
      {kind === "slides" && (
        <>
          <rect x="5" y="9" width="40" height="28" rx="3.5" className="fill-wall stroke-ink/20" strokeWidth="1.2" />
          <rect x="11" y="15.6" width="40" height="28" rx="3.5" className="fill-ink/10" />
          <rect x="11" y="14" width="40" height="28" rx="3.5" className="fill-white stroke-ink/20" strokeWidth="1.2" />
          <rect x="16" y="19" width="15" height="2.8" rx="1.4" className="fill-ink/25" />
          <path d="M39.5 23.5A6.5 6.5 0 1 1 33 30H39.5Z" className="fill-slides/30" />
          <path d="M33 30A6.5 6.5 0 0 1 39.5 23.5V30Z" className="fill-slides" />
          <rect x="16" y="26" width="3" height="9" rx="1" className="fill-ink/15" />
          <rect x="21" y="29" width="3" height="6" rx="1" className="fill-ink/15" />
          <Badge text="P" className="fill-slides" x={4} y={31} />
        </>
      )}
      {kind === "cover" && (
        <>
          <Sheet>
            <circle cx="28" cy="17" r="4.2" className="fill-board/10 stroke-board/60" strokeWidth="1.1" />
            <path d="M28 14.6 28.8 16.4 30.6 16.6 29.2 17.8 29.6 19.6 28 18.7 26.4 19.6 26.8 17.8 25.4 16.6 27.2 16.4Z" className="fill-board/60" />
            <rect x="20" y="25" width="16" height="3" rx="1.5" className="fill-ink/30" />
            <rect x="22.5" y="31" width="11" height="2.4" rx="1.2" className="fill-ink/15" />
            <rect x="24" y="42" width="8" height="2.2" rx="1.1" className="fill-ink/15" />
          </Sheet>
          <Badge text="W" className="fill-word" />
        </>
      )}
      {kind === "convert" && (
        <>
          <g transform="translate(-4 -2) scale(0.78)">
            <Sheet>
              <Lines y={22} widths={[18, 20, 14]} />
            </Sheet>
            <Badge text="W" className="fill-word" x={7} y={7} />
          </g>
          <g transform="translate(13 10) scale(0.76)">
            <Sheet>
              <Lines y={22} widths={[18, 20, 14]} />
            </Sheet>
            <Badge text="PDF" className="fill-pdf" x={6} y={28} />
          </g>
        </>
      )}
      {kind === "letter" && (
        <>
          <rect x="14" y="7" width="28" height="30" rx="2.5" className="fill-white stroke-ink/20" strokeWidth="1.2" />
          <Lines x={18} y={13} widths={[14, 20, 17]} />
          <path d="M6 26.5 28 40 50 26.5V47A3 3 0 0 1 47 50H9A3 3 0 0 1 6 47Z" className="fill-ink/10" transform="translate(0 1.6)" />
          <path d="M6 26.5 28 40 50 26.5V47A3 3 0 0 1 47 50H9A3 3 0 0 1 6 47Z" className="fill-wall stroke-ink/20" strokeWidth="1.2" strokeLinejoin="round" />
          <path d="M6.6 48.6 22.5 36.6M49.4 48.6 33.5 36.6" className="stroke-ink/20" strokeWidth="1.2" fill="none" />
          <Badge text="W" className="fill-word" x={4} y={29} />
        </>
      )}
      {kind === "exam" && (
        <>
          <Sheet>
            <rect x="18" y="12" width="14" height="2.6" rx="1.3" className="fill-ink/30" />
            {[18, 24, 30, 36].map((y) => (
              <g key={y}>
                <rect x="18" y={y} width="3.6" height="3.6" rx="0.9" className="fill-none stroke-ink/30" strokeWidth="1.1" />
                <rect x="24" y={y + 0.6} width="14" height="2.4" rx="1.2" className="fill-ink/15" />
              </g>
            ))}
            <path d="M18.8 19.9 19.9 21 21.9 18.6" className="fill-none stroke-board" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
          </Sheet>
          <Badge text="PDF" className="fill-pdf" />
        </>
      )}
    </svg>
  );
}
