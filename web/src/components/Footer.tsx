import Link from "next/link";
import { Logo } from "./Logo";

export const CONTACT = {
  email: "zeudjotiyo@gmail.com",
  whatsapp: "+237 673 41 43 81",
};

export function Footer() {
  return (
    <footer className="mt-auto border-t border-slate-100 bg-white/70 py-8">
      <div className="mx-auto grid max-w-6xl gap-6 px-5 sm:grid-cols-[1fr_auto]">
        <div>
          <Logo />
          <p className="mt-2 max-w-sm text-xs text-slate-500">On présente ton travail, on ne l&apos;écrit pas à ta place. · Fait au Cameroun 🇨🇲</p>
        </div>
        <nav className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm text-slate-600">
          <Link href="/document" className="hover:text-brand-700">Mise en forme</Link>
          <Link href="/tarifs" className="hover:text-brand-700">Tarifs</Link>
          <Link href="/garde" className="hover:text-brand-700">Page de garde</Link>
          <Link href="/cgu" className="hover:text-brand-700">Conditions (CGU)</Link>
          <a href={`mailto:${CONTACT.email}`} className="hover:text-brand-700">Contact</a>
          <Link href="/confidentialite" className="hover:text-brand-700">Confidentialité</Link>
          <Link href="/lettre" className="hover:text-brand-700">Lettre / demande</Link>
          <Link href="/mentions-legales" className="hover:text-brand-700">Mentions légales</Link>
          <Link href="/epreuve" className="hover:text-brand-700">Épreuve (profs)</Link>
        </nav>
      </div>
    </footer>
  );
}

export function LegalPage({ title, updated, children }: { title: string; updated: string; children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="mx-auto flex w-full max-w-3xl items-center justify-between px-5 pt-6 pb-2">
        <Logo />
        <Link href="/" className="text-sm font-semibold text-slate-500 hover:text-slate-700">← Accueil</Link>
      </header>
      <main className="mx-auto w-full max-w-3xl px-5 pt-6 pb-16">
        <h1 className="font-display text-3xl font-extrabold text-ink">{title}</h1>
        <p className="mt-1 text-sm text-slate-500">Dernière mise à jour : {updated}</p>
        <div className="legal mt-8 space-y-6 text-[15px] leading-relaxed text-slate-700 [&_h2]:mt-8 [&_h2]:font-display [&_h2]:text-xl [&_h2]:font-bold [&_h2]:text-ink [&_li]:ml-5 [&_li]:list-disc [&_ul]:space-y-1.5">
          {children}
        </div>
      </main>
      <Footer />
    </div>
  );
}
