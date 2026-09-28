import Link from "next/link";
import { Icon } from "./Icon";
import { Logo } from "./Logo";

export const CONTACT = {
  email: "zeudjotiyo@gmail.com",
  whatsapp: "+237 673 41 43 81",
};

export function Footer() {
  return (
    <footer className="board mt-auto py-10">
      <div className="mx-auto grid max-w-6xl gap-8 px-6 sm:grid-cols-[1fr_auto]">
        <div>
          <Logo tone="board" />
          <p className="mt-3 max-w-sm text-[14px] text-white/65">On présente ton travail, on ne l&apos;écrit pas à ta place. Fait au Cameroun.</p>
          <p className="mt-1 text-[14px] text-white/65">WhatsApp {CONTACT.whatsapp}</p>
        </div>
        <nav className="grid grid-cols-2 gap-x-10 gap-y-2.5 text-[15px] text-white/75">
          <Link href="/document" className="hover:text-white">Mise en forme</Link>
          <Link href="/tarifs" className="hover:text-white">Tarifs</Link>
          <Link href="/garde" className="hover:text-white">Page de garde</Link>
          <Link href="/cgu" className="hover:text-white">Conditions (CGU)</Link>
          <Link href="/lettre" className="hover:text-white">Lettre / demande</Link>
          <Link href="/confidentialite" className="hover:text-white">Confidentialité</Link>
          <Link href="/epreuve" className="hover:text-white">Épreuve (profs)</Link>
          <Link href="/mentions-legales" className="hover:text-white">Mentions légales</Link>
          <a href={`mailto:${CONTACT.email}`} className="hover:text-white">Contact</a>
        </nav>
      </div>
    </footer>
  );
}

export function LegalPage({ title, updated, children }: { title: string; updated: string; children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="mx-auto flex w-full max-w-3xl items-center justify-between px-6 pt-6 pb-2">
        <Logo />
        <Link href="/" className="inline-flex items-center gap-1.5 text-[15px] font-semibold text-ink/60 hover:text-ink">
          <Icon name="arrow-left" size={17} /> Accueil
        </Link>
      </header>
      <main className="mx-auto w-full max-w-3xl px-6 pt-8 pb-16">
        <div className="paper rounded-[2px] px-6 py-8 sm:px-10">
          <h1 className="font-display text-[2.6rem] leading-[0.95] font-black uppercase">{title}</h1>
          <p className="mt-2 text-[14px] text-ink/55">Dernière mise à jour : {updated}</p>
          <div className="legal mt-8 max-w-prose space-y-6 text-[16px] leading-relaxed text-ink/80 [&_h2]:mt-9 [&_h2]:font-display [&_h2]:text-[24px] [&_h2]:leading-none [&_h2]:font-black [&_h2]:text-ink [&_h2]:uppercase [&_li]:ml-5 [&_li]:list-disc [&_ul]:space-y-1.5">
            {children}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
