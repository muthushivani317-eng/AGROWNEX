import {
  hasRecentUsableSatellite,
  runSoilScanWithSatellite,
  SATELLITE_REFRESH_AFTER_MS,
} from "../services/soilScanOrchestrator";
import type { SatelliteDashboard } from "@/features/satellite/types";

const NOW = Date.parse("2026-08-20T12:00:00Z");

function dashboard(overrides: Partial<SatelliteDashboard["session"]> = {}) {
  return {
    farmId: "farm-1",
    hasPolygon: true,
    hasData: true,
    status: "available",
    unavailableReason: "none",
    messageCode: null,
    alerts: [],
    session: {
      id: "session-1",
      farmId: "farm-1",
      provider: "copernicus",
      status: "available",
      unavailableReason: "none",
      isSample: false,
      captureDate: "2026-08-01T00:00:00Z",
      cloudCover: 10,
      resolutionM: 10,
      ndvi: 0.3,
      ndre: 0.2,
      evi: 0.25,
      ndmi: 0.1,
      vegetationHealth: "moderate",
      stressLevel: "none",
      moistureStatus: "adequate",
      trend: null,
      ndviDelta: null,
      confidence: 80,
      metadata: null,
      createdAt: new Date(NOW - 60_000).toISOString(),
      images: [],
      indices: [],
      alerts: [],
      ...overrides,
    },
  } satisfies SatelliteDashboard;
}

describe("soil scan satellite dependency", () => {
  it("reuses recently processed numeric satellite evidence", () => {
    expect(hasRecentUsableSatellite(dashboard(), NOW)).toBe(true);
  });

  it("refreshes evidence older than seven days", () => {
    const old = dashboard({
      createdAt: new Date(NOW - SATELLITE_REFRESH_AFTER_MS).toISOString(),
    });
    expect(hasRecentUsableSatellite(old, NOW)).toBe(false);
  });

  it("refreshes a session without numeric evidence", () => {
    expect(
      hasRecentUsableSatellite(
        dashboard({ ndvi: null, ndre: null, evi: null, ndmi: null }),
        NOW,
      ),
    ).toBe(false);
  });

  it("refreshes stale satellite evidence before running the soil scan", async () => {
    const events: string[] = [];
    const result = await runSoilScanWithSatellite({
      getDashboard: async () => {
        events.push("dashboard");
        return dashboard({
          createdAt: new Date(NOW - SATELLITE_REFRESH_AFTER_MS).toISOString(),
        });
      },
      refreshSatellite: async () => {
        events.push("satellite");
      },
      runSoilScan: async () => {
        events.push("soil");
        return "complete";
      },
      onPhaseChange: (phase) => events.push(phase),
    });

    expect(result).toBe("complete");
    expect(events).toEqual([
      "checking_satellite",
      "dashboard",
      "refreshing_satellite",
      "satellite",
      "preparing_soil",
      "soil",
    ]);
  });

  it("refreshes waterlogging evidence after satellite evidence and before soil results", async () => {
    const events: string[] = [];
    await runSoilScanWithSatellite({
      getDashboard: async () => dashboard({
        createdAt: new Date(NOW - SATELLITE_REFRESH_AFTER_MS).toISOString(),
      }),
      refreshSatellite: async () => { events.push("satellite"); },
      refreshWaterlogging: async () => { events.push("waterlogging"); },
      runSoilScan: async () => { events.push("soil"); return "complete"; },
      onPhaseChange: (phase) => events.push(phase),
    });

    expect(events).toEqual([
      "checking_satellite",
      "refreshing_satellite",
      "satellite",
      "refreshing_waterlogging",
      "waterlogging",
      "preparing_soil",
      "soil",
    ]);
  });

  it("skips satellite refresh when recent evidence is usable", async () => {
    const refreshSatellite = jest.fn();
    await runSoilScanWithSatellite({
      getDashboard: async () => dashboard(),
      refreshSatellite,
      runSoilScan: async () => "complete",
      nowMs: NOW,
    });
    expect(refreshSatellite).not.toHaveBeenCalled();
  });
});
