/**
 * Crop Calendar domain types (docs/API_CONTRACT.md → CROP CALENDAR).
 * Client-side camelCase mirror of the backend calendar schemas. Activities are
 * localized by `code` (Tamil-first); `title`/`description` are English fallback.
 */

export type Priority = "low" | "medium" | "high";
export type EventStatus = "pending" | "done" | "skipped";
export type WeatherDependency = "none" | "irrigation" | "spraying";
export type WeatherAdvisory =
  "none" | "delay_irrigation" | "delay_spraying" | "recommend_irrigation";
export type Season = "kharif" | "rabi" | "summer";

/**
 * "VERIFIED" -- an independent agronomist personally reviewed this exact
 * schedule for AgrowAI. "SOURCED_PUBLIC_REFERENCE" -- compiled from a real,
 * cited public agricultural source (TNAU/ICAR/KVK/etc.) but not personally
 * reviewed by an independent agronomist for AgrowAI (product decision,
 * 2026-08-17). Both are live/shown to farmers; the UI must label them
 * distinctly rather than implying a review that hasn't happened. `null`
 * means the event has no live registry backing (should not normally reach
 * the client -- both providers filter these out).
 */
export type RegistryVerificationStatus =
  "VERIFIED" | "SOURCED_PUBLIC_REFERENCE" | null;

export type CalendarView =
  "today" | "upcoming" | "timeline" | "month" | "completed" | "missed";

export interface CalendarEvent {
  id: string;
  farmId: string;
  crop: string | null;
  season: Season | null;
  code: string;
  activityType: string;
  title: string;
  description: string;
  scheduledDate: string; // YYYY-MM-DD
  dayOffset: number;
  growthStage: string;
  priority: Priority;
  status: EventStatus;
  weatherDependency: WeatherDependency;
  weatherAdvisory: WeatherAdvisory;
  reminderEnabled: boolean;
  reminderHour: number | null;
  completedAt: string | null;
  notes: string | null;
  registryVersion: string | null;
  registryVerificationStatus: RegistryVerificationStatus;
  registrySourceReference: string | null;
  isOrganic?: boolean;
  createdAt: string;
  dataState: "live" | "cached" | "stale";
  cachedAt: string | null;
}

export interface CalendarSummary {
  farmId: string;
  crop: string | null;
  season: Season | null;
  total: number;
  completed: number;
  pending: number;
  missed: number;
  skipped: number;
}

export interface GenerateCalendarInput {
  farmId: string;
  crop?: string | null;
  sowingDate?: string | null;
  irrigationType?: string | null;
  remindersEnabled?: boolean;
}

export interface UpdateEventInput {
  status?: EventStatus;
  reminderEnabled?: boolean;
  notes?: string | null;
}

// --------------------------------------------------------------------------- //
// Backend envelope shapes (snake_case).
// --------------------------------------------------------------------------- //
export interface ApiCalendarEvent {
  id: string;
  farm_id: string;
  crop: string | null;
  season: Season | null;
  code: string;
  activity_type: string;
  title: string;
  description: string;
  scheduled_date: string;
  day_offset: number;
  growth_stage: string;
  priority: Priority;
  status: EventStatus;
  weather_dependency: WeatherDependency;
  weather_advisory: WeatherAdvisory;
  reminder_enabled: boolean;
  reminder_hour: number | null;
  completed_at: string | null;
  notes: string | null;
  registry_version: string | null;
  registry_verification_status: RegistryVerificationStatus;
  registry_source_reference: string | null;
  is_organic?: boolean;
  created_at: string;
}

export interface ApiCalendarSummary {
  farm_id: string;
  crop: string | null;
  season: Season | null;
  total: number;
  completed: number;
  pending: number;
  missed: number;
  skipped: number;
}
