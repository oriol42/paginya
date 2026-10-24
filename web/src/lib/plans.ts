/** Paginya's offers (perDay 0 = unlimited) (the server computes the real amounts: see api/app/pricing.py). */
export const DOC_PRICE = 550;

export const PLANS = {
  essentiel: { name: "Essentiel", price: 3000, perDay: 10, who: "Étudiants, enseignants, particuliers" },
  pro: { name: "Pro", price: 5000, perDay: 0, who: "Imprimeries, secrétariats, entreprises" },
} as const;

export type Plan = keyof typeof PLANS;

export const perDayText = (n: number) => (n ? `${n} documents par jour` : "Documents illimités");
