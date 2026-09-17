import { api } from "@/services/apiClient";
import { endpoints } from "@/services/endpoints";
import { ApiError, type Paginated as ApiPaginated } from "@/types";

import { DEFAULT_PAGE_SIZE } from "../constants";
import type {
  ApiSatelliteAlert,
  ApiSatelliteDashboard,
  ApiSatelliteHistoryEntry,
  ApiSatelliteSession,
  ApiSatelliteTimeline,
  Paginated,
  SatelliteAlert,
  SatelliteDashboard,
  SatelliteHistoryEntry,
  SatelliteSession,
  SatelliteTimeline,
  ApiWaterloggingAssessment,
  WaterloggingAssessment,
  SatelliteReadiness,
} from "../types";
import {
  apiToAlert,
  apiToDashboard,
  apiToHistoryEntry,
  apiToSession,
  apiToTimeline,
} from "./satelliteMapper";
import type { SatelliteProvider } from "./satelliteProvider";
import { satelliteStorage } from "./satelliteStorage";
import { logger } from "@/lib/logger";

// Mirrors the backend's existing acquisition lookback. This is an operational
// freshness label, not an agronomic threshold.
const OBSERVATION_STALE_AFTER_DAYS = 14;

export function cachedDashboardDataSource(
  dashboard: SatelliteDashboard,
  now = new Date(),
): "cached" | "stale" {
  const captureDate = dashboard.session?.captureDate;
  if (!captureDate) return "stale";
  const capturedAt = Date.parse(`${captureDate}T00:00:00Z`);
  if (!Number.isFinite(capturedAt)) return "stale";
  const ageDays = (now.getTime() - capturedAt) / (24 * 60 * 60 * 1000);
  return ageDays > OBSERVATION_STALE_AFTER_DAYS ? "stale" : "cached";
}

export const mapWaterloggingAssessment = (
  dto: ApiWaterloggingAssessment,
): WaterloggingAssessment => ({
  id: dto.id,
  farmId: dto.farm_id,
  decision: dto.decision,
  observedAt: dto.observed_at,
  processedAt: dto.processed_at,
  source: dto.source,
  aoiCoveragePct: dto.aoi_coverage_pct,
  evidencePresent: dto.evidence_present,
  evidenceMissing: dto.evidence_missing,
  freshness: dto.freshness,
  explanation: dto.explanation,
  isSample: dto.is_sample,
  provenance: dto.provenance,
});

export function cachedWaterloggingDataSource(
  assessment: WaterloggingAssessment,
  now = new Date(),
): "cached" | "stale" {
  const timestamp = assessment.observedAt ?? assessment.processedAt;
  const observed = Date.parse(timestamp);
  if (!Number.isFinite(observed)) return "stale";
  const ageDays = (now.getTime() - observed) / (24 * 60 * 60 * 1000);
  return assessment.freshness === "stale" ||
    ageDays > OBSERVATION_STALE_AFTER_DAYS
    ? "stale"
    : "cached";
}

export async function getWaterloggingAssessment(
  farmId: string,
): Promise<WaterloggingAssessment | null> {
  try {
    const dto = await api.get<ApiWaterloggingAssessment | null>(
      endpoints.satellite.waterlogging,
      { params: { farm_id: farmId } },
    );
    if (!dto) return null;
    const result = {
      ...mapWaterloggingAssessment(dto),
      dataSource: "live" as const,
    };
    satelliteStorage.cacheWaterlogging(farmId, result);
    return result;
  } catch (error) {
    const cached = satelliteStorage.getCachedWaterlogging(farmId);
    if (cached && error instanceof ApiError && error.isNetwork) {
      return { ...cached, dataSource: cachedWaterloggingDataSource(cached) };
    }
    throw error;
  }
}

export async function getWaterloggingHistory(
  farmId: string,
): Promise<WaterloggingAssessment[]> {
  try {
    const page = await api.get<ApiPaginated<ApiWaterloggingAssessment>>(
      endpoints.satellite.waterloggingHistory,
      { params: { farm_id: farmId, page: 1, page_size: DEFAULT_PAGE_SIZE } },
    );
    const items = page.items.map(mapWaterloggingAssessment);
    satelliteStorage.cacheWaterloggingHistory(farmId, items);
    return items;
  } catch (error) {
    const cached = satelliteStorage.getCachedWaterloggingHistory(farmId);
    if (cached && error instanceof ApiError && error.isNetwork) {
      return cached.map((item) => ({
        ...item,
        dataSource: cachedWaterloggingDataSource(item),
      }));
    }
    throw error;
  }
}

export async function refreshWaterloggingAssessment(
  farmId: string,
): Promise<WaterloggingAssessment> {
  const result = mapWaterloggingAssessment(
    await api.post<ApiWaterloggingAssessment>(
      `${endpoints.satellite.waterloggingRefresh}?farm_id=${farmId}`,
    ),
  );
  satelliteStorage.cacheWaterlogging(farmId, { ...result, dataSource: "live" });
  return result;
}

export async function repairSatelliteImages(farmId: string): Promise<void> {
  await api.post(
    `${endpoints.satellite.imageRepair}?farm_id=${encodeURIComponent(farmId)}`,
  );
}

export async function getSatelliteReadiness(): Promise<SatelliteReadiness> {
  return api.get<SatelliteReadiness>(endpoints.satellite.readiness);
}

/**
 * Backend Satellite provider (docs/API_CONTRACT → satellite). The dashboard,
 * history and timeline are mirrored to MMKV so monitoring stays readable offline;
 * on a network error the last cached copy is served. A refresh surfaces the network
 * error so the hook can queue it for retry.
 */
export const apiSatelliteProvider: SatelliteProvider = {
  async dashboard(farmId: string): Promise<SatelliteDashboard> {
    logger.info("satellite.request", "satellite_request_started");
    try {
      const dto = await api.get<ApiSatelliteDashboard>(
        endpoints.satellite.root,
        {
          params: { farm_id: farmId },
        },
      );
      const result = apiToDashboard(dto);
      result.dataSource = "live";
      satelliteStorage.cacheDashboard(farmId, result);
      logger.info("satellite.request", "satellite_request_completed", {
        response_data_present: Boolean(result),
      });
      return result;
    } catch (err) {
      const cached = satelliteStorage.getCachedDashboard(farmId);
      if (cached && err instanceof ApiError && err.isNetwork) {
        logger.info("satellite.request", "satellite_request_completed", {
          response_data_present: true,
          source: "cache",
        });
        return { ...cached, dataSource: cachedDashboardDataSource(cached) };
      }
      logger.info("satellite.request", "satellite_request_failed", {
        category:
          err instanceof ApiError
            ? err.isNetwork
              ? "network_unavailable"
              : err.errorCode
            : "unknown",
      });
      throw err;
    }
  },

  async history(
    farmId: string,
    page = 1,
    pageSize = DEFAULT_PAGE_SIZE,
  ): Promise<Paginated<SatelliteHistoryEntry>> {
    try {
      const dto = await api.get<ApiPaginated<ApiSatelliteHistoryEntry>>(
        endpoints.satellite.history,
        { params: { farm_id: farmId, page, page_size: pageSize } },
      );
      const result: Paginated<SatelliteHistoryEntry> = {
        items: dto.items.map(apiToHistoryEntry),
        page: dto.page,
        pageSize: dto.page_size,
        total: dto.total,
        totalPages: dto.total_pages,
      };
      if (result.page === 1)
        satelliteStorage.cacheHistory(farmId, result.items);
      return result;
    } catch (err) {
      const cached = satelliteStorage.getCachedHistory(farmId);
      if (cached && err instanceof ApiError && err.isNetwork) {
        return {
          items: cached,
          page: 1,
          pageSize: cached.length,
          total: cached.length,
          totalPages: 1,
        };
      }
      throw err;
    }
  },

  async timeline(farmId: string, range: string): Promise<SatelliteTimeline> {
    const key = `${farmId}:${range}`;
    try {
      const dto = await api.get<ApiSatelliteTimeline>(
        endpoints.satellite.timeline,
        {
          params: { farm_id: farmId, range },
        },
      );
      const result = apiToTimeline(dto);
      satelliteStorage.cacheTimeline(key, result);
      return result;
    } catch (err) {
      const cached = satelliteStorage.getCachedTimeline(key);
      if (cached && err instanceof ApiError && err.isNetwork) return cached;
      throw err;
    }
  },

  async alerts(farmId: string): Promise<SatelliteAlert[]> {
    const dto = await api.get<ApiSatelliteAlert[]>(endpoints.satellite.alerts, {
      params: { farm_id: farmId },
    });
    return dto.map(apiToAlert);
  },

  async refresh(farmId: string): Promise<SatelliteSession> {
    return apiToSession(
      await api.post<ApiSatelliteSession>(
        `${endpoints.satellite.refresh}?farm_id=${farmId}`,
      ),
    );
  },
};
