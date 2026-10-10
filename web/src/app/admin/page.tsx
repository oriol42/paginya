import type { Metadata } from "next";
import { AdminCode } from "@/components/AdminCode";

export const metadata: Metadata = { title: "Équipe", robots: { index: false } };

/** The team types its code once on this phone or computer: its own documents are then free. */
export default function Admin() {
  return (
    <main className="grid min-h-dvh place-items-center bg-ink/[0.03] px-6">
      <AdminCode />
    </main>
  );
}
