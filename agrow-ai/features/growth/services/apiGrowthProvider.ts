import { api } from "@/services/apiClient";
import { endpoints } from "@/services/endpoints";
import { type Paginated } from "@/types";

import type {
  ApiGrowthImage,
  ApiGrowthSessionDetail,
  ApiGrowthTimeline,
  ApiUploadResult,
  GrowthImage,
  GrowthSessionDetail,
  GrowthTimeline,
  UploadGrowthInput,
  UploadResult,
  ApiStageState,
  StageState,
  StageTransitionInput,
  StageTransitionHistory,
  ApiStageTransitionHistory,
} from "../types";
import {
  apiToImage,
  apiToSessionDetail,
  apiToTimeline,
  apiToUploadResult,
  apiToStageState,
} from "./growthMapper";

export async function getStageState(
  farmId: string,
  cropCycleId: string,
): Promise<StageState | null> {
  const dto = await api.get<ApiStageState | null>(endpoints.growth.stage, {
    params: { farm_id: farmId, crop_cycle_id: cropCycleId },
  });
  return dto ? apiToStageState(dto) : null;
}

export async function submitStageTransition(
  input: StageTransitionInput,
): Promise<StageState> {
  const dto = await api.post<ApiStageState>(endpoints.growth.stageTransition, {
    farm_id: input.farmId,
    crop_cycle_id: input.cropCycleId,
    event: input.event,
    stage: input.stage ?? null,
    expected_version: input.expectedVersion ?? null,
    idempotency_key: input.idempotencyKey,
    reason: input.reason ?? null,
    expert_reviewed: false,
    allow_large_jump: false,
    evidence: {
      registry_verified: false,
      planting_date_present: false,
      supports: ["farmer_selection"],
      conflicts: [],
      missing: [],
    },
  });
  return apiToStageState(dto);
}

export async function getStageHistory(
  stateId: string,
): Promise<StageTransitionHistory[]> {
  const rows = await api.get<ApiStageTransitionHistory[]>(
    endpoints.growth.stageHistory(stateId),
  );
  return rows.map((item) => ({
    id: item.id,
    event: item.event,
    priorState: item.prior_state,
    nextState: item.next_state,
    priorStage: item.prior_stage,
    stage: item.stage,
    reason: item.reason,
    expertReviewed: item.expert_reviewed,
    createdAt: item.created_at,
  }));
}
import { growthStorage } from "./growthStorage";
import type { GrowthProvider } from "./growthProvider";

/**
 * Backend growth provider (docs/API_CONTRACT.md → CROP GROWTH). Gemini vision and
 * R2 storage run server-side; the image is sent as base64 JSON. Every history
 * fetch is mirrored to MMKV. Failures are propagated so stale or cross-farm
 * cached photos are never presented as a successful history response.
 */
export const apiGrowthProvider: GrowthProvider = {
  async upload(input: UploadGrowthInput): Promise<UploadResult> {
    const dto = await api.post<ApiUploadResult>(endpoints.growth.upload, {
      image_base64: input.imageBase64,
      mime_type: input.mimeType,
      farm_id: input.farmId,
      session_id: input.sessionId ?? undefined,
      crop: input.crop ?? undefined,
      variety: input.variety ?? undefined,
      language: input.language,
      capture_method: input.captureMethod,
      latitude: input.latitude ?? undefined,
      longitude: input.longitude ?? undefined,
      notes: input.notes ?? undefined,
    });
    const result = apiToUploadResult(dto);
    growthStorage.upsertImage(result.image);
    growthStorage.upsertSession(result.session);
    return result;
  },

  async history(
    sessionId?: string | null,
    farmId?: string | null,
  ): Promise<GrowthImage[]> {
      const data = await api.get<Paginated<ApiGrowthImage>>(
        endpoints.growth.history,
        {
          params: {
            page: 1,
            page_size: 50,
            session_id: sessionId ?? undefined,
            farm_id: farmId ?? undefined,
          },
        },
      );
      const images = data.items.map(apiToImage);
      growthStorage.cacheImages(images);
      return images;
  },

  async timeline(
    sessionId?: string | null,
    farmId?: string | null,
  ): Promise<GrowthTimeline> {
    const dto = await api.get<ApiGrowthTimeline>(endpoints.growth.timeline, {
      params: {
        session_id: sessionId ?? undefined,
        farm_id: farmId ?? undefined,
      },
    });
    return apiToTimeline(dto);
  },

  async latest(): Promise<GrowthImage | null> {
    const dto = await api.get<ApiGrowthImage | null>(endpoints.growth.latest);
    return dto ? apiToImage(dto) : null;
  },

  async session(id: string): Promise<GrowthSessionDetail> {
    const dto = await api.get<ApiGrowthSessionDetail>(
      endpoints.growth.session(id),
    );
    return apiToSessionDetail(dto);
  },

  async deleteImage(id: string): Promise<void> {
    await api.delete<null>(endpoints.growth.image(id));
    growthStorage.removeImage(id);
  },
};
