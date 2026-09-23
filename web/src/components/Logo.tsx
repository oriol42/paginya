import Link from "next/link";

export function Logo({ className = "" }: { className?: string }) {
  return (
    <Link href="/" className={`flex items-center gap-2 ${className}`} aria-label="Paginya, accueil">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/icon.svg" alt="" width={30} height={30} className="rounded-lg" />
      <span className="font-display text-xl font-extrabold tracking-tight text-ink">
        paginya<span className="text-sun">.</span>
      </span>
    </Link>
  );
}
