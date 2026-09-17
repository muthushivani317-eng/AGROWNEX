/** Home Dashboard domain types. */

export type TaskIcon =
  | 'irrigate'
  | 'inspect'
  | 'spray'
  | 'weed'
  | 'fertilizer'
  | 'drainage'
  | 'heat';

export type TaskTone = 'primary' | 'warning' | 'danger' | 'info';

/** A rule-based task suggestion for today (deterministic; localized by key). */
export interface DashboardTask {
  id: string;
  labelKey: string;
  icon: TaskIcon;
  tone: TaskTone;
}

export type ActivityKind = 'farm' | 'profile' | 'weather';

/** A recent-activity entry derived from real data (no fabricated events). */
export interface ActivityItem {
  id: string;
  kind: ActivityKind;
  titleKey: string;
  params?: Record<string, string | number>;
  /** Raw insight category (weather activity only) for localized labels. */
  category?: string;
  timestamp: string | null;
}

/** Relative-time result: an i18n key plus optional interpolation params. */
export interface RelativeTime {
  key: string;
  params?: Record<string, number>;
}
