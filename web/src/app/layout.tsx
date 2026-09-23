import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Paginya · Des documents propres, sans toucher à Word",
  description:
    "Pages de garde aux normes de ton école et mise en forme automatique de tes documents. Word + PDF, paiement Mobile Money.",
  manifest: "/manifest.webmanifest",
  applicationName: "Paginya",
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
      <body className="min-h-full flex flex-col font-sans">{children}</body>
    </html>
  );
}
