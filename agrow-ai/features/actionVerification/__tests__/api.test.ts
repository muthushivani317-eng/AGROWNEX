import { mapAction } from "../api";

it("maps a farmer completion without creating a success outcome", () => {
  const action = mapAction({
    id: "a1",
    farm_id: "f1",
    crop_cycle_id: null,
    source_feature: "weather",
    source_record_id: "w1",
    source_version: "1",
    action_code: "weather_mission",
    source_verified: true,
    farmer_created: false,
    suggestion_time: "2026-08-15T00:00:00Z",
    due_at: null,
    expires_at: null,
    status: "farmer_reported_done",
    verification_scope: "workflow_completion_only",
    version: 2,
    pending_sync: false,
    created_at: "2026-08-15T00:00:00Z",
    updated_at: "2026-08-15T00:00:00Z",
  });
  expect(action.status).toBe("farmer_reported_done");
  expect(action).not.toHaveProperty("successful");
});
