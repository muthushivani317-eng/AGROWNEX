import type { AuthUser } from "@/features/auth";
import type { FarmSummary } from "@/features/farm";
import type { WeatherBundle } from "@/features/weather";

import { buildRecentActivity } from "../utils/activity";

function farm(id: string, name: string, updatedAt: string): FarmSummary {
  return {
    id,
    name,
    crop: "paddy",
    status: "active",
    areaHectares: 1,
    district: "madurai",
    hasBoundary: false,
    centroidLat: null,
    centroidLng: null,
    latitude: 9.9,
    longitude: 78.1,
    imageCount: 0,
    updatedAt,
    syncStatus: "synced",
  };
}

const user = {
  id: "u1",
  name: "Muthu",
  profileCompleted: true,
  createdAt: "2026-07-01T00:00:00Z",
} as AuthUser;

function weatherWithAlert(): WeatherBundle {
  return {
    location: { latitude: 0, longitude: 0, timezone: null, name: null },
    current: {} as WeatherBundle["current"],
    hourly: [],
    daily: [],
    insights: [
      {
        code: "heavy_rain.severe",
        category: "heavy_rain",
        severity: "critical",
        title: "",
        message: "",
        params: {},
      },
    ],
    mission: {
      primaryAction: "Protect fields from heavy rain",
      reason: "",
      avoid: null,
      secondaryActions: [],
      confidenceNote: "",
      sourceInsightCode: "heavy_rain.severe",
      crop: null,
    },
    fetchedAt: "2026-07-10T08:00:00Z",
    source: "test",
  };
}

describe("buildRecentActivity", () => {
  it("lists recent farms newest-first and includes profile setup", () => {
    const items = buildRecentActivity(
      [
        farm("a", "Old", "2026-07-01T00:00:00Z"),
        farm("b", "New", "2026-07-09T00:00:00Z"),
      ],
      user,
      null,
    );
    const farmItems = items.filter((i) => i.kind === "farm");
    expect(farmItems[0].params?.name).toBe("New");
    expect(items.some((i) => i.kind === "profile")).toBe(true);
  });

  it("adds a weather alert entry only for warning/critical insights", () => {
    const items = buildRecentActivity([], null, weatherWithAlert());
    const alert = items.find((i) => i.kind === "weather");
    expect(alert).toBeDefined();
    expect(alert?.category).toBe("heavy_rain");
  });

  it("caps recent farms at three and omits profile when incomplete", () => {
    const farms = Array.from({ length: 6 }, (_, i) =>
      farm(
        `f${i}`,
        `Farm ${i}`,
        `2026-07-${`${10 - i}`.padStart(2, "0")}T00:00:00Z`,
      ),
    );
    const items = buildRecentActivity(farms, null, null);
    expect(items.filter((i) => i.kind === "farm")).toHaveLength(3);
    expect(items.some((i) => i.kind === "profile")).toBe(false);
  });

  it("caps the total at five items", () => {
    const farms = Array.from({ length: 4 }, (_, i) =>
      farm(`f${i}`, `Farm ${i}`, `2026-07-0${i + 1}T00:00:00Z`),
    );
    // 3 farms (cap) + profile + weather alert = 5
    const items = buildRecentActivity(farms, user, weatherWithAlert());
    expect(items).toHaveLength(5);
  });
});
