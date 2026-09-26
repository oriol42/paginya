import type { Metadata, Viewport } from "next";
import { WakeServer } from "@/components/WakeServer";
import { SITE_URL } from "@/lib/site";
import "./globals.css";

const DESCRIPTION =
  "Paginya met ton mémoire, ton rapport de stage, ton cours ou ta lettre au propre, aux normes camerounaises : page de garde avec le logo de ton école, en-tête République du Cameroun, sommaire. Word + PDF, paiement Mobile Money.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: "Paginya · Mise en page automatique de tes documents", template: "%s · Paginya" },
  description: DESCRIPTION,
  keywords: ["Paginya", "mise en page mémoire", "rapport de stage", "page de garde", "normes de rédaction Cameroun", "Word", "PDF", "Mobile Money"],
  manifest: "/manifest.webmanifest",
  applicationName: "Paginya",
  alternates: { canonical: "/" },
  openGraph: { type: "website", locale: "fr_CM", siteName: "Paginya", title: "Paginya · Tes documents au propre en 1 minute", description: DESCRIPTION, url: "/", images: [{ url: "/og.png", width: 1200, height: 630 }] },
  twitter: { card: "summary_large_image" },
  // Google Search Console: paste the code of the "balise HTML" method in NEXT_PUBLIC_GOOGLE_VERIFICATION
  verification: process.env.NEXT_PUBLIC_GOOGLE_VERIFICATION ? { google: process.env.NEXT_PUBLIC_GOOGLE_VERIFICATION } : undefined,
};

/** Tells Google what Paginya is (name, kind of app, price) so the name search shows it properly. */
const JSON_LD = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: "Paginya",
  url: SITE_URL,
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web, Android, iPhone",
  inLanguage: "fr",
  description: DESCRIPTION,
  offers: { "@type": "Offer", price: "0", priceCurrency: "XAF", description: "Aperçu gratuit, paiement Mobile Money au téléchargement" },
};

export const viewport: Viewport = {
  themeColor: "#0E9F6E",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className="h-full antialiased">
      <body className="min-h-full flex flex-col font-sans">
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }} />
        <WakeServer />
        {children}
      </body>
    </html>
  );
}
