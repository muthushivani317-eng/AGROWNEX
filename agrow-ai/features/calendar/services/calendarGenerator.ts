import { uuid } from "@/utils/id";

import type { CalendarEvent, GenerateCalendarInput, Season } from "../types";
import { getSchedule } from "./schedules";

/**
 * Deterministic client-side calendar generation for the local/dev provider.
 * Mirrors `backend/app/modules/calendar/generator.py` (no AI). Pure and tested.
 */
const RAINFED = new Set(["rainfed", "rain-fed", "rain fed", "none"]);

function addDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export function deriveSeason(sowingDate: string): Season {
  const month = new Date(`${sowingDate}T00:00:00Z`).getUTCMonth() + 1;
  if (month >= 6 && month <= 9) return "kharif";
  if (month >= 10 || month === 1) return "rabi";
  return "summer";
}

function isRainfed(irrigationType?: string | null): boolean {
  return !!irrigationType && RAINFED.has(irrigationType.trim().toLowerCase());
}

export function generateEvents(
  input: GenerateCalendarInput & { sowingDate: string },
  nowIso: string,
): CalendarEvent[] {
  const { farmId, crop = null, sowingDate, irrigationType } = input;
  const remindersEnabled = input.remindersEnabled ?? true;
  const rainfed = isRainfed(irrigationType);
  const season = deriveSeason(sowingDate);

  const events = getSchedule(crop).map((tmpl) => {
    const irrigationTask = tmpl.weatherDependency === "irrigation";
    const priority = rainfed && irrigationTask ? "low" : tmpl.priority;
    const reminder =
      (rainfed && irrigationTask ? false : tmpl.reminderEnabled) &&
      remindersEnabled;
    return {
      id: uuid(),
      farmId,
      crop,
      season,
      code: tmpl.code,
      activityType: tmpl.activityType,
      title: tmpl.title,
      description: tmpl.description,
      scheduledDate: addDays(sowingDate, tmpl.dayOffset),
      dayOffset: tmpl.dayOffset,
      growthStage: tmpl.growthStage,
      priority,
      status: "pending" as const,
      weatherDependency: tmpl.weatherDependency,
      weatherAdvisory: "none" as const,
      reminderEnabled: reminder,
      reminderHour: reminder ? 6 : null,
      completedAt: null,
      notes: null,
      registryVersion: null,
      registryVerificationStatus: null,
      registrySourceReference: null,
      createdAt: nowIso,
      dataState: "live" as const,
      cachedAt: null,
    };
  });

  events.sort(
    (a, b) =>
      a.scheduledDate.localeCompare(b.scheduledDate) ||
      a.dayOffset - b.dayOffset,
  );
  return events;
}
