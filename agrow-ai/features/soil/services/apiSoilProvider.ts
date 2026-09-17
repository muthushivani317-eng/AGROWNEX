import { api } from "@/services/apiClient";
import { endpoints } from "@/services/endpoints";
import { ApiError, type Paginated as ApiPaginated } from "@/types";

import { DEFAULT_PAGE_SIZE } from "../constants";
import type {
  ApiSoilDashboard,
  ApiSoilHistoryEntry,
  ApiSoilRecommendation,
  ApiSoilReport,
  Paginated,
  SoilDashboard,
  SoilHistoryEntry,
  SoilRecommendation,
  SoilReport,
  SoilReportInput,
  RemoteSoilOutcome,
  ApiRemoteSoilOutcome,
} from "../types";
import {
  apiToDashboard,
  apiToHistoryEntry,
  apiToRecommendation,
  apiToReport,
  reportInputToApi,
} from "./soilMapper";
import type { SoilProvider } from "./soilProvider";
import { soilStorage } from "./soilStorage";

/**
 * Backend Soil Intelligence provider (docs/API_CONTRACT → soil). The dashboard and
 * history are mirrored to MMKV so soil insights stay readable offline; on a network
 * error the last cached copy is served. Report submission surfaces the network error
 * so the hook can queue it for retry.
 */
export const apiSoilProvider: SoilProvider = {
  async dashboard(farmId: string): Promise<SoilDashboard> {
    try {
      const dto = await api.get<ApiSoilDashboard>(endpoints.soil.root, {
        params: { farm_id: farmId },
      });
      const result = apiToDashboard(dto);
      soilStorage.cacheDashboard(farmId, result);
      return result;
    } catch (err) {
      const cached = soilStorage.getCachedDashboard(farmId);
      if (cached && err instanceof ApiError && err.isNetwork) return cached;
      throw err;
    }
  },

  async latest(farmId: string): Promise<SoilReport> {
    return apiToReport(
      await api.get<ApiSoilReport>(endpoints.soil.latest, {
        params: { farm_id: farmId },
      }),
    );
  },

  async history(
    farmId: string,
    page = 1,
    pageSize = DEFAULT_PAGE_SIZE,
  ): Promise<Paginated<SoilHistoryEntry>> {
    try {
      const dto = await api.get<ApiPaginated<ApiSoilHistoryEntry>>(
        endpoints.soil.history,
        {
          params: { farm_id: farmId, page, page_size: pageSize },
        },
      );
      const result: Paginated<SoilHistoryEntry> = {
        items: dto.items.map(apiToHistoryEntry),
        page: dto.page,
        pageSize: dto.page_size,
        total: dto.total,
        totalPages: dto.total_pages,
      };
      if (result.page === 1) soilStorage.cacheHistory(farmId, result.items);
      return result;
    } catch (err) {
      const cached = soilStorage.getCachedHistory(farmId);
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

  async recommendations(farmId: string): Promise<SoilRecommendation[]> {
    const dto = await api.get<ApiSoilRecommendation[]>(
      endpoints.soil.recommendation,
      {
        params: { farm_id: farmId },
      },
    );
    return dto.map(apiToRecommendation);
  },

  async submitReport(input: SoilReportInput): Promise<SoilReport> {
    return apiToReport(
      await api.post<ApiSoilReport>(
        endpoints.soil.report,
        reportInputToApi(input),
      ),
    );
  },

  async remoteEstimation(farmId: string): Promise<RemoteSoilOutcome> {
    const dto = await api.get<ApiRemoteSoilOutcome>(endpoints.soil.remote, {
      params: { farm_id: farmId },
    });
    return {
      status: dto.status,
      reason: dto.reason,
      estimates: dto.estimates.map((item) => ({
        indicator: item.indicator,
        value: item.value,
        unit: item.unit,
        provider: item.provider,
        modelVersion: item.model_version,
      })),
    };
  },
};
