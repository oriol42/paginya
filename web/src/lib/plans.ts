/** Paginya's offers (perDay 0 = unlimited) (the server computes the real amounts: see api/app/pricing.py). */
export const DOC_PRICE = 100;

/** Essentiel is no longer sold (22/11/2026) but the passes already bought keep working: it stays here to show them. */
export const PLANS = {
  essentiel: { name: "Essentiel", price: 3000, perDay: 10, who: "Étudiants, enseignants, particuliers" },
  pro: { name: "Pro", price: 2000, perDay: 0, who: "Entreprises, imprimeries, secrétariats" },
} as const;

export type Plan = keyof typeof PLANS;

/** The passes that can still be bought. */
export const SOLD_PLANS: Plan[] = ["pro"];

export const perDayText = (n: number) => (n ? `${n} documents par jour` : "Documents illimités");

/** « Environ 67 F par jour » for a 30-day pass. */
export const perDayCost = (price: number) => `Environ ${Math.round(price / 30)} F par jour`;
