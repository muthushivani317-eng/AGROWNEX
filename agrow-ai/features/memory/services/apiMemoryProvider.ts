import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';
import { ApiError, type Paginated as ApiPaginated } from '@/types';

import { DEFAULT_PAGE_SIZE } from '../constants';
import type {
  ApiFarmMemory,
  ApiMemoryDashboard,
  ApiMemoryRebuildResult,
  ApiMemorySummaryBundle,
  FarmMemory,
  MemoryDashboard,
  MemoryHistoryFilter,
  MemoryRebuildResult,
  MemorySummaryBundle,
  Paginated,
} from '../types';
import {
  apiToDashboard,
  apiToMemory,
  apiToSummaryBundle,
} from './memoryMapper';
import { MemoryError, type MemoryProvider } from './memoryProvider';
import { memoryStorage } from './memoryStorage';

/**
 * Backend Farm Memory provider (docs/API_CONTRACT → memory). The aggregation + engine
 * run server-side. The dashboard, timeline, summaries and detail are mirrored to MMKV
 * so the farm memory stays readable offline; on a network error the last cached copy is
 * served. A rebuild surfaces the network error so the hook can queue it for retry.
 */
function toParams(filter?: MemoryHistoryFilter): Record<string, string | number> {
  const params: Record<string, string | number> = {};
  if (filter?.sourceModule) params.source_module = filter.sourceModule;
  if (filter?.season) params.season = filter.season;
  if (filter?.crop) params.crop = filter.crop;
  if (filter?.importance) params.importance = filter.importance;
  if (filter?.q) params.q = filter.q;
  return params;
}

function hasActiveFilter(filter?: MemoryHistoryFilter): boolean {
  return Boolean(
    filter?.sourceModule ||
      filter?.season ||
      filter?.crop ||
      filter?.importance ||
      filter?.q?.trim(),
  );
}

/** Apply the requested history constraints to an offline first-page cache. */
export function filterCachedMemories(
  items: FarmMemory[],
  filter?: MemoryHistoryFilter,
): FarmMemory[] {
  const query = filter?.q?.trim().toLocaleLowerCase();
  return items.filter((item) => {
    if (filter?.sourceModule && item.sourceModule !== filter.sourceModule) return false;
    if (filter?.season && item.season !== filter.season) return false;
    if (filter?.crop && item.crop !== filter.crop) return false;
    if (filter?.importance && item.importance !== filter.importance) return false;
    if (!query) return true;
    return [
      item.summary,
      item.eventType,
      item.crop,
      item.location,
      ...item.tags,
    ].some((value) => value?.toLocaleLowerCase().includes(query));
  });
}

export const apiMemoryProvider: MemoryProvider = {
  async dashboard(farmId: string): Promise<MemoryDashboard> {
    try {
      const dto = await api.get<ApiMemoryDashboard>(endpoints.memory.root, {
        params: { farm_id: farmId },
      });
      const result = apiToDashboard(dto);
      memoryStorage.cacheDashboard(farmId, result);
      return result;
    } catch (err) {
      const cached = memoryStorage.getCachedDashboard(farmId);
      if (cached && err instanceof ApiError && err.isNetwork) return cached;
      throw err;
    }
  },

  async latest(farmId: string): Promise<FarmMemory> {
    const memory = apiToMemory(
      await api.get<ApiFarmMemory>(endpoints.memory.latest, {
        params: { farm_id: farmId },
      }),
    );
    memoryStorage.cacheDetail(memory);
    return memory;
  },

  async history(
    farmId: string,
    filter?: MemoryHistoryFilter,
    page = 1,
    pageSize = DEFAULT_PAGE_SIZE,
  ): Promise<Paginated<FarmMemory>> {
    try {
      const dto = await api.get<ApiPaginated<ApiFarmMemory>>(endpoints.memory.history, {
        params: { farm_id: farmId, page, page_size: pageSize, ...toParams(filter) },
      });
      const result: Paginated<FarmMemory> = {
        items: dto.items.map(apiToMemory),
        page: dto.page,
        pageSize: dto.page_size,
        total: dto.total,
        totalPages: dto.total_pages,
      };
      // Cache only the unfiltered first page for offline browsing.
      if (result.page === 1 && !hasActiveFilter(filter)) {
        memoryStorage.cacheHistory(farmId, result.items);
      }
      return result;
    } catch (err) {
      const cached = memoryStorage.getCachedHistory(farmId);
      if (cached && err instanceof ApiError && err.isNetwork) {
        const items = filterCachedMemories(cached, filter);
        return { items, page: 1, pageSize: items.length, total: items.length, totalPages: 1 };
      }
      throw err;
    }
  },

  async summary(farmId: string): Promise<MemorySummaryBundle> {
    try {
      const bundle = apiToSummaryBundle(
        await api.get<ApiMemorySummaryBundle>(endpoints.memory.summary, {
          params: { farm_id: farmId },
        }),
      );
      memoryStorage.cacheSummary(farmId, bundle);
      return bundle;
    } catch (err) {
      const cached = memoryStorage.getCachedSummary(farmId);
      if (cached && err instanceof ApiError && err.isNetwork) return cached;
      throw err;
    }
  },

  async getMemory(id: string): Promise<FarmMemory> {
    try {
      const memory = apiToMemory(await api.get<ApiFarmMemory>(endpoints.memory.byId(id)));
      memoryStorage.cacheDetail(memory);
      return memory;
    } catch (err) {
      const cached = memoryStorage.getCachedDetail(id);
      if (cached && err instanceof ApiError && err.isNetwork) return cached;
      if (err instanceof ApiError && err.errorCode === 'memory_not_found') {
        throw new MemoryError('not_found', 'Memory not found');
      }
      throw err;
    }
  },

  async rebuild(farmId: string): Promise<MemoryRebuildResult> {
    const dto = await api.post<ApiMemoryRebuildResult>(
      `${endpoints.memory.rebuild}?farm_id=${farmId}`,
    );
    return {
      farmId: dto.farm_id,
      created: dto.created,
      total: dto.total,
      summaries: dto.summaries,
      links: dto.links,
    };
  },
};
