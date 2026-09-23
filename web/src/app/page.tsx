import Link from "next/link";
import { HeroCovers } from "@/components/HeroCovers";
import { Footer } from "@/components/Footer";
import { Logo } from "@/components/Logo";

const FEATURES = [
  { icon: "🎨", title: "Page de garde", text: "En-tête bilingue République / Ministère / École, logo, encadreurs. 4 styles, 5 couleurs." },
  { icon: "📑", title: "Sommaire & table des matières", text: "Générés automatiquement, avec les bons numéros de page." },
  { icon: "🔠", title: "Titres & chapitres", text: "Parties, chapitres, I., A., 1.1… détectés même si tu n'as rien mis en gras." },
  { icon: "•", title: "Listes propres", text: "Tes tirets et « 1) » deviennent de vraies puces et listes numérotées." },
  { icon: "▦", title: "Tableaux & légendes", text: "« Tableau 1 » au-dessus, « Figure 1 » en dessous, numérotés et listés." },
  { icon: "i·1", title: "Pagination aux normes", text: "i, ii, iii pour les pages préliminaires, puis 1, 2, 3 dès l'introduction." },
];

const FAQ = [
  ["Est-ce que vous modifiez mon texte ?", "Non. Paginya ne change pas tes mots : il s'occupe seulement de la présentation. On vérifie automatiquement que rien n'est perdu."],
  ["Comment je paie ?", "Par MTN Mobile Money ou Orange Money. Tu vois tout ton document gratuitement avant, tu paies seulement pour le télécharger."],
  ["Et si mon encadreur demande des corrections ?", "Tu modifies et tu retélécharges gratuitement pendant 7 jours avec le même lien."],
  ["Mon école n'est pas dans la liste ?", "Choisis « Mon école n'est pas dans la liste » et tape ton en-tête : Paginya le met en forme comme les autres."],
];

const RAW = `REMERCIEMENTS
Au moment où nous achevons notre formation…
- Au Professeur Alice NGA MINKALA ;
- Au chef de département…

CHAPITRE I : HISTORIQUE ET MISSIONS
I. Historique
ADVANS Cameroun est une institution…
1. Collecter l'épargne
2. Octroyer des crédits
Poste   Effectif   Rôle
Chef d'agence   1   Direction
Tableau 1 : Répartition du personnel`;

export default function Home() {
  return (
    <main className="relative flex flex-1 flex-col overflow-hidden">
      <div className="pointer-events-none absolute -top-40 -right-32 h-[28rem] w-[28rem] rounded-full bg-brand-100 blur-3xl" />
      <div className="pointer-events-none absolute top-96 -left-40 h-80 w-80 rounded-full bg-amber-100/70 blur-3xl" />

      <header className="relative mx-auto flex w-full max-w-6xl items-center justify-between px-5 pt-[max(1.25rem,env(safe-area-inset-top))] pb-4">
        <Logo />
        <nav className="flex items-center gap-1 text-sm font-semibold">
          <Link href="/garde" className="hidden rounded-full px-3 py-2 text-slate-600 hover:bg-white sm:block">Page de garde</Link>
          <Link href="/document" className="hidden rounded-full px-3 py-2 text-slate-600 hover:bg-white sm:block">Mise en forme</Link>
          <Link href="/document" className="rounded-full bg-ink px-3.5 py-2 text-white sm:hidden">Commencer</Link>
        </nav>
      </header>

      {/* Hero */}
      <section className="relative mx-auto grid w-full max-w-6xl items-center gap-2 px-5 pt-4 pb-12 lg:grid-cols-2 lg:gap-10 lg:pt-10">
        <div>
          <span className="inline-flex items-center gap-2 rounded-full bg-white/90 px-3 py-1.5 text-xs font-bold text-brand-700 ring-1 ring-brand-100">
            🇨🇲 Aux normes des universités camerounaises
          </span>
          <h1 className="mt-4 font-display text-[2.4rem] leading-[1.05] font-extrabold tracking-tight text-ink sm:text-5xl lg:text-[3.6rem]">
            Tu écris.<br />
            On rend ça <span className="bg-gradient-to-r from-brand-500 to-emerald-400 bg-clip-text text-transparent">propre</span>.
          </h1>
          <p className="mt-4 max-w-md text-[1.05rem] leading-relaxed text-slate-600">
            Page de garde, sommaire, titres, listes, tableaux, pagination… Ton rapport, ton mémoire ou ton exposé prêt à imprimer, sans toucher à Word.
          </p>

          <div className="mt-7 grid gap-3 sm:max-w-md">
            <Link href="/document" className="group flex items-center gap-4 rounded-3xl bg-brand-500 p-4 text-white shadow-xl shadow-brand-500/25 transition hover:bg-brand-600 active:scale-[.98]">
              <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-white/15 text-2xl">📄</span>
              <span className="flex-1">
                <span className="block font-display text-lg font-bold">Mettre en forme mon document</span>
                <span className="block text-sm text-white/80">Word, PDF, photos ou texte collé</span>
              </span>
              <span className="text-2xl transition group-hover:translate-x-1">→</span>
            </Link>
            <Link href="/garde" className="group flex items-center gap-4 rounded-3xl bg-white p-4 ring-1 ring-slate-200 transition hover:ring-brand-300 active:scale-[.98]">
              <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-brand-50 text-2xl">🎨</span>
              <span className="flex-1">
                <span className="block font-display text-lg font-bold text-ink">Créer une page de garde</span>
                <span className="block text-sm text-slate-500">Prête en 1 minute, aux normes de ton école</span>
              </span>
              <span className="text-2xl text-slate-400 transition group-hover:translate-x-1">→</span>
            </Link>
          </div>

          <div className="mt-3 grid grid-cols-2 gap-2 sm:max-w-md">
            <Link href="/lettre" className="flex items-center gap-2.5 rounded-2xl bg-white/80 px-3.5 py-3 text-sm font-bold text-ink ring-1 ring-slate-200 transition hover:ring-brand-300">
              <span className="text-lg">✉️</span> Lettre / demande
            </Link>
            <Link href="/epreuve" className="flex items-center gap-2.5 rounded-2xl bg-white/80 px-3.5 py-3 text-sm font-bold text-ink ring-1 ring-slate-200 transition hover:ring-brand-300">
              <span className="text-lg">📝</span> Épreuve (profs)
            </Link>
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-2 text-xs font-semibold text-slate-600">
            <span className="rounded-full bg-white px-3 py-1.5 ring-1 ring-slate-200">✨ Aperçu gratuit</span>
            <span className="rounded-full bg-yellow-300 px-3 py-1.5 text-ink">MTN MoMo</span>
            <span className="rounded-full bg-orange-500 px-3 py-1.5 text-white">Orange Money</span>
          </div>
        </div>
        <HeroCovers />
      </section>

      {/* Before / after */}
      <section className="relative bg-ink py-14 text-white">
        <div className="mx-auto w-full max-w-6xl px-5">
          <p className="text-sm font-bold tracking-wide text-brand-200 uppercase">Avant / après</p>
          <h2 className="mt-2 max-w-xl font-display text-3xl leading-tight font-extrabold">Ton texte tel quel. Le résultat, en quelques secondes.</h2>
          <div className="mt-8 grid items-center gap-5 md:grid-cols-[1fr_auto_1fr]">
            <div className="rounded-3xl bg-white/5 p-5 ring-1 ring-white/10">
              <p className="mb-3 text-xs font-bold tracking-wide text-white/50 uppercase">Ce que tu as tapé</p>
              <pre className="font-mono text-[12.5px] leading-relaxed whitespace-pre-wrap text-white/80">{RAW}</pre>
            </div>
            <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-brand-500 text-xl font-bold shadow-lg shadow-brand-500/40 md:rotate-0">→</div>
            <div className="grid grid-cols-2 gap-3">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/exemples/apres-sommaire.png" alt="Sommaire généré automatiquement" className="rounded-md bg-white shadow-2xl" />
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/exemples/apres-chapitre.png" alt="Chapitre mis en forme avec liste et tableau" className="translate-y-6 rounded-md bg-white shadow-2xl" />
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="relative mx-auto w-full max-w-6xl px-5 py-16">
        <h2 className="font-display text-3xl font-extrabold text-ink">Tout ce qu&apos;on fait à ta place</h2>
        <div className="mt-7 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="rounded-3xl bg-white p-5 ring-1 ring-slate-100 transition hover:shadow-lg">
              <span className="grid h-11 w-11 place-items-center rounded-2xl bg-brand-50 font-display text-lg font-bold text-brand-700">{f.icon}</span>
              <h3 className="mt-3 font-display text-lg font-bold text-ink">{f.title}</h3>
              <p className="mt-1 text-sm leading-relaxed text-slate-600">{f.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How you pay (no numbers here: the price is shown at the end, before paying) */}
      <section className="relative mx-auto w-full max-w-6xl px-5 pb-16">
        <div className="grid gap-6 rounded-[32px] bg-white p-7 ring-1 ring-slate-100 md:grid-cols-[1.2fr_1fr] md:items-center md:p-10">
          <div>
            <h2 className="font-display text-3xl leading-tight font-extrabold text-ink">Tu paies seulement si le résultat te plaît.</h2>
            <p className="mt-3 text-slate-600">
              Importe, regarde toutes tes pages, change le style autant que tu veux : c&apos;est gratuit. Tu paies une seule fois, en Mobile Money, quand tu télécharges.
            </p>
          </div>
          <ul className="space-y-3 text-[15px] text-slate-700">
            {["Aperçu complet, sans inscription", "MTN MoMo ou Orange Money, en 2 touches", "Word + PDF prêts à imprimer", "Modifications gratuites pendant 7 jours"].map((t) => (
              <li key={t} className="flex gap-3"><span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">✓</span>{t}</li>
            ))}
          </ul>
        </div>
      </section>

      {/* FAQ */}
      <section className="relative mx-auto w-full max-w-3xl px-5 pb-20">
        <h2 className="font-display text-3xl font-extrabold text-ink">Questions fréquentes</h2>
        <div className="mt-6 space-y-2.5">
          {FAQ.map(([q, a]) => (
            <details key={q} className="group rounded-2xl bg-white p-4 ring-1 ring-slate-100 open:ring-brand-200">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 font-display font-bold text-ink">
                {q}
                <span className="text-xl text-brand-500 transition group-open:rotate-45">+</span>
              </summary>
              <p className="mt-2 text-[15px] leading-relaxed text-slate-600">{a}</p>
            </details>
          ))}
        </div>
      </section>

      <Footer />
    </main>
  );
}
