/** Produce formatting helpers (rupees, quantity, relative harvest countdown). */

/** Format a rupee amount with Indian digit grouping, e.g. `₹41,000`. */
export function formatRupees(value: number): string {
  const rounded = Math.round(value);
  try {
    return `₹${rounded.toLocaleString('en-IN')}`;
  } catch {
    return `₹${rounded}`;
  }
}

/** Format a quantity with its unit label, trimming trailing zeros. */
export function formatQuantity(quantity: number, unitLabel: string): string {
  const n = Number.isInteger(quantity) ? String(quantity) : String(quantity);
  return `${n} ${unitLabel}`;
}

/**
 * Relative harvest-countdown label key + count for i18n. Returns a code the
 * screen maps to a localized string (Tamil-first) rather than English here.
 */
export function harvestCountdown(
  daysToHarvest: number,
): { key: 'today' | 'tomorrow' | 'inDays' | 'overdue'; days: number } {
  if (daysToHarvest < 0) return { key: 'overdue', days: Math.abs(daysToHarvest) };
  if (daysToHarvest === 0) return { key: 'today', days: 0 };
  if (daysToHarvest === 1) return { key: 'tomorrow', days: 1 };
  return { key: 'inDays', days: daysToHarvest };
}
