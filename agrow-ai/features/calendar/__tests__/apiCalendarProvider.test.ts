jest.mock("@/services/apiClient", () => ({
  api: { get: jest.fn(), post: jest.fn(), put: jest.fn() },
}));

import { api } from "@/services/apiClient";
import { apiCalendarProvider } from "../services/apiCalendarProvider";
import { calendarStorage } from "../services/calendarStorage";
import type { CalendarEvent } from "../types";

const cached: CalendarEvent = {
  id: "cached-1",
  farmId: "farm-1",
  crop: "paddy",
  season: "kharif",
  code: "observe",
  activityType: "monitoring",
  title: "calendar.verified.observe.title",
  description: "calendar.verified.observe.description",
  scheduledDate: "2026-08-15",
  dayOffset: 1,
  growthStage: "stage",
  priority: "medium",
  status: "pending",
  weatherDependency: "none",
  weatherAdvisory: "none",
  reminderEnabled: false,
  reminderHour: null,
  completedAt: null,
  notes: null,
  registryVersion: "v1",
  registryVerificationStatus: "VERIFIED",
  registrySourceReference: "DOC-1",
  createdAt: "2026-08-14T00:00:00Z",
  dataState: "live",
  cachedAt: null,
};

describe("apiCalendarProvider offline cache safety", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    calendarStorage.clear();
  });

  it("returns visibly cached data when the network fails", async () => {
    calendarStorage.cacheFarm("farm-1", [cached], "2026-08-14T01:00:00Z");
    (api.get as jest.Mock).mockRejectedValue(new Error("offline"));
    const result = await apiCalendarProvider.list("farm-1", "timeline");
    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      dataState: "cached",
      cachedAt: "2026-08-14T01:00:00Z",
    });
  });

  it("does not fabricate an empty success when offline without cache", async () => {
    (api.get as jest.Mock).mockRejectedValue(new Error("offline"));
    await expect(
      apiCalendarProvider.list("farm-1", "timeline"),
    ).rejects.toThrow("offline");
  });

  it("normalizes the backend no-verified-rule code for the screen", async () => {
    (api.post as jest.Mock).mockRejectedValue({
      errorCode: "STAGE_DATA_UNAVAILABLE",
    });
    await expect(
      apiCalendarProvider.generate({
        farmId: "farm-1",
        crop: "paddy",
        sowingDate: "2026-08-01",
      }),
    ).rejects.toMatchObject({ code: "STAGE_DATA_UNAVAILABLE" });
  });

  it("does not replay calendar generation after a deterministic server failure", async () => {
    (api.post as jest.Mock).mockRejectedValue(new Error("server failure"));

    await expect(
      apiCalendarProvider.generate({
        farmId: "farm-1",
        crop: "paddy",
        sowingDate: "2026-08-01",
      }),
    ).rejects.toThrow("server failure");

    expect(api.post).toHaveBeenCalledWith(
      expect.any(String),
      expect.any(Object),
      expect.objectContaining({ _skipRetry: true }),
    );
  });

  it("mirrors every successful view for later offline use", async () => {
    const dto = {
      id: cached.id,
      farm_id: cached.farmId,
      crop: cached.crop,
      season: cached.season,
      code: cached.code,
      activity_type: cached.activityType,
      title: cached.title,
      description: cached.description,
      scheduled_date: cached.scheduledDate,
      day_offset: cached.dayOffset,
      growth_stage: cached.growthStage,
      priority: cached.priority,
      status: cached.status,
      weather_dependency: cached.weatherDependency,
      weather_advisory: cached.weatherAdvisory,
      reminder_enabled: cached.reminderEnabled,
      reminder_hour: cached.reminderHour,
      completed_at: cached.completedAt,
      notes: cached.notes,
      registry_version: cached.registryVersion,
      registry_verification_status: cached.registryVerificationStatus,
      registry_source_reference: cached.registrySourceReference,
      created_at: cached.createdAt,
    };
    (api.get as jest.Mock).mockResolvedValue([dto]);
    await apiCalendarProvider.list("farm-1", "today");
    expect(calendarStorage.forFarm("farm-1")).toHaveLength(1);
  });
});
