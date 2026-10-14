/** Current academic year, "2026-2027": it starts in September, so January to August still belong to the previous one. */
export function academicYear(now = new Date()): string {
  const start = now.getMonth() >= 8 ? now.getFullYear() : now.getFullYear() - 1;
  return `${start}-${start + 1}`;
}
