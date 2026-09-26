/** Public address of the site (search engines, share previews). Set NEXT_PUBLIC_SITE_URL when a real domain is bought. */
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "https://paginya.vercel.app").replace(/\/$/, "");
