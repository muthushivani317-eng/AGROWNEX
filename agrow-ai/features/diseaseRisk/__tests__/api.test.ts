jest.mock("@/services/apiClient", () => ({
  api: { post: jest.fn() },
}));

jest.mock("@/utils/id", () => ({ uuid: () => "request-id" }));

import { api } from "@/services/apiClient";
import { evaluateRisk } from "../api";

describe("Disease Risk API", () => {
  it("sends the active crop cycle so confirmed stage evidence is retained", async () => {
    (api.post as jest.Mock).mockResolvedValue({
      id: "risk-1",
      farm_id: "farm-1",
      crop: "paddy",
      disease_key: null,
      status: "INSUFFICIENT_EVIDENCE",
      risk_level: null,
      confidence: "verified_rule_evidence",
      weather_factors: [],
      weather_source: "live",
      crop_stage: "vegetative",
      generated_at: "2026-08-28T00:00:00Z",
      valid_until: null,
      rule_version: "1",
      rule_verification_status: "VERIFIED",
      farmer_message_key: "diseaseRisk.insufficientData",
      missing_inputs: [],
      acknowledged_at: null,
      cached: false,
    });

    await evaluateRisk("farm-1", "cycle-1");

    expect(api.post).toHaveBeenCalledWith("/disease-risk/evaluate", {
      farm_id: "farm-1",
      crop_cycle_id: "cycle-1",
      idempotency_key: "request-id",
    });
  });
});
