jest.mock("@/services/apiClient", () => ({
  api: { get: jest.fn(), post: jest.fn(), put: jest.fn(), delete: jest.fn() },
  configureApiAuth: jest.fn(),
}));

import { api } from "@/services/apiClient";
import { ApiError } from "@/types";

import {
  getWaterloggingAssessment,
  getWaterloggingHistory,
} from "../services/apiSatelliteProvider";
import { satelliteStorage } from "../services/satelliteStorage";
import type { WaterloggingAssessment } from "../types";

const apiGet = api.get as jest.Mock;

const cached: WaterloggingAssessment = {
  id: "assessment-1",
  farmId: "farm-1",
  decision: "insufficient_data",
  observedAt: "2026-07-01T00:00:00Z",
  processedAt: "2026-07-01T01:00:00Z",
  source: null,
  aoiCoveragePct: null,
  evidencePresent: [],
  evidenceMissing: ["satellite_observation"],
  freshness: "unknown",
  explanation: "Not enough evidence.",
  isSample: false,
  provenance: { evidence_type: "insufficient" },
};

describe("waterlogging offline cache", () => {
  beforeEach(() => {
    apiGet.mockReset();
    satelliteStorage.clear();
  });

  it("returns a timestamped stale cached result on a network failure", async () => {
    satelliteStorage.cacheWaterlogging("farm-1", cached);
    apiGet.mockRejectedValue(
      new ApiError({ status: 0, message: "offline", errorCode: "network" }),
    );
    const result = await getWaterloggingAssessment("farm-1");
    expect(result?.id).toBe("assessment-1");
    expect(result?.dataSource).toBe("stale");
    expect(result?.observedAt).toBe("2026-07-01T00:00:00Z");
  });

  it("returns cached history without presenting it as live", async () => {
    satelliteStorage.cacheWaterloggingHistory("farm-1", [cached]);
    apiGet.mockRejectedValue(
      new ApiError({ status: 0, message: "offline", errorCode: "network" }),
    );
    const result = await getWaterloggingHistory("farm-1");
    expect(result).toHaveLength(1);
    expect(result[0].dataSource).toBe("stale");
  });

  it("does not fabricate a result when offline without cache", async () => {
    apiGet.mockRejectedValue(
      new ApiError({ status: 0, message: "offline", errorCode: "network" }),
    );
    await expect(getWaterloggingAssessment("farm-1")).rejects.toBeInstanceOf(
      ApiError,
    );
  });
});
