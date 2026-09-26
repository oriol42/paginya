import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

export const dynamic = "force-static";

const PAGES = ["", "garde", "document", "lettre", "epreuve", "tarifs", "cgu", "confidentialite", "mentions-legales"];

export default function sitemap(): MetadataRoute.Sitemap {
  return PAGES.map((p) => ({ url: p ? `${SITE_URL}/${p}/` : `${SITE_URL}/`, changeFrequency: "weekly", priority: p ? 0.7 : 1 }));
}
