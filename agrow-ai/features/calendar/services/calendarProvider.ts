import { isBackendConfigured } from "@/config/env";
import { logger } from "@/lib/logger";

import type {
  CalendarEvent,
  CalendarSummary,
  CalendarView,
  GenerateCalendarInput,
  UpdateEventInput,
} from "../types";

/**
 * Crop Calendar data source contract. Backed by the deterministic AgrowAI
 * calendar API when configured, otherwise a local, offline provider that
 * generates the same schedule client-side (mirrors the app's swappable
 * providers). Designed so future AI scheduling can replace the backend
 * generation without any frontend change.
 */
export interface CalendarProvider {
  generate(input: GenerateCalendarInput): Promise<CalendarEvent[]>;
  list(farmId: string, view: CalendarView): Promise<CalendarEvent[]>;
  summary(farmId: string): Promise<CalendarSummary>;
  updateEvent(id: string, patch: UpdateEventInput): Promise<CalendarEvent>;
}

export class CalendarError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "CalendarError";
  }
}

let provider: CalendarProvider | null = null;

export function getCalendarProvider(): CalendarProvider {
  if (provider) return provider;
  if (isBackendConfigured) {
    provider = require("./apiCalendarProvider")
      .apiCalendarProvider as CalendarProvider;
    logger.info("calendar", "using api provider");
  } else {
    provider = require("./localCalendarProvider")
      .localCalendarProvider as CalendarProvider;
    logger.info("calendar", "using local provider");
  }
  return provider;
}
