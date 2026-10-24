import { initialLetter, type Letter } from "@/components/forms/LetterForm";

const DRAFT_KEY = "paginya:lettre:draft"; // same key as FormShell (`paginya:${kind}:draft`)

/**
 * Hands a letter typed elsewhere over to /lettre, already split into its fields (read by the server):
 * the form restores this draft when it opens. Empty fields keep the form's defaults. False if storage is blocked.
 */
export function saveLetterDraft(found: Partial<Letter>): boolean {
  try {
    const base = initialLetter();
    const pick = <T extends object>(def: T, got: Partial<T> | undefined): T =>
      ({ ...def, ...Object.fromEntries(Object.entries(got ?? {}).filter(([, v]) => v !== "" && v != null)) }) as T;
    const draft: Letter = {
      ...pick(base, { ...found, sender: undefined, recipient: undefined }),
      sender: pick(base.sender, found.sender),
      recipient: pick(base.recipient, found.recipient),
      attachments: found.attachments ?? [],
      bodyEdited: true,
    };
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
    localStorage.removeItem(`${DRAFT_KEY}:id`); // a new letter, not the order from last time
    return true;
  } catch {
    return false;
  }
}
