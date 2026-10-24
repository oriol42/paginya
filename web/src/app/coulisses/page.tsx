import type { Metadata } from "next";
import { AdminLogin } from "@/components/AdminLogin";

export const metadata: Metadata = { title: "Équipe", robots: { index: false } };

/** The team signs in with Google once on this phone or computer: its own documents are then free. */
export default function Admin() {
  return <AdminLogin />;
}
