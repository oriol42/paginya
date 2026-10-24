/** Customer account (Google sign-in): holds the 30-day pass, or the team's free access. The token stays in this browser. */
import { api, type Account } from "./api";

export type { Account };

const KEY = "propre:account";

export function savedAccount(): Account | null {
  try { return JSON.parse(localStorage.getItem(KEY) ?? "null"); } catch { return null; }
}

export function keepAccount(a: Account | null) {
  try {
    if (a) localStorage.setItem(KEY, JSON.stringify(a));
    else localStorage.removeItem(KEY);
  } catch { /* storage blocked: the account lasts for this visit */ }
}

/** Fresh pass state from the server; a dead token signs the browser out. */
export async function refreshAccount(): Promise<Account | null> {
  const a = savedAccount();
  if (!a) return null;
  try {
    const fresh = { ...(await api.accountMe(a.token)), token: a.token };
    keepAccount(fresh);
    return fresh;
  } catch (e) {
    if ((e as Error & { status?: number }).status === 401) keepAccount(null);
    return a;
  }
}

export const hasPass = (a: Account | null) => !!a && a.pass_until * 1000 > Date.now();

/** Downloads are free for a team account, or with an active pass while today's documents are not used up. */
export const canUnlock = (a: Account | null) => !!a && (a.team || (hasPass(a) && (a.used_today ?? 0) < (a.per_day || Infinity)));
