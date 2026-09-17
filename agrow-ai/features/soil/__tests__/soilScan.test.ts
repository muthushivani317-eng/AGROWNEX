import { mapSoilScan } from "../services/soilScan";
import { soilStorage } from "../services/soilStorage";

describe("soil scan contract", () => {
  it("maps all eleven bounded outputs without inventing measurements", () => {
    const scan = mapSoilScan({
      farm_id: "farm-1",
      aoi_verified: true,
      generated_at: "2026-08-15T00:00:00Z",
      indicators: Array.from({ length: 11 }, (_, index) => ({
        code: `code_${index}`,
        status: "insufficient_data",
        evidence_class: "INSUFFICIENT_DATA",
        value: null,
        explanation_code: "soil.scan.insufficient",
        details: {},
        sampling_points: [],
      })),
    });
    expect(scan.indicators).toHaveLength(11);
    expect(scan.indicators.every((item) => item.value === null)).toBe(true);
  });

  it("maps persisted provenance, AOI and a real sampling plan", () => {
    const scan = mapSoilScan({
      id: "scan-1",
      farm_id: "farm-1",
      aoi_verified: true,
      aoi_geojson: {
        type: "Polygon",
        coordinates: [
          [
            [78, 11],
            [78.2, 11],
            [78.2, 11.2],
            [78, 11],
          ],
        ],
      },
      generated_at: "2026-08-15T00:00:00Z",
      provider_states: {
        weather: "live",
        satellite: "available",
        terrain: "unavailable",
      },
      provenance: { production_mock_used: false },
      indicators: [],
      sampling_plan: {
        id: "plan-1",
        status: "available",
        created_at: "2026-08-15T00:00:00Z",
        scope: "physical_sample_location_guidance_only",
        points: [
          {
            zone_id: "zone-1",
            longitude: 78.1,
            latitude: 11.1,
            source: "copernicus",
            reference: "scene-1",
            reason: "spatial_variability:different",
            quality: "usable",
            sample_data: false,
          },
        ],
      },
    });
    expect(scan.samplingPlan?.points[0]).toMatchObject({
      zoneId: "zone-1",
      sampleData: false,
    });
    expect(scan.aoiGeojson?.type).toBe("Polygon");
  });

  it("keeps offline scan cache isolated by user and farm", () => {
    const scan = {
      id: "scan-1",
      farmId: "farm-1",
      aoiVerified: false,
      aoiGeojson: null,
      generatedAt: "2026-08-15T00:00:00Z",
      indicators: [],
      providerStates: {},
      provenance: {},
      samplingPlan: null,
    };
    soilStorage.cacheScan("user-a", "farm-1", scan);
    expect(soilStorage.getCachedScan("user-a", "farm-1")?.id).toBe("scan-1");
    expect(soilStorage.getCachedScan("user-b", "farm-1")).toBeNull();
    expect(soilStorage.getCachedScan("user-a", "farm-2")).toBeNull();
  });
});
