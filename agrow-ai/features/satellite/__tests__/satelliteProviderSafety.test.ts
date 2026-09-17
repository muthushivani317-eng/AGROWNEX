import { unavailableSatelliteProvider } from "../services/satelliteProvider";
import { cachedDashboardDataSource } from "../services/apiSatelliteProvider";
import type { SatelliteDashboard } from "../types";
import { en } from "../../../localization/locales/en";
import { ta } from "../../../localization/locales/ta";

describe("satellite production safety provider", () => {
  it("never fabricates indices when the backend is unavailable", async () => {
    const session = await unavailableSatelliteProvider.refresh("farm-1");
    expect(session.status).toBe("unavailable");
    expect(session.unavailableReason).toBe("provider_not_configured");
    expect(session.isSample).toBe(false);
    expect(session.ndvi).toBeNull();
    expect(session.indices).toEqual([]);
    expect(session.images).toEqual([]);
  });

  it("returns an explicit unavailable dashboard", async () => {
    const dashboard = await unavailableSatelliteProvider.dashboard(
      "farm-1",
      true,
    );
    expect(dashboard.hasData).toBe(false);
    expect(dashboard.messageCode).toBe(
      "satellite.status.provider_not_configured",
    );
    expect(dashboard.dataSource).toBe("live");
  });
});

test("an empty alert list never claims the farm is healthy", () => {
  expect(en.satellite.alertsEmptyMessage.toLowerCase()).not.toContain(
    "healthy",
  );
  expect(en.satellite.alertsEmptyMessage).toContain("data quality");
  expect(ta.satellite.alertsEmptyMessage).toBeTruthy();
});

describe("satellite cached observation freshness", () => {
  const dashboard = (captureDate: string): SatelliteDashboard => ({
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
      captureDate,
      cloudCover: 10,
      resolutionM: 10,
      ndvi: 0.5,
      ndre: null,
      evi: null,
      ndmi: null,
      vegetationHealth: "moderate",
      stressLevel: "unknown",
      moistureStatus: "unknown",
      trend: "unknown",
      ndviDelta: null,
      confidence: 50,
      metadata: null,
      createdAt: `${captureDate}T00:00:00Z`,
      images: [],
      indices: [],
      alerts: [],
    },
  });

  it("labels an older cached observation as stale", () => {
    expect(
      cachedDashboardDataSource(
        dashboard("2026-07-01"),
        new Date("2026-08-15T00:00:00Z"),
      ),
    ).toBe("stale");
  });

  it("keeps a recent cached observation labelled cached", () => {
    expect(
      cachedDashboardDataSource(
        dashboard("2026-08-10"),
        new Date("2026-08-15T00:00:00Z"),
      ),
    ).toBe("cached");
  });
});
