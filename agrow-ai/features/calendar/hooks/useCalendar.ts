import { useMutation, useQuery } from "@tanstack/react-query";

import { queryClient } from "@/lib/queryClient";
import { offlineQueue } from "@/lib/db";
import { logger } from "@/lib/logger";
import { endpoints } from "@/services/endpoints";
import { uuid } from "@/utils/id";
import { ApiError } from "@/types";

import { calendarKeys } from "../constants";
import { getCalendarProvider } from "../services/calendarProvider";
import { calendarStorage } from "../services/calendarStorage";
import type {
  CalendarView,
  GenerateCalendarInput,
  UpdateEventInput,
} from "../types";

/** Activities for one farm + view (timeline, today, upcoming, completed, missed). */
export function useCalendarView(farmId: string | null, view: CalendarView) {
  return useQuery({
    queryKey: calendarKeys.view(farmId, view),
    enabled: Boolean(farmId),
    queryFn: () => getCalendarProvider().list(farmId as string, view),
  });
}

/** Progress roll-up for a farm (drives the progress indicators). */
export function useCalendarSummary(farmId: string | null) {
  return useQuery({
    queryKey: calendarKeys.summary(farmId),
    enabled: Boolean(farmId),
    queryFn: () => getCalendarProvider().summary(farmId as string),
  });
}

/** Deterministically (re)generate a farm's calendar. */
export function useGenerateCalendar() {
  return useMutation({
    mutationFn: (input: GenerateCalendarInput) =>
      getCalendarProvider().generate(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: calendarKeys.all });
    },
  });
}

/**
 * Complete/update an activity. Works offline: if the request fails, the change
 * is applied to the local mirror and queued in the offline outbox to sync later
 * (docs: offline task completion, existing outbox pattern).
 */
export function useUpdateEvent() {
  return useMutation({
    mutationFn: async ({
      id,
      patch,
    }: {
      id: string;
      patch: UpdateEventInput;
    }) => {
      try {
        return await getCalendarProvider().updateEvent(id, patch);
      } catch (err) {
        if (!(err instanceof ApiError) || !err.isNetwork) throw err;
        logger.info("calendar", "update failed, queueing offline");
        await offlineQueue.enqueue({
          id: `calendar-${id}-${uuid()}`,
          endpoint: endpoints.calendar.event(id),
          method: "PUT",
          payload: {
            status: patch.status,
            reminder_enabled: patch.reminderEnabled,
            notes: patch.notes,
          },
          entityType: "calendar_event",
        });
        const optimistic = calendarStorage.update(
          id,
          patch,
          new Date().toISOString(),
        );
        if (optimistic) return optimistic;
        throw err;
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: calendarKeys.all });
    },
  });
}
