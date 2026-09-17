import type { NotificationItem } from '../types';

const PRIORITY_ORDER: Record<string, number> = {
  critical: 3,
  high: 2,
  medium: 1,
  low: 0,
};

const SEVERITY_ORDER: Record<string, number> = {
  critical: 2,
  warning: 1,
  info: 0,
};

export function isValidActionRoute(route: string | null): route is string {
  return typeof route === 'string' && route.length > 0 && !/\{[^}]+\}/.test(route);
}

/** Pick the single most urgent item: priority, then severity, then newest,
 * then id as a final stable tiebreaker. Pure and unit-testable. */
export function selectTopPriority(
  items: NotificationItem[],
): NotificationItem | null {
  if (!items.length) return null;
  return [...items].sort((a, b) => {
    const priority =
      (PRIORITY_ORDER[b.priority] ?? 0) -
      (PRIORITY_ORDER[a.priority] ?? 0);
    if (priority !== 0) return priority;
    const severity =
      (SEVERITY_ORDER[b.severity] ?? 0) -
      (SEVERITY_ORDER[a.severity] ?? 0);
    if (severity !== 0) return severity;
    const timestamp = b.createdAt.localeCompare(a.createdAt);
    if (timestamp !== 0) return timestamp;
    return a.id.localeCompare(b.id);
  })[0];
}
