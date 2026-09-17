import type {
  CalendarView,
  EventStatus,
  Priority,
  WeatherAdvisory,
} from "./types";

export const CALENDAR_STORE_KEY = "agrowai.calendar.events";
export const CALENDAR_SELECTED_FARM_KEY = "agrowai.calendar.selectedFarm";

/** Upcoming window (days) — mirrors the backend default. */
export const UPCOMING_DAYS = 7;
export const WEATHER_ADVISORY_HORIZON_DAYS = 3;

export const calendarKeys = {
  all: ["calendar"] as const,
  farm: (farmId: string | null) =>
    ["calendar", "farm", farmId ?? "all"] as const,
  view: (farmId: string | null, view: CalendarView) =>
    ["calendar", "farm", farmId ?? "all", view] as const,
  summary: (farmId: string | null) =>
    ["calendar", "summary", farmId ?? "all"] as const,
};

export const CALENDAR_VIEWS: CalendarView[] = [
  "today",
  "upcoming",
  "timeline",
  "month",
  "completed",
];

/** View → i18n label key (under the `calendar` namespace). */
export const VIEW_LABEL_KEY: Record<CalendarView, string> = {
  today: "calendar.viewToday",
  upcoming: "calendar.viewUpcoming",
  timeline: "calendar.viewTimeline",
  month: "calendar.viewMonth",
  completed: "calendar.viewCompleted",
  missed: "calendar.viewMissed",
};

/** Priority → AgBadge tone. */
export const PRIORITY_TONE: Record<
  Priority,
  "neutral" | "info" | "warning" | "danger"
> = {
  low: "neutral",
  medium: "info",
  high: "warning",
};

export const PRIORITY_LABEL_KEY: Record<Priority, string> = {
  low: "calendar.priorityLow",
  medium: "calendar.priorityMedium",
  high: "calendar.priorityHigh",
};

export const STATUS_LABEL_KEY: Record<EventStatus, string> = {
  pending: "calendar.statusPending",
  done: "calendar.statusDone",
  skipped: "calendar.statusSkipped",
};

/** Weather advisory code → localized message key (reuses backend advisory codes). */
export const ADVISORY_LABEL_KEY: Record<WeatherAdvisory, string | null> = {
  none: null,
  delay_irrigation: "calendar.advDelayIrrigation",
  delay_spraying: "calendar.advDelaySpraying",
  recommend_irrigation: "calendar.advRecommendIrrigation",
};

export const SEASON_LABEL_KEY: Record<string, string> = {
  kharif: "calendar.seasonKharif",
  rabi: "calendar.seasonRabi",
  summer: "calendar.seasonSummer",
};

/**
 * Activity `code` → localized title/description keys. The backend sends the same
 * codes; the frontend owns the Tamil-first wording (docs: localized activity
 * codes). Missing codes fall back to the backend English title/description.
 */
export function activityTitleKey(code: string): string {
  return `calendar.activities.${code}.title`;
}

export function activityDescKey(code: string): string {
  return `calendar.activities.${code}.desc`;
}
