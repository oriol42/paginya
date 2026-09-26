import type { Metadata } from "next";
import { Suspense } from "react";
import { Studio } from "@/components/studio/Studio";

export const metadata: Metadata = {
  title: "Page de garde",
  description: "Crée ta page de garde aux normes de ton école en 1 minute. Plusieurs styles, Word + PDF.",
};

export default function GardePage() {
  return (
    <Suspense>
      <Studio />
    </Suspense>
  );
}
