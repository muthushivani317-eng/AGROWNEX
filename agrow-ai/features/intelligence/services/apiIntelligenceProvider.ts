import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';
import { ApiError, type Paginated as ApiPaginated } from '@/types';

import { DEFAULT_PAGE_SIZE } from '../constants';
import type {
  ApiIntelligenceDashboard,
  ApiIntelligenceHistoryEntry,
  ApiIntelligenceReport,
  IntelligenceDashboard,
  IntelligenceHistoryEntry,
  IntelligenceReport,
  Paginated,
} from '../types';
import { IntelligenceError, type IntelligenceProvider } from './intelligenceProvider';
import { apiToDashboard, apiToHistoryEntry, apiToReport } from './intelligenceMapper';
import { intelligenceStorage } from './intelligenceStorage';

/**
 * Backend Crop Intelligence provider (docs/API_CONTRACT → intelligence). The
 * aggregation + pure engine run server-side. The dashboard, history and reports are
 * mirrored to MMKV so the farm-health assessment stays readable offline; on a network
 * error the last cached copy is served. A refresh surfaces the network error so the
 * hook can queue it for retry.
 */
export const apiIntelligenceProvider: IntelligenceProvider = {
  async dashboard(farmId: string): Promise<IntelligenceDashboard> {
    try {
      const dto = await api.get<ApiIntelligenceDashboard>(endpoints.intelligence.root, {
        params: { farm_id: farmId },
      });
      const result = apiToDashboard(dto);
      intelligenceStorage.cacheDashboard(farmId, result);
      return result;
    } catch (err) {
      const cached = intelligenceStorage.getCachedDashboard(farmId);
      if (cached && err instanceof ApiError && err.isNetwork) return cached;
      throw err;
    }
  },

  async latest(farmId: string): Promise<IntelligenceReport> {
    const report = apiToReport(
      await api.get<ApiIntelligenceReport>(endpoints.intelligence.latest, {
        params: { farm_id: farmId },
      }),
    );
    intelligenceStorage.cacheReport(report);
    return report;
  },

  async history(
    farmId: string,
    page = 1,
    pageSize = DEFAULT_PAGE_SIZE,
  ): Promise<Paginated<IntelligenceHistoryEntry>> {
    try {
      const dto = await api.get<ApiPaginated<ApiIntelligenceHistoryEntry>>(
        endpoints.intelligence.history,
        { params: { farm_id: farmId, page, page_size: pageSize } },
      );
      const result: Paginated<IntelligenceHistoryEntry> = {
        items: dto.items.map(apiToHistoryEntry),
        page: dto.page,
        pageSize: dto.page_size,
        total: dto.total,
        totalPages: dto.total_pages,
      };
      if (result.page === 1) intelligenceStorage.cacheHistory(farmId, result.items);
      return result;
    } catch (err) {
      const cached = intelligenceStorage.getCachedHistory(farmId);
      if (cached && err instanceof ApiError && err.isNetwork) {
        return { items: cached, page: 1, pageSize: cached.length, total: cached.length, totalPages: 1 };
      }
      throw err;
    }
  },

  async getReport(id: string): Promise<IntelligenceReport> {
    try {
      const report = apiToReport(
        await api.get<ApiIntelligenceReport>(endpoints.intelligence.report(id)),
      );
      intelligenceStorage.cacheReport(report);
      return report;
    } catch (err) {
      const cached = intelligenceStorage.getCachedReport(id);
      if (cached && err instanceof ApiError && err.isNetwork) return cached;
      if (err instanceof ApiError && err.errorCode === 'intelligence_report_not_found') {
        throw new IntelligenceError('not_found', 'Report not found');
      }
      throw err;
    }
  },

  async refresh(farmId: string): Promise<IntelligenceReport> {
    const report = apiToReport(
      await api.post<ApiIntelligenceReport>(
        `${endpoints.intelligence.refresh}?farm_id=${farmId}`,
      ),
    );
    intelligenceStorage.cacheReport(report);
    return report;
  },
};
