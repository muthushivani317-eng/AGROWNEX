import { appStorage } from "@/lib/storage";
import { api } from "@/services/apiClient";
import { endpoints } from "@/services/endpoints";
import { ApiError } from "@/types";

import {
  type ApiHarvestReadiness,
  type HarvestReadiness,
  type HarvestReadinessHistoryEntry,
  type ApiHarvestReadinessHistoryEntry,
  fallbackHarvestReadiness,
  mapHarvestReadiness,
} from "../harvestReadiness";

const key = (farmId: string, cycleId: string) =>
  `agrowai.harvest-readiness.${farmId}.${cycleId}`;

function save(value: HarvestReadiness) {
  if (value.farmId && value.cropCycleId) {
    appStorage.setJSON(key(value.farmId, value.cropCycleId), value);
  }
  return value;
}

export async function getCurrentReadiness(farmId: string, cropCycleId: string) {
  try {
    const dto = await api.get<ApiHarvestReadiness | null>(
      endpoints.harvestReadiness.current,
      { params: { farm_id: farmId, crop_cycle_id: cropCycleId } },
    );
    if (dto) return save(mapHarvestReadiness(dto));
    appStorage.remove(key(farmId, cropCycleId));
    return fallbackHarvestReadiness();
  } catch (error) {
    const cached = appStorage.getJSON<HarvestReadiness>(
      key(farmId, cropCycleId),
    );
    if (error instanceof ApiError && error.isNetwork && cached) {
      return { ...cached, cached: true };
    }
    throw error;
  }
}

export async function evaluateReadiness(farmId: string, cropCycleId: string) {
  const dto = await api.post<ApiHarvestReadiness>(
    endpoints.harvestReadiness.evaluate,
    {
      farm_id: farmId,
      crop_cycle_id: cropCycleId,
      farmer_observations: [],
      weather_freshness: "missing",
      idempotency_key: `harvest-evaluate-${Date.now()}`,
    },
  );
  return save(mapHarvestReadiness(dto));
}

export async function confirmReadiness(readinessId: string, ready: boolean) {
  const dto = await api.post<ApiHarvestReadiness>(
    endpoints.harvestReadiness.confirm,
    {
      readiness_id: readinessId,
      ready,
      idempotency_key: `harvest-confirm-${Date.now()}`,
    },
  );
  return save(mapHarvestReadiness(dto));
}

export async function getReadinessHistory(
  readinessId: string,
): Promise<HarvestReadinessHistoryEntry[]> {
  const rows = await api.get<ApiHarvestReadinessHistoryEntry[]>(
    endpoints.harvestReadiness.history(readinessId),
  );
  return rows.map((row) => ({
    id: row.id,
    event: row.event,
    priorState: row.prior_state,
    nextState: row.next_state,
    farmerConfirmed: row.farmer_confirmed,
    createdAt: row.created_at,
  }));
}
