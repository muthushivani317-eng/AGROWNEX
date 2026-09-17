import type {
  CalendarEvent,
  CalendarSummary,
  CalendarView,
  GenerateCalendarInput,
  UpdateEventInput,
} from "../types";
import { UPCOMING_DAYS } from "../constants";
import { calendarStorage } from "./calendarStorage";
import { generateEvents } from "./calendarGenerator";
import { CalendarError, type CalendarProvider } from "./calendarProvider";

/**
 * Offline calendar provider. Generates the deterministic schedule client-side
 * and persists it in MMKV, so the calendar, offline completion and history all
 * work in development without a backend (mirrors the backend generation).
 */
function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function shiftIso(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

const LIVE_REGISTRY_STATUSES = new Set([
  "VERIFIED",
  "SOURCED_PUBLIC_REFERENCE",
]);

function hasLiveSchedule(event: CalendarEvent): boolean {
  return (
    event.registryVerificationStatus != null &&
    LIVE_REGISTRY_STATUSES.has(event.registryVerificationStatus)
  );
}

function filterByView(
  events: CalendarEvent[],
  view: CalendarView,
): CalendarEvent[] {
  const today = todayIso();
  switch (view) {
    case "today":
      return events.filter((e) => e.scheduledDate === today);
    case "upcoming":
      return events.filter(
        (e) =>
          e.status === "pending" &&
          e.scheduledDate >= today &&
          e.scheduledDate <= shiftIso(today, UPCOMING_DAYS),
      );
    case "completed":
      return events.filter((e) => e.status === "done");
    case "missed":
      return events.filter(
        (e) => e.status === "pending" && e.scheduledDate < today,
      );
    case "timeline":
    case "month":
    default:
      return events;
  }
}

export const localCalendarProvider: CalendarProvider = {
  async generate(input: GenerateCalendarInput): Promise<CalendarEvent[]> {
    if (!input.sowingDate) {
      throw new CalendarError(
        "sowing_date_required",
        "Set the crop and sowing date for this farm before generating a calendar.",
      );
    }
    const events = generateEvents(
      { ...input, sowingDate: input.sowingDate },
      new Date().toISOString(),
    );
    if (events.length === 0) {
      throw new CalendarError(
        "STAGE_DATA_UNAVAILABLE",
        "Verified crop-stage information is not available.",
      );
    }
    calendarStorage.replaceFarmPlan(input.farmId, events);
    return calendarStorage.forFarm(input.farmId);
  },

  async list(farmId: string, view: CalendarView): Promise<CalendarEvent[]> {
    const verified = calendarStorage
      .forFarm(farmId)
      .filter(hasLiveSchedule);
    return filterByView(verified, view);
  },

  async summary(farmId: string): Promise<CalendarSummary> {
    const events = calendarStorage
      .forFarm(farmId)
      .filter(hasLiveSchedule);
    const today = todayIso();
    const count = (fn: (e: CalendarEvent) => boolean) =>
      events.filter(fn).length;
    return {
      farmId,
      crop: events[0]?.crop ?? null,
      season: events[0]?.season ?? null,
      total: events.length,
      completed: count((e) => e.status === "done"),
      pending: count((e) => e.status === "pending"),
      missed: count((e) => e.status === "pending" && e.scheduledDate < today),
      skipped: count((e) => e.status === "skipped"),
    };
  },

  async updateEvent(
    id: string,
    patch: UpdateEventInput,
  ): Promise<CalendarEvent> {
    const updated = calendarStorage.update(id, patch, new Date().toISOString());
    if (!updated) throw new CalendarError("not_found", "Activity not found");
    return updated;
  },
};
