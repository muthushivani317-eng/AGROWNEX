import { api } from "@/services/apiClient";

import {
  submitGroundnutStageDecision,
  submitStageTransition,
} from "../services/apiGrowthProvider";
import {
  pendingStageTransitions,
  queueStageTransition,
  removePendingStageTransition,
  syncPendingStageTransitions,
} from "../services/stageOfflineQueue";

jest.mock("@/services/apiClient", () => ({ api: { post: jest.fn() } }));

const input = {
  farmId: "farm-1",
  cropCycleId: "cycle-1",
  event: "correct" as const,
  stage: "flowering" as const,
  expectedVersion: 2,
  idempotencyKey: "stage-correction-0001",
  reason: "Farmer observation",
};

describe("crop-stage farmer workflow", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    pendingStageTransitions().forEach((item) =>
      removePendingStageTransition(item.idempotencyKey),
    );
  });

  it("sends farmer correction without claiming registry or expert verification", async () => {
    (api.post as jest.Mock).mockResolvedValue({
      id: "state-1",
      farm_id: "farm-1",
      crop_cycle_id: "cycle-1",
      state: "corrected",
      suggested_stage: null,
      confirmed_stage: "flowering",
      registry_version: null,
      calculation_version: "stage-state-machine-v1",
      version: 3,
      pending_sync: false,
      evidence_snapshot: { supports: ["farmer_selection"] },
      updated_at: "2026-08-15T00:00:00Z",
    });

    await submitStageTransition(input);

    expect(api.post).toHaveBeenCalledWith(
      "/growth/stage/transition",
      expect.objectContaining({
        event: "correct",
        expert_reviewed: false,
        evidence: expect.objectContaining({
          registry_verified: false,
          supports: ["farmer_selection"],
        }),
      }),
    );
  });

  it("persists an offline correction as pending until explicitly removed", () => {
    queueStageTransition(input);
    expect(pendingStageTransitions()).toEqual([
      expect.objectContaining({ idempotencyKey: "stage-correction-0001" }),
    ]);

    removePendingStageTransition("stage-correction-0001");
    expect(pendingStageTransitions()).toEqual([]);
  });

  it("sends a Groundnut correction to the dedicated confirmation endpoint", async () => {
    (api.post as jest.Mock).mockResolvedValue({
      id: "session-1",
      farm_id: "farm-1",
      crop: "groundnut",
      variety: null,
      title: null,
      sowing_date: "2026-08-01",
      status: "active",
      current_growth_stage: "flowering",
      latest_health_score: 80,
      latest_risk_level: "low",
      image_count: 1,
      created_at: "2026-08-01T00:00:00Z",
      updated_at: "2026-08-15T00:00:00Z",
    });

    const session = await submitGroundnutStageDecision({
      sessionId: "session-1",
      imageId: "image-1",
      action: "correct",
      stage: "flowering",
    });

    expect(api.post).toHaveBeenCalledWith(
      "/growth/groundnut/session/session-1/stage-confirmation",
      {
        image_id: "image-1",
        action: "correct",
        stage: "flowering",
      },
    );
    expect(session.currentGrowthStage).toBe("flowering");
  });

  it("syncs a queued action once and removes it only after server success", async () => {
    queueStageTransition(input);
    const send = jest.fn().mockResolvedValue({});

    await expect(syncPendingStageTransitions(send)).resolves.toEqual({
      synced: 1,
      remaining: 0,
    });
    expect(send).toHaveBeenCalledWith(input);
  });
});
