/** Scheme formatting helpers (deadline countdown as an i18n key + count). */

export type DeadlineKey =
  | 'none'
  | 'today'
  | 'tomorrow'
  | 'daysLeft'
  | 'closed';

/**
 * Relative deadline label key + day count for i18n. Returns a code the screen
 * maps to a localized string (Tamil-first) rather than English text here.
 */
export function deadlineInfo(
  lastDate: string | null,
  now = new Date(),
): { key: DeadlineKey; days: number } {
  if (!lastDate) return { key: 'none', days: 0 };
  const end = new Date(lastDate);
  if (Number.isNaN(end.getTime())) return { key: 'none', days: 0 };
  const startOfDay = (d: Date) =>
    new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((startOfDay(end) - startOfDay(now)) / 86_400_000);
  if (days < 0) return { key: 'closed', days: 0 };
  if (days === 0) return { key: 'today', days: 0 };
  if (days === 1) return { key: 'tomorrow', days: 1 };
  return { key: 'daysLeft', days };
}

/** Is the deadline within the "closing soon" window (<= 7 days)? */
export function isClosingSoon(lastDate: string | null, now = new Date()): boolean {
  const info = deadlineInfo(lastDate, now);
  return (
    info.key === 'today' ||
    info.key === 'tomorrow' ||
    (info.key === 'daysLeft' && info.days <= 7)
  );
}
