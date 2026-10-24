import { API_URL } from "./api";

/**
 * Visitor funnel: where people stop between the ad and the payment.
 * Each step goes to our server (counted once per visitor) and to the Meta Pixel, so the ads can look for buyers.
 */
export type Step =
  | "visit" | "open_document" | "open_garde" | "open_lettre" | "open_epreuve" | "open_convertir"
  | "upload" | "pay_open" | "pay_start" | "paid";

type Fbq = (...args: unknown[]) => void;

const SID_KEY = "paginya:sid";
const SRC_KEY = "paginya:src";

/** Meta's standard events, the ones its ads can optimise for. */
const PIXEL: Partial<Record<Step, string>> = {
  open_document: "ViewContent", open_garde: "ViewContent", open_lettre: "ViewContent", open_epreuve: "ViewContent", open_convertir: "ViewContent",
  upload: "Lead", pay_open: "InitiateCheckout", pay_start: "AddPaymentInfo", paid: "Purchase",
};

function sid(): string {
  try {
    let id = localStorage.getItem(SID_KEY);
    if (!id) {
      id = Array.from(crypto.getRandomValues(new Uint8Array(12)), (b) => b.toString(16).padStart(2, "0")).join("");
      localStorage.setItem(SID_KEY, id);
    }
    return id;
  } catch {
    return "";
  }
}

/** Where the visitor came from, decided on the landing page and kept for the next steps. */
function source(): string {
  const q = new URLSearchParams(window.location.search);
  let src = q.get("utm_source")
    ?? (q.has("fbclid") ? "facebook" : q.has("ttclid") ? "tiktok" : q.has("gclid") ? "google" : null);
  if (!src && document.referrer && !document.referrer.startsWith(window.location.origin)) {
    const host = new URL(document.referrer).hostname;
    src = /facebook|fb\.|messenger/.test(host) ? "facebook" : /instagram/.test(host) ? "instagram" : /tiktok/.test(host) ? "tiktok"
      : /google/.test(host) ? "google" : /whatsapp|wa\.me/.test(host) ? "whatsapp" : host;
  }
  try {
    if (src) localStorage.setItem(SRC_KEY, src);
    return src ?? localStorage.getItem(SRC_KEY) ?? "direct";
  } catch {
    return src ?? "direct";
  }
}

export function track(step: Step, value?: number) {
  if (typeof window === "undefined") return;
  const id = sid();
  if (id) {
    const body = JSON.stringify({ sid: id, step, src: source() });
    // text/plain: no CORS preflight, and the beacon survives the page being closed
    if (!navigator.sendBeacon?.(`${API_URL}/events`, body)) {
      fetch(`${API_URL}/events`, { method: "POST", body, keepalive: true }).catch(() => {});
    }
  }
  const fbq = (window as unknown as { fbq?: Fbq }).fbq;
  const event = PIXEL[step];
  if (fbq && event) fbq("track", event, value ? { value, currency: "XAF" } : undefined);
}
