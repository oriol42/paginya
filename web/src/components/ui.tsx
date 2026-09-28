import type { ReactNode } from "react";
import { Icon } from "./Icon";

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[13px] font-bold tracking-wide text-ink/80">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-ink/60">{hint}</span>}
    </label>
  );
}

// Typed-form look: white paper field, ink underline that turns into the highlighter on focus.
const base =
  "press w-full min-w-0 rounded-md border-0 bg-paper px-3.5 py-3 text-[16px] text-ink shadow-[inset_0_-2px_0_0_rgba(22,24,26,0.18)] ring-1 ring-black/10 " +
  "placeholder:text-ink/40 focus:shadow-[inset_0_-3px_0_0_var(--color-hi-deep)] focus:ring-ink/25 focus:outline-none";

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${base} ${props.className ?? ""}`} />;
}

/** Grows with its content (`rows` is the minimum) so no line is ever cut in half. */
export function TextArea({ rows = 2, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const lines = typeof props.value === "string" ? props.value.split("\n").length : 0;
  return <textarea {...props} rows={Math.max(rows, lines)} className={`${base} resize-none leading-relaxed ${props.className ?? ""}`} />;
}

export function Select({ className = "", children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <span className={`relative block ${className}`}>
      <select {...props} className={`${base} appearance-none pr-10 font-semibold`}>{children}</select>
      <Icon name="chevron-down" size={18} className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 text-ink/60" />
    </span>
  );
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="press flex w-full items-center justify-between gap-3 rounded-md bg-paper px-3.5 py-3 text-left text-[15px] font-semibold text-ink ring-1 ring-black/10"
    >
      {label}
      <span className={`relative h-6 w-11 shrink-0 rounded-full transition-colors duration-200 ${checked ? "bg-board" : "bg-ink/20"}`}>
        <span
          className={`absolute top-0.5 left-0.5 grid h-5 w-5 place-items-center rounded-full bg-white shadow transition-transform duration-200 ease-[var(--ease-out-expo)] ${checked ? "translate-x-5" : ""}`}
        >
          {checked && <Icon name="check" size={12} stroke={3} className="text-board" />}
        </span>
      </span>
    </button>
  );
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3">
      <h3 className="font-display text-[19px] leading-none font-black tracking-wide text-ink uppercase">{title}</h3>
      {children}
    </section>
  );
}

export function Segmented<T extends string | number>({
  value, options, onChange,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="grid rounded-md bg-ink/[0.07] p-1" style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}>
      {options.map((o) => (
        <button
          key={String(o.value)}
          type="button"
          onClick={() => onChange(o.value)}
          className={`press rounded px-2 py-2 text-[14px] font-bold transition-colors ${value === o.value ? "bg-paper text-ink shadow-[0_1px_2px_rgba(0,0,0,0.18)]" : "text-ink/55 hover:text-ink"}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** Bottom sheet on phones, centered dialog on larger screens: a sheet of paper pinned over the page. */
export function Sheet({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-board/70 sm:items-center" onClick={onClose}>
      <div
        className="sheet-in paper relative flex max-h-[88dvh] w-full max-w-lg flex-col rounded-t-xl sm:rounded-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <span className="pin top-2.5 left-1/2 -translate-x-1/2" aria-hidden />
        <div className="flex items-center justify-between px-5 pt-7 pb-2">
          <h2 className="font-display text-[26px] leading-none font-black tracking-wide text-ink uppercase">{title}</h2>
          <button type="button" onClick={onClose} className="press grid h-10 w-10 place-items-center rounded-md text-ink/60 ring-1 ring-black/10 hover:text-ink" aria-label="Fermer">
            <Icon name="x" size={18} />
          </button>
        </div>
        <div className="overflow-y-auto px-5 pt-2 pb-[max(1.5rem,env(safe-area-inset-bottom))]">{children}</div>
      </div>
    </div>
  );
}

/** Violet ink status stamp (EN COURS, CONFORME, PAYÉ). `land` plays the press once. */
export function Stamp({ children, land = false, className = "" }: { children: ReactNode; land?: boolean; className?: string }) {
  return <span className={`stamp ${land ? "stamp-in" : ""} ${className}`}>{children}</span>;
}

/** The one primary action of a screen: a yellow label pinned on the board. Pressing pushes the pin in. */
export function PinLabel({ children, className = "", ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={`pin-label press relative inline-flex items-center justify-center gap-2 rounded-md bg-hi px-6 py-4 font-display text-[22px] leading-none font-black tracking-wide text-ink uppercase shadow-[0_2px_0_0_var(--color-hi-deep),0_12px_24px_-10px_rgba(0,0,0,0.55)] hover:bg-[#ffe04a] disabled:opacity-50 ${className}`}
    >
      <span className="pin -top-2 left-1/2 -translate-x-1/2" aria-hidden />
      {children}
    </button>
  );
}
