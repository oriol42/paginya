import { initialExam, type Exam } from "@/components/forms/ExamForm";

const DRAFT_KEY = "paginya:epreuve:draft"; // same key as FormShell (`paginya:${kind}:draft`)

/** Merges the headers read on each page: the first page that has a value wins. */
export function mergeExamFields(pages: (Record<string, string> | undefined)[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const page of pages) for (const [key, value] of Object.entries(page ?? {})) if (value && !out[key]) out[key] = value;
  return out;
}

/**
 * Hands scanned (or pasted) pages over to /epreuve: the form restores this local draft when it opens,
 * so the exam arrives already filled and already laid out. Returns false if the browser blocks storage.
 */
export function saveExamDraft(fields: Record<string, string>, content: string): boolean {
  try {
    const known = Object.keys(initialExam());
    const clean = Object.fromEntries(Object.entries(fields).filter(([k, v]) => known.includes(k) && typeof v === "string" && k !== "content"));
    const draft: Exam = { ...initialExam(), ...clean, content };
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
    localStorage.removeItem(`${DRAFT_KEY}:id`); // a new paper, not the order from last time
    return true;
  } catch {
    return false;
  }
}
