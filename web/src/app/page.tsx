import Link from "next/link";
import { Footer } from "@/components/Footer";
import { Icon } from "@/components/Icon";
import { Logo } from "@/components/Logo";

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

const STEPS: [string, string, string][] = [
  ["Dépose", "Ton fichier Word ou PDF, des photos de tes pages, ou ton texte collé depuis WhatsApp ou ChatGPT.", "Même tout en désordre."],
  ["Vérifie", "Tu vois toutes tes pages gratuitement. Tu choisis le type : cours, exposé, rapport de stage, mémoire…", "Rien n'est ajouté sans ton accord."],
  ["Télécharge", "Tu paies une fois par MTN MoMo ou Orange Money et tu récupères ton Word et ton PDF.", "Corrections gratuites 7 jours."],
];

// What Paginya does, laid out as the table of contents it generates.
const CONTENTS: [string, string][] = [
  ["Page de garde aux normes", "en-tête, logo, encadreurs"],
  ["Titres et chapitres", "Parties, I., A., 1.1… détectés"],
  ["Sommaire et table des matières", "si ton document en a besoin"],
  ["Listes et tableaux", "vraies puces, légendes numérotées"],
  ["Pagination", "i, ii, iii puis 1, 2, 3"],
  ["Typographie française", "espaces, « guillemets »"],
];

const PRICES: [string, string][] = [
  ["Page de garde", "350"],
  ["Lettre / demande", "350"],
  ["CV · Épreuve", "550"],
  ["Document ≤ 15 pages", "1 000"],
  ["Rapport 16 – 40 pages", "2 000"],
  ["Mémoire + de 40 pages", "3 000"],
];

const FAQ: [string, string][] = [
  ["Est-ce que vous modifiez mon texte ?", "Non. Paginya ne change pas tes mots : il s'occupe seulement de la présentation."],
  ["Comment je paie ?", "Par MTN Mobile Money ou Orange Money. Tu vois tout ton document gratuitement avant, tu paies seulement pour le télécharger."],
  ["Et si mon encadreur demande des corrections ?", "Tu modifies et tu retélécharges gratuitement pendant 7 jours avec le même lien."],
  ["Mon école n'est pas dans la liste ?", "Choisis « Autre » et tape ton en-tête : Paginya le met en forme comme les autres."],
];

export default function Home() {
  return (
    <main className="flex flex-1 flex-col">
      {/* ---------- The board ---------- */}
      <section className="board board-frame relative overflow-hidden">
        <header className="relative mx-auto flex w-full max-w-6xl items-center justify-between px-6 pt-[max(1.4rem,env(safe-area-inset-top))] pb-2">
          <Logo tone="board" />
          <nav className="flex items-center gap-1 text-[15px] font-semibold">
            <Link href="/tarifs" className="hidden rounded-md px-3 py-2 text-white/75 hover:text-white sm:block">Tarifs</Link>
            <Link href="/garde" className="hidden rounded-md px-3 py-2 text-white/75 hover:text-white sm:block">Page de garde</Link>
            <Link href="/document" className="press rounded-md bg-white/10 px-3.5 py-2 text-white ring-1 ring-white/20 hover:bg-white/15">Commencer</Link>
          </nav>
        </header>

        <div className="relative mx-auto grid w-full max-w-6xl gap-10 px-6 pt-6 pb-14 lg:grid-cols-[1.05fr_1fr] lg:items-center lg:pt-12 lg:pb-20">
          <div className="rise">
            <h1 className="font-display text-[3.4rem] leading-[0.9] font-black tracking-[-0.01em] uppercase sm:text-[4.6rem] lg:text-[5.4rem]">
              Ton document,<br />
              <span className="relative inline-block -rotate-1"><span className="hi text-ink">aux normes</span><span className="pin -top-2 left-3" aria-hidden /></span><br />
              de ton école.
            </h1>
            <p className="mt-5 max-w-md text-[17px] leading-relaxed text-white/80">
              Rapport de stage, mémoire, cours ou exposé : dépose-le tel quel, Paginya le met en page en une minute. Tu vois tout gratuitement avant de payer.
            </p>
            <div className="mt-7 flex flex-col items-start gap-3">
              <Link
                href="/document"
                className="pin-label press relative inline-flex -rotate-1 items-center gap-3 rounded-[3px] bg-hi px-6 pt-5 pb-4 font-display text-[19px] leading-none sm:text-[23px] font-black tracking-wide text-ink uppercase shadow-[0_2px_0_0_var(--color-hi-deep),0_14px_28px_-10px_rgba(0,0,0,0.6)] hover:bg-[#ffe04a]"
              >
                <span className="pin -top-2 left-1/2 -translate-x-1/2" aria-hidden />
                Mettre mon document au propre
                <Icon name="arrow-right" size={22} stroke={2.6} />
              </Link>
              <p className="text-[14px] font-semibold text-white/70">Aperçu gratuit · dès 350 F · MTN MoMo et Orange Money</p>
            </div>
          </div>

          {/* Before → after, pinned on the board */}
          <div className="relative mx-auto h-[430px] w-full max-w-[460px] sm:h-[520px]">
            <figure
              style={{ ["--tilt" as string]: "-5deg", animationDelay: "80ms" }}
              className="paper crumpled pin-in absolute top-2 left-0 w-[62%] origin-top-left overflow-hidden rounded-[2px] p-4 [transform:rotate(var(--tilt))] sm:p-5"
            >
              <span className="pin top-2 left-1/2 -translate-x-1/2" aria-hidden />
              <pre className="mt-3 font-mono text-[9.5px] leading-[1.55] break-words whitespace-pre-wrap text-ink/70 sm:text-[11px]">{RAW}</pre>
              <figcaption className="mt-3 border-t border-dashed border-ink/20 pt-2 text-[12px] font-bold tracking-wide text-ink/50 uppercase">Ce que tu as tapé</figcaption>
            </figure>
            <figure
              style={{ ["--tilt" as string]: "3deg", animationDelay: "260ms" }}
              className="paper pin-in absolute right-0 bottom-0 w-[64%] rounded-[2px] p-2 [transform:rotate(var(--tilt))]"
            >
              <span className="pin top-1.5 left-1/2 -translate-x-1/2" aria-hidden />
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/exemples/apres-chapitre.png" alt="Le même chapitre mis en forme par Paginya : titres, liste et tableau" className="mt-3 w-full" width={600} height={849} />
              <span className="stamp stamp-in absolute right-3 bottom-8 bg-paper/60 text-[26px] sm:text-[30px]" style={{ animationDelay: "900ms" }}>
                Conforme
              </span>
            </figure>
          </div>
        </div>
      </section>

      {/* ---------- Three steps, like an instruction sheet ---------- */}
      <section className="mx-auto w-full max-w-6xl px-6 py-16 sm:py-20">
        <h2 className="max-w-2xl font-display text-[2.6rem] leading-[0.95] font-black uppercase sm:text-[3.4rem]">Trois gestes, et c&apos;est rendu.</h2>
        <ol className="mt-10 grid gap-10 md:grid-cols-3 md:gap-8">
          {STEPS.map(([title, text, note], i) => (
            <li key={title} className="grid grid-cols-[auto_1fr] gap-x-5 md:block">
              <span className="row-span-3 font-display text-[5.5rem] leading-[0.8] font-black text-board tabular md:text-[7rem]" aria-hidden>{i + 1}</span>
              <h3 className="font-display text-[28px] leading-none font-black uppercase md:mt-3">{title}</h3>
              <p className="mt-2 max-w-sm text-[16px] leading-relaxed text-ink/75">{text}</p>
              <p className="mt-2 inline-block -rotate-1 text-[16px] font-medium text-pen italic underline decoration-pen/40 decoration-wavy underline-offset-4">{note}</p>
            </li>
          ))}
        </ol>
        <div className="paper relative mt-14 max-w-xl -rotate-1 rounded-[2px] px-6 pt-7 pb-5" style={{ background: "#fff8c9" }}>
          <span className="pin top-2 left-6" aria-hidden />
          <p className="font-display text-[20px] font-black uppercase">Aussi, en deux minutes</p>
          <ul className="mt-3 grid gap-1 sm:grid-cols-3">
            {([["/garde", "landmark", "Page de garde"], ["/lettre", "mail", "Lettre, demande"], ["/epreuve", "pen-line", "Épreuve (profs)"]] as const).map(([href, icon, label]) => (
              <li key={href}>
                <Link href={href} className="press flex items-center gap-2 rounded-md py-2 text-[16px] font-bold hover:text-board">
                  <Icon name={icon} size={18} className="text-board" />{label}<Icon name="chevron-right" size={16} className="text-ink/40" />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* ---------- What it does, as a real table of contents ---------- */}
      <section className="board relative overflow-hidden py-16 sm:py-20">
        <div className="mx-auto grid w-full max-w-6xl gap-10 px-6 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
          <div>
            <h2 className="font-display text-[2.6rem] leading-[0.95] font-black uppercase sm:text-[3.4rem]">Tout ce qu&apos;on range à ta place.</h2>
            <p className="mt-4 max-w-md text-[17px] leading-relaxed text-white/75">
              Même si tu n&apos;as rien mis en gras, même avec des « 1- » et des « =&gt; » partout : Paginya retrouve la structure de ton travail.
            </p>
          </div>
          <div className="paper relative rounded-[2px] px-6 pt-9 pb-7 sm:px-10" style={{ transform: "rotate(-1deg)" }}>
            <span className="pin top-3 left-1/2 -translate-x-1/2" aria-hidden />
            <p className="text-center font-display text-[26px] font-black tracking-[0.2em] uppercase">Sommaire</p>
            <ul className="mt-5 space-y-3.5">
              {CONTENTS.map(([title, detail], i) => (
                <li key={title} className="flex items-baseline gap-2 text-[16px]">
                  <span className="font-bold">{title}</span>
                  <span className="min-w-6 flex-1 translate-y-[-3px] border-b-2 border-dotted border-ink/30" aria-hidden />
                  <span className="hidden text-right text-[14px] text-ink/60 sm:inline">{detail}</span>
                  <span className="w-5 text-right font-bold tabular">{i + 1}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* ---------- The official header, shown for real ---------- */}
      <section className="mx-auto w-full max-w-6xl px-6 py-16 sm:py-20">
        <div className="grid gap-10">
          <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr] lg:items-end">
            <h2 className="font-display text-[2.6rem] leading-[0.95] font-black uppercase sm:text-[3.4rem]">L&apos;en-tête de ton école, en français et en anglais.</h2>
            <div>
            <p className="max-w-md text-[17px] leading-relaxed text-ink/75">
              République du Cameroun, ministère, université, faculté : choisis ton établissement parmi près de 50, le logo se place tout seul. Tu décides de le mettre ou non.
            </p>
            <Link href="/garde" className="press mt-6 inline-flex items-center gap-2 rounded-md bg-board px-5 py-3.5 text-[16px] font-bold text-white hover:bg-board-2">
              Créer ma page de garde <Icon name="arrow-right" size={18} />
            </Link>
            </div>
          </div>
          <div className="paper relative mx-auto w-full max-w-4xl rotate-[0.6deg] rounded-[2px] px-4 pt-9 pb-8 sm:px-12" aria-label="Exemple d'en-tête officiel">
            <span className="pin top-3 left-1/2 -translate-x-1/2" aria-hidden />
            <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 text-center text-[9.5px] leading-snug font-bold sm:text-[12px]">
              <div>
                <p>RÉPUBLIQUE DU CAMEROUN</p>
                <p className="font-normal italic">Paix – Travail – Patrie</p>
                <p className="text-ink/40">********</p>
                <p>MINISTÈRE DE L&apos;ENSEIGNEMENT SUPÉRIEUR</p>
                <p className="text-ink/40">********</p>
                <p>UNIVERSITÉ DE DOUALA</p>
              </div>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logos/armoiries.png" alt="" className="h-16 w-auto sm:h-20" width={80} height={90} />
              <div>
                <p>REPUBLIC OF CAMEROON</p>
                <p className="font-normal italic">Peace – Work – Fatherland</p>
                <p className="text-ink/40">********</p>
                <p>MINISTRY OF HIGHER EDUCATION</p>
                <p className="text-ink/40">********</p>
                <p>THE UNIVERSITY OF DOUALA</p>
              </div>
            </div>
            <p className="mt-6 text-center font-display text-[22px] leading-tight font-black uppercase sm:text-[28px]">Rapport de stage</p>
            <div className="mx-auto mt-3 h-2 w-3/4 rounded bg-ink/10" />
            <div className="mx-auto mt-2 h-2 w-1/2 rounded bg-ink/10" />
          </div>
        </div>
      </section>

      {/* ---------- Price list, pinned ---------- */}
      <section className="board relative overflow-hidden py-16 sm:py-20" id="tarifs">
        <div className="mx-auto grid w-full max-w-6xl gap-10 px-6 lg:grid-cols-[1fr_1fr] lg:items-center">
          <div className="lg:order-2">
            <h2 className="font-display text-[2.6rem] leading-[0.95] font-black uppercase sm:text-[3.4rem]">Tu paies seulement si ça te plaît.</h2>
            <p className="mt-4 max-w-md text-[17px] leading-relaxed text-white/75">
              Importe, regarde toutes tes pages, change le style autant que tu veux : c&apos;est gratuit. Tu paies une seule fois, par Mobile Money, quand tu télécharges.
            </p>
          </div>
          <div className="relative pb-24 lg:order-1 lg:pr-10">
          <div className="paper relative rounded-[2px] px-6 pt-9 pb-6 sm:px-9" style={{ transform: "rotate(-1.2deg)" }}>
            <span className="pin top-3 left-1/2 -translate-x-1/2" aria-hidden />
            <p className="text-center font-display text-[26px] font-black tracking-[0.2em] uppercase">Tarifs</p>
            <table className="mt-4 w-full text-[16px]">
              <tbody>
                {PRICES.map(([label, price]) => (
                  <tr key={label} className="border-b border-ink/10 last:border-0">
                    <td className="py-2.5 font-semibold">{label}</td>
                    <td className="py-2.5 text-right font-display text-[24px] font-black tabular">{price}&nbsp;F</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-4 text-[13px] text-ink/60">Word + PDF · MTN MoMo et Orange Money</p>
          </div>
          <div className="paper absolute right-0 bottom-0 w-56 rotate-3 rounded-[2px] px-5 pt-7 pb-4" style={{ background: "#fff8c9" }}>
            <span className="pin top-2 left-1/2 -translate-x-1/2" aria-hidden />
            <p className="text-[16px] leading-snug font-medium text-pen italic">Corrections gratuites pendant 7 jours, avec le même lien.</p>
          </div>
          </div>
        </div>
      </section>

      {/* ---------- Questions ---------- */}
      <section className="mx-auto w-full max-w-3xl px-6 py-16 sm:py-20">
        <h2 className="font-display text-[2.6rem] leading-[0.95] font-black uppercase">Questions fréquentes</h2>
        <div className="mt-7 divide-y divide-ink/10 border-y border-ink/10">
          {FAQ.map(([q, a]) => (
            <details key={q} className="group py-4">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-[18px] font-bold">
                {q}
                <Icon name="plus" size={20} className="text-board transition-transform duration-200 group-open:rotate-45" />
              </summary>
              <p className="mt-2 max-w-prose text-[16px] leading-relaxed text-ink/75">{a}</p>
            </details>
          ))}
        </div>
        <Link
          href="/document"
          className="pin-label press relative mt-10 inline-flex -rotate-1 items-center gap-3 rounded-[3px] bg-hi px-6 pt-5 pb-4 font-display text-[22px] leading-none font-black tracking-wide text-ink uppercase shadow-[0_2px_0_0_var(--color-hi-deep),0_10px_20px_-10px_rgba(0,0,0,0.45)] hover:bg-[#ffe04a]"
        >
          <span className="pin -top-2 left-1/2 -translate-x-1/2" aria-hidden />
          Commencer gratuitement <Icon name="arrow-right" size={20} stroke={2.6} />
        </Link>
      </section>

      <Footer />
    </main>
  );
}
