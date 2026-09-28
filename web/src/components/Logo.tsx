import Link from "next/link";

/** Wordmark: condensed black letters, the dot is a push-pin. `tone` follows the ground it sits on. */
export function Logo({ className = "", tone = "paper" }: { className?: string; tone?: "paper" | "board" }) {
  return (
    <Link href="/" className={`inline-flex items-center gap-2 ${className}`} aria-label="Paginya, accueil">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/icon.svg" alt="" width={28} height={28} className="rounded-md" />
      <span className={`font-display text-[26px] leading-none font-black tracking-wide uppercase ${tone === "board" ? "text-white" : "text-ink"}`}>
        Paginya
        <span className="ml-0.5 inline-block h-2.5 w-2.5 translate-y-[-2px] rounded-full bg-pin shadow-[0_2px_2px_rgba(0,0,0,0.35)] align-baseline" aria-hidden />
      </span>
    </Link>
  );
}
