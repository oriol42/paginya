/** Documents opened on this phone, newest first: the import screen offers them instead of reopening the last one. */
export type Recent = { id: string; title: string; kind: string; pages: number; at: number };

const KEY = "propre:recents:v1";
const MAX = 8;

export function recents(): Recent[] {
  try {
    return (JSON.parse(localStorage.getItem(KEY) ?? "[]") as Recent[]).filter((r) => r && r.id);
  } catch {
    return [];
  }
}

export function remember(r: Omit<Recent, "at">): void {
  try {
    const list = [{ ...r, at: Date.now() }, ...recents().filter((x) => x.id !== r.id)].slice(0, MAX);
    localStorage.setItem(KEY, JSON.stringify(list));
  } catch { /* private mode */ }
}

export function forget(id: string): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(recents().filter((x) => x.id !== id)));
  } catch { /* ignore */ }
}
