/** Market formatting helpers (Indian rupee grouping + relative "updated" time). */

/** Format a rupee amount with Indian digit grouping, e.g. `₹2,050`. */
export function formatRupees(value: number): string {
  const rounded = Math.round(value);
  try {
    return `₹${rounded.toLocaleString('en-IN')}`;
  } catch {
    return `₹${rounded}`;
  }
}

/**
 * Relative "updated" label key + count for i18n. Returns a code the screen maps
 * to a localized string (Tamil-first) rather than English text here.
 */
export function updatedAgo(
  isoDate: string,
  now = new Date(),
): { key: 'today' | 'yesterday' | 'daysAgo'; days: number } {
  const then = new Date(isoDate);
  const startOfDay = (d: Date) =>
    new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((startOfDay(now) - startOfDay(then)) / 86_400_000);
  if (days <= 0) return { key: 'today', days: 0 };
  if (days === 1) return { key: 'yesterday', days: 1 };
  return { key: 'daysAgo', days };
}
