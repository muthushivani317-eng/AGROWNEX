import {
  cachedWaterloggingDataSource,
  mapWaterloggingAssessment,
} from "../services/apiSatelliteProvider";
import { en } from "@/localization/locales/en";
import { ta } from "@/localization/locales/ta";

describe("waterlogging assessment mapping", () => {
  it("preserves safety and provenance fields", () => {
    const result = mapWaterloggingAssessment({
      id: "assessment-1",
      farm_id: "farm-1",
      decision: "insufficient_data",
      observed_at: null,
      processed_at: "2026-08-13T00:00:00Z",
      source: null,
      aoi_coverage_pct: null,
      evidence_present: [],
      evidence_missing: ["baseline_scene"],
      freshness: "unknown",
      explanation: "Not enough evidence.",
      is_sample: false,
      provenance: { scene_id: null },
    });
    expect(result.decision).toBe("insufficient_data");
    expect(result.aoiCoveragePct).toBeNull();
    expect(result.evidenceMissing).toEqual(["baseline_scene"]);
    expect(result.isSample).toBe(false);
  });

  it("labels cached observations stale from their original observation time", () => {
    const assessment = mapWaterloggingAssessment({
      id: "assessment-1",
      farm_id: "farm-1",
      decision: "insufficient_data",
      observed_at: "2026-07-01T00:00:00Z",
      processed_at: "2026-07-01T01:00:00Z",
      source: null,
      aoi_coverage_pct: null,
      evidence_present: [],
      evidence_missing: ["satellite_observation"],
      freshness: "unknown",
      explanation: "Not enough evidence.",
      is_sample: false,
      provenance: {},
    });
    expect(
      cachedWaterloggingDataSource(
        assessment,
        new Date("2026-08-13T00:00:00Z"),
      ),
    ).toBe("stale");
  });

  it("keeps Tamil and English waterlogging states in parity", () => {
    expect(Object.keys(ta.satellite.waterlogging).sort()).toEqual(
      Object.keys(en.satellite.waterlogging).sort(),
    );
  });
});
