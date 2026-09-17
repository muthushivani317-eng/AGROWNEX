import type { WeatherBundle, WeatherInsight } from "@/features/weather";

import { generateTasks } from "../utils/tasks";

function weatherWith(codes: string[]): WeatherBundle {
  const insights: WeatherInsight[] = codes.map((code) => ({
    code,
    category: code.split(".")[0] as WeatherInsight["category"],
    severity: "advice",
    title: "",
    message: "",
    params: {},
  }));
  return {
    location: { latitude: 0, longitude: 0, timezone: null, name: null },
    current: {} as WeatherBundle["current"],
    hourly: [],
    daily: [],
    insights,
    mission: {
      primaryAction: "",
      reason: "",
      avoid: null,
      secondaryActions: [],
      confidenceNote: "",
      sourceInsightCode: codes[0] ?? null,
      crop: null,
    },
    fetchedAt: "",
    source: "test",
  };
}

// A fixed Wednesday (no weekly-rotation tasks) keeps assertions stable.
const WED = new Date("2026-07-08T09:00:00");

describe("generateTasks", () => {
  it("always includes crop inspection", () => {
    const ids = generateTasks(null, null, WED).map((t) => t.id);
    expect(ids).toContain("inspect");
  });

  it("recommends irrigation from the weather insight", () => {
    const tasks = generateTasks(
      weatherWith(["irrigation.recommended"]),
      null,
      WED,
    );
    expect(tasks.map((t) => t.id)).toContain("irrigate");
  });

  it("suggests a spray delay when spraying is discouraged", () => {
    const tasks = generateTasks(
      weatherWith(["spraying.avoid_wind"]),
      null,
      WED,
    );
    const spray = tasks.find((t) => t.id === "spray-delay");
    expect(spray).toBeDefined();
    expect(spray?.tone).toBe("warning");
  });

  it("adds drainage and heat tasks for hazards", () => {
    const ids = generateTasks(
      weatherWith(["heavy_rain.severe", "heat_stress.extreme"]),
      null,
      WED,
    ).map((t) => t.id);
    expect(ids).toContain("drainage");
    expect(ids).toContain("heat");
  });

  it("rotates weekly chores by weekday (deterministic)", () => {
    const monday = new Date("2026-07-06T09:00:00"); // day 1 → weeding
    const tuesday = new Date("2026-07-07T09:00:00"); // day 2 → fertilizer
    expect(generateTasks(null, null, monday).map((t) => t.id)).toContain(
      "weed",
    );
    expect(generateTasks(null, null, tuesday).map((t) => t.id)).toContain(
      "fertilizer",
    );
    // Wednesday has neither.
    const wed = generateTasks(null, null, WED).map((t) => t.id);
    expect(wed).not.toContain("weed");
    expect(wed).not.toContain("fertilizer");
  });
});
