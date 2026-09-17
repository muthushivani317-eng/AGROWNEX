import { localCalendarProvider } from "../services/localCalendarProvider";
import { calendarStorage } from "../services/calendarStorage";
import { CalendarError } from "../services/calendarProvider";
import type { CalendarEvent } from "../types";

describe("localCalendarProvider verified-data boundary", () => {
  beforeEach(() => calendarStorage.clear());

  it("requires a planting date before checking the registry", async () => {
    await expect(
      localCalendarProvider.generate({ farmId: "farm-1", crop: "wheat" }),
    ).rejects.toMatchObject({ code: "sowing_date_required" });
  });

  it("does not generate, persist, or notify from legacy schedules", async () => {
    const request = localCalendarProvider.generate({
      farmId: "farm-1",
      crop: "paddy",
      sowingDate: "2026-08-01",
    });
    await expect(request).rejects.toBeInstanceOf(CalendarError);
    await expect(
      localCalendarProvider.generate({
        farmId: "farm-1",
        crop: "paddy",
        sowingDate: "2026-08-01",
      }),
    ).rejects.toMatchObject({ code: "STAGE_DATA_UNAVAILABLE" });
    expect(calendarStorage.forFarm("farm-1")).toEqual([]);
  });

  it("still supports manually stored event history", async () => {
    expect(await localCalendarProvider.list("farm-1", "timeline")).toEqual([]);
    expect((await localCalendarProvider.summary("farm-1")).total).toBe(0);
  });

  it("keeps sourced public-reference events visible offline", async () => {
    const event = {
      id: "sugarcane-1",
      farmId: "farm-1",
      crop: "sugarcane",
      season: "kharif",
      code: "inspect_crop",
      activityType: "inspection",
      title: "Inspect crop",
      description: "Inspect the field",
      scheduledDate: "2026-08-25",
      dayOffset: 5,
      growthStage: "establishment",
      priority: "medium",
      status: "pending",
      weatherDependency: "none",
      weatherAdvisory: "none",
      reminderEnabled: false,
      reminderHour: null,
      completedAt: null,
      notes: null,
      registryVersion: "1",
      registryVerificationStatus: "SOURCED_PUBLIC_REFERENCE",
      registrySourceReference: "TNAU",
      createdAt: "2026-08-20T00:00:00Z",
      dataState: "live",
      cachedAt: null,
    } satisfies CalendarEvent;
    calendarStorage.cacheFarm("farm-1", [event]);

    expect(await localCalendarProvider.list("farm-1", "timeline")).toHaveLength(1);
    expect((await localCalendarProvider.summary("farm-1")).total).toBe(1);
  });
});
