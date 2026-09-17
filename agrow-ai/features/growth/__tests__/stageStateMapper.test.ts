import { apiToStageState } from "../services/growthMapper";

it("keeps suggested and confirmed stages separate", () => {
  const state = apiToStageState({
    id: "state-1",
    farm_id: "farm-1",
    crop_cycle_id: "cycle-1",
    state: "awaiting_confirmation",
    suggested_stage: "flowering",
    confirmed_stage: null,
    registry_version: "rice-v1",
    calculation_version: "stage-state-machine-v1",
    version: 2,
    pending_sync: false,
    evidence_snapshot: { weather_source: "cached" },
    updated_at: "2026-08-13T00:00:00Z",
  });
  expect(state.suggestedStage).toBe("flowering");
  expect(state.confirmedStage).toBeNull();
  expect(state.evidenceSnapshot.weather_source).toBe("cached");
});
