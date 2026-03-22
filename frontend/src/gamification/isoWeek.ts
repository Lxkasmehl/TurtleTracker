/** ISO week key `YYYY-Www` (UTC), sufficient for weekly quest resets and streaks. */
export function getISOWeekKey(date: Date = new Date()): string {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return `${d.getUTCFullYear()}-W${String(weekNo).padStart(2, '0')}`;
}

/** Previous ISO week key (approximate, week-boundary safe for streak checks). */
export function previousISOWeekKey(weekKey: string): string | null {
  const m = weekKey.match(/^(\d{4})-W(\d{2})$/);
  if (!m) return null;
  let y = Number(m[1]);
  let w = Number(m[2]) - 1;
  if (w < 1) {
    y -= 1;
    w = 52;
  }
  return `${y}-W${String(w).padStart(2, '0')}`;
}

/** Count consecutive weeks ending at `currentWeek` present in `set`. */
export function consecutiveWeeksEndingAt(currentWeek: string, weeks: Set<string>): number {
  let n = 0;
  let cursor: string | null = currentWeek;
  while (cursor && weeks.has(cursor)) {
    n += 1;
    cursor = previousISOWeekKey(cursor);
  }
  return n;
}
