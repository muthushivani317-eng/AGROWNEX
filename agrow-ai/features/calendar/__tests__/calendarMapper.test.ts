import { apiToEvent, apiToSummary } from "../services/calendarMapper";
import type { ApiCalendarEvent, ApiCalendarSummary } from "../types";

const apiEvent: ApiCalendarEvent = {
  id: "e1",
  farm_id: "f1",
  crop: "paddy",
  season: "kharif",
  code: "irrigation_1",
  activity_type: "irrigation",
  title: "First irrigation",
  description: "Give a light irrigation.",
  scheduled_date: "2026-06-18",
  day_offset: 3,
  growth_stage: "seedling",
  priority: "high",
  status: "pending",
  weather_dependency: "irrigation",
  weather_advisory: "delay_irrigation",
  reminder_enabled: true,
  reminder_hour: 6,
  completed_at: null,
  notes: null,
  created_at: "2026-06-15T00:00:00Z",
  registry_version: "verified-1",
  registry_verification_status: "VERIFIED",
  registry_source_reference: "TEST-DOC",
};

describe("apiToEvent", () => {
  it("maps snake_case to camelCase", () => {
    const event = apiToEvent(apiEvent);
    expect(event.farmId).toBe("f1");
    expect(event.activityType).toBe("irrigation");
    expect(event.scheduledDate).toBe("2026-06-18");
    expect(event.dayOffset).toBe(3);
    expect(event.weatherAdvisory).toBe("delay_irrigation");
    expect(event.reminderHour).toBe(6);
    expect(event.registryVerificationStatus).toBe("VERIFIED");
    expect(event.registrySourceReference).toBe("TEST-DOC");
  });

  it("defaults a missing advisory to none", () => {
    const { weather_advisory, ...rest } = apiEvent;
    void weather_advisory;
    const event = apiToEvent(rest as ApiCalendarEvent);
    expect(event.weatherAdvisory).toBe("none");
  });
});

describe("apiToSummary", () => {
  it("maps the summary envelope", () => {
    const dto: ApiCalendarSummary = {
      farm_id: "f1",
      crop: "paddy",
      season: "kharif",
      total: 15,
      completed: 2,
      pending: 11,
      missed: 2,
      skipped: 0,
    };
    const summary = apiToSummary(dto);
    expect(summary.farmId).toBe("f1");
    expect(summary.total).toBe(15);
    expect(summary.missed).toBe(2);
  });
});
