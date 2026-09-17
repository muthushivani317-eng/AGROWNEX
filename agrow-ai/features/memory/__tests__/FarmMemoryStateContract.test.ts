import fs from "node:fs";
import path from "node:path";

import { filterCachedMemories } from "../services/apiMemoryProvider";
import type { FarmMemory } from "../types";

const readScreen = (name: string) =>
  fs.readFileSync(path.resolve(__dirname, "..", "screens", name), "utf8");

const memory = (overrides: Partial<FarmMemory>): FarmMemory => ({
  id: "m1",
  farmId: "farm-1",
  sourceModule: "weather",
  eventType: "weather_alert",
  summary: "memory.weather",
  params: null,
  confidence: 80,
  importance: "high",
  importanceScore: 80,
  observation: "observed",
  season: "kharif",
  seasonYear: 2026,
  crop: "paddy",
  location: "Thoothukudi",
  occurredAt: "2026-09-01T00:00:00Z",
  createdAt: "2026-09-01T00:00:00Z",
  tags: ["rain"],
  occurrences: 1,
  links: [],
  ...overrides,
});

describe("Farm Memory loading and recovery contract", () => {
  it("waits for farm selection before evaluating dashboard emptiness", () => {
    const dashboard = readScreen("MemoryDashboardScreen.tsx");
    expect(dashboard).toContain('testID="farm-memory-farm-loading"');
    expect(dashboard).toContain("farmsLoading || query.isLoading ?");
  });

  it("keeps offline-banner ownership at the app shell", () => {
    for (const screen of [
      "MemoryDashboardScreen.tsx",
      "MemoryTimelineScreen.tsx",
      "MemorySummaryScreen.tsx",
      "MemoryDetailScreen.tsx",
    ]) {
      expect(readScreen(screen)).not.toContain("<AgOfflineBanner");
    }
  });

  it("supports refresh and retry on every server-backed memory view", () => {
    for (const screen of [
      "MemoryDashboardScreen.tsx",
      "MemoryTimelineScreen.tsx",
      "MemorySummaryScreen.tsx",
      "MemoryDetailScreen.tsx",
    ]) {
      const source = readScreen(screen);
      expect(source).toContain("<RefreshControl");
      expect(source).toContain("query.isRefetching");
      expect(source).toContain("query.refetch()");
      expect(source).toContain("<AgErrorState");
    }
  });

  it("applies active filters to cached offline history", () => {
    const items = [
      memory({ id: "weather" }),
      memory({ id: "soil", sourceModule: "soil", crop: "banana", importance: "low", tags: ["ph"] }),
    ];
    expect(filterCachedMemories(items, { sourceModule: "soil" }).map((x) => x.id)).toEqual(["soil"]);
    expect(filterCachedMemories(items, { crop: "paddy", importance: "high" }).map((x) => x.id)).toEqual(["weather"]);
    expect(filterCachedMemories(items, { q: "PH" }).map((x) => x.id)).toEqual(["soil"]);
  });
});
