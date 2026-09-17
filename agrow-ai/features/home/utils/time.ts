import type { RelativeTime } from '../types';

/** Locale-neutral clock "HH:mm". */
export function formatClock(now: Date = new Date()): string {
  const h = `${now.getHours()}`.padStart(2, '0');
  const m = `${now.getMinutes()}`.padStart(2, '0');
  return `${h}:${m}`;
}

/**
 * Relative time as an i18n key (+ params). Tamil-first: the actual wording lives
 * in the `home.time*` translations, this only decides the bucket.
 */
export function relativeTimeKey(
  iso: string | null,
  now: number = Date.now(),
): RelativeTime {
  if (!iso) return { key: 'home.timeUnknown' };
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return { key: 'home.timeUnknown' };

  const minutes = Math.floor(Math.max(0, now - then) / 60000);
  if (minutes < 1) return { key: 'home.timeJustNow' };
  if (minutes < 60) return { key: 'home.timeMinutesAgo', params: { n: minutes } };

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return { key: 'home.timeHoursAgo', params: { n: hours } };

  const days = Math.floor(hours / 24);
  if (days === 1) return { key: 'home.timeYesterday' };
  if (days < 7) return { key: 'home.timeDaysAgo', params: { n: days } };

  const weeks = Math.floor(days / 7);
  if (weeks < 5) return { key: 'home.timeWeeksAgo', params: { n: weeks } };

  return { key: 'home.timeMonthsAgo', params: { n: Math.floor(days / 30) } };
}
