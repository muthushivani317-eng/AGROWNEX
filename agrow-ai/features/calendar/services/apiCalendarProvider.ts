import { api } from "@/services/apiClient";
import { endpoints } from "@/services/endpoints";
import type { AxiosRequestConfig } from "axios";

import { UPCOMING_DAYS } from "../constants";
import type {
  ApiCalendarEvent,
  ApiCalendarSummary,
  CalendarEvent,
  CalendarSummary,
  CalendarView,
  GenerateCalendarInput,
  UpdateEventInput,
} from "../types";
import { apiToEvent, apiToSummary } from "./calendarMapper";
import { calendarStorage } from "./calendarStorage";
import { CalendarError, type CalendarProvider } from "./calendarProvider";

function normalizeCalendarError(error: unknown): never {
  const code =
    typeof error === "object" && error !== null
      ? String(
          (error as { errorCode?: unknown; code?: unknown }).errorCode ??
            (error as { code?: unknown }).code ??
            "",
        )
      : "";
  if (code === "STAGE_DATA_UNAVAILABLE") {
    throw new CalendarError(
      code,
      "Verified crop-stage information is not available.",
    );
  }
  throw error;
}

/** Live registry statuses -- see types.ts's RegistryVerificationStatus. */
const LIVE_REGISTRY_STATUSES = new Set(["VERIFIED", "SOURCED_PUBLIC_REFERENCE"]);
const noRetry = { _skipRetry: true } as AxiosRequestConfig;

function cachedForView(farmId: string, view: CalendarView): CalendarEvent[] {
  const events = calendarStorage
    .forFarm(farmId)
    .filter(
      (event) =>
        event.registryVerificationStatus != null &&
        LIVE_REGISTRY_STATUSES.has(event.registryVerificationStatus),
    );
  const today = new Date().toISOString().slice(0, 10);
  if (view === "today")
    return events.filter((event) => event.scheduledDate === today);
  if (view === "completed")
    return events.filter((event) => event.status === "done");
  if (view === "missed") {
    return events.filter(
      (event) => event.status === "pending" && event.scheduledDate < today,
    );
  }
  if (view === "upcoming") {
    const end = new Date(`${today}T00:00:00Z`);
    end.setUTCDate(end.getUTCDate() + UPCOMING_DAYS);
    const endIso = end.toISOString().slice(0, 10);
    return events.filter(
      (event) =>
        event.status === "pending" &&
        event.scheduledDate >= today &&
        event.scheduledDate <= endIso,
    );
  }
  return events;
}

/**
 * Backend calendar provider (docs/API_CONTRACT.md → CROP CALENDAR). Generation
 * and weather advisories are computed server-side; every fetch is mirrored to
 * MMKV so the calendar stays readable offline.
 */
function endpointForView(view: CalendarView): { url: string; days?: number } {
  switch (view) {
    case "today":
      return { url: endpoints.calendar.today };
    case "upcoming":
      return { url: endpoints.calendar.upcoming, days: UPCOMING_DAYS };
    case "completed":
      return { url: endpoints.calendar.completed };
    case "missed":
      return { url: endpoints.calendar.missed };
    case "timeline":
    case "month":
    default:
      return { url: endpoints.calendar.root };
  }
}

export const apiCalendarProvider: CalendarProvider = {
  async generate(input: GenerateCalendarInput): Promise<CalendarEvent[]> {
    try {
      const dto = await api.post<ApiCalendarEvent[]>(
        endpoints.calendar.generate,
        {
          farm_id: input.farmId,
          crop: input.crop,
          sowing_date: input.sowingDate,
          irrigation_type: input.irrigationType,
          reminders_enabled: input.remindersEnabled ?? true,
        },
        noRetry,
      );
      const events = dto.map(apiToEvent);
      calendarStorage.cacheFarm(input.farmId, events);
      return events;
    } catch (error) {
      normalizeCalendarError(error);
    }
  },

  async list(farmId: string, view: CalendarView): Promise<CalendarEvent[]> {
    const { url, days } = endpointForView(view);
    try {
      const dto = await api.get<ApiCalendarEvent[]>(url, {
        params: { farm_id: farmId, ...(days ? { days } : {}) },
      });
      const events = dto.map(apiToEvent);
      if (view === "timeline") calendarStorage.cacheFarm(farmId, events);
      else calendarStorage.mergeFarmCache(farmId, events);
      return events;
    } catch (error) {
      const cached = cachedForView(farmId, view);
      if (cached.length > 0) return cached;
      throw error;
    }
  },

  async summary(farmId: string): Promise<CalendarSummary> {
    const dto = await api.get<ApiCalendarSummary>(endpoints.calendar.summary, {
      params: { farm_id: farmId },
    });
    return apiToSummary(dto);
  },

  async updateEvent(
    id: string,
    patch: UpdateEventInput,
  ): Promise<CalendarEvent> {
    const dto = await api.put<ApiCalendarEvent>(endpoints.calendar.event(id), {
      status: patch.status,
      reminder_enabled: patch.reminderEnabled,
      notes: patch.notes,
    });
    const event = apiToEvent(dto);
    calendarStorage.update(id, patch, event.completedAt);
    return event;
  },
};
