import { appStorage } from "@/lib/storage";

import { CALENDAR_STORE_KEY } from "../constants";
import type { CalendarEvent, UpdateEventInput } from "../types";

/** Local calendar mirror in MMKV (local provider + offline cache + offline sync). */
function readAll(): CalendarEvent[] {
  return appStorage.getJSON<CalendarEvent[]>(CALENDAR_STORE_KEY) ?? [];
}

function writeAll(list: CalendarEvent[]): void {
  appStorage.setJSON(CALENDAR_STORE_KEY, list);
}

function sortByDate(list: CalendarEvent[]): CalendarEvent[] {
  return [...list].sort(
    (a, b) =>
      a.scheduledDate.localeCompare(b.scheduledDate) ||
      a.dayOffset - b.dayOffset,
  );
}

export const calendarStorage = {
  all(): CalendarEvent[] {
    return sortByDate(readAll());
  },

  forFarm(farmId: string): CalendarEvent[] {
    return sortByDate(readAll().filter((e) => e.farmId === farmId));
  },

  get(id: string): CalendarEvent | null {
    return readAll().find((e) => e.id === id) ?? null;
  },

  /** Replace a farm's *pending* plan with a freshly generated one, keeping history. */
  replaceFarmPlan(farmId: string, events: CalendarEvent[]): void {
    const kept = readAll().filter(
      (e) => e.farmId !== farmId || e.status !== "pending",
    );
    writeAll([...kept, ...events]);
  },

  /** Overwrite the cache for a farm (used when caching an API fetch). */
  cacheFarm(
    farmId: string,
    events: CalendarEvent[],
    cachedAt: string = new Date().toISOString(),
  ): void {
    const others = readAll().filter((e) => e.farmId !== farmId);
    const cached = events.map((event) => ({
      ...event,
      dataState: "cached" as const,
      cachedAt,
    }));
    writeAll([...others, ...cached]);
  },

  mergeFarmCache(
    farmId: string,
    events: CalendarEvent[],
    cachedAt: string = new Date().toISOString(),
  ): void {
    const list = readAll();
    const incomingIds = new Set(events.map((event) => event.id));
    const kept = list.filter(
      (event) => event.farmId !== farmId || !incomingIds.has(event.id),
    );
    const cached = events.map((event) => ({
      ...event,
      dataState: "cached" as const,
      cachedAt,
    }));
    writeAll([...kept, ...cached]);
  },

  update(
    id: string,
    patch: UpdateEventInput,
    completedAt: string | null,
  ): CalendarEvent | null {
    const list = readAll();
    const index = list.findIndex((e) => e.id === id);
    if (index < 0) return null;
    const current = list[index];
    const updated: CalendarEvent = {
      ...current,
      status: patch.status ?? current.status,
      reminderEnabled: patch.reminderEnabled ?? current.reminderEnabled,
      notes: patch.notes !== undefined ? patch.notes : current.notes,
      completedAt:
        patch.status === "done"
          ? completedAt
          : patch.status
            ? null
            : current.completedAt,
    };
    list[index] = updated;
    writeAll(list);
    return updated;
  },

  clear(): void {
    appStorage.remove(CALENDAR_STORE_KEY);
  },
};
