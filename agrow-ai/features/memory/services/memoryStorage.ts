import { appStorage } from '@/lib/storage';

import {
  MEMORY_DASHBOARD_CACHE_KEY,
  MEMORY_DETAIL_CACHE_KEY,
  MEMORY_HISTORY_CACHE_KEY,
  MEMORY_LOCAL_KEY,
  MEMORY_SUMMARY_CACHE_KEY,
} from '../constants';
import type {
  FarmMemory,
  MemoryDashboard,
  MemorySummaryBundle,
} from '../types';

/**
 * Local Farm Memory store in MMKV:
 *  - an offline **cache** of the last-seen API dashboard / history / summary / detail, and
 *  - the **local-provider** memories (per farm) used in dev / without a backend.
 */
function read<T>(key: string): T {
  return (appStorage.getJSON<T>(key) ?? {}) as T;
}

export const memoryStorage = {
  // --- Offline cache (API provider) ---
  cacheDashboard(farmId: string, dashboard: MemoryDashboard): void {
    const map = read<Record<string, MemoryDashboard>>(MEMORY_DASHBOARD_CACHE_KEY);
    map[farmId] = dashboard;
    appStorage.setJSON(MEMORY_DASHBOARD_CACHE_KEY, map);
  },
  getCachedDashboard(farmId: string): MemoryDashboard | null {
    return read<Record<string, MemoryDashboard>>(MEMORY_DASHBOARD_CACHE_KEY)[farmId] ?? null;
  },
  cacheHistory(farmId: string, items: FarmMemory[]): void {
    const map = read<Record<string, FarmMemory[]>>(MEMORY_HISTORY_CACHE_KEY);
    map[farmId] = items;
    appStorage.setJSON(MEMORY_HISTORY_CACHE_KEY, map);
  },
  getCachedHistory(farmId: string): FarmMemory[] | null {
    return read<Record<string, FarmMemory[]>>(MEMORY_HISTORY_CACHE_KEY)[farmId] ?? null;
  },
  cacheSummary(farmId: string, bundle: MemorySummaryBundle): void {
    const map = read<Record<string, MemorySummaryBundle>>(MEMORY_SUMMARY_CACHE_KEY);
    map[farmId] = bundle;
    appStorage.setJSON(MEMORY_SUMMARY_CACHE_KEY, map);
  },
  getCachedSummary(farmId: string): MemorySummaryBundle | null {
    return read<Record<string, MemorySummaryBundle>>(MEMORY_SUMMARY_CACHE_KEY)[farmId] ?? null;
  },
  cacheDetail(memory: FarmMemory): void {
    const map = read<Record<string, FarmMemory>>(MEMORY_DETAIL_CACHE_KEY);
    map[memory.id] = memory;
    appStorage.setJSON(MEMORY_DETAIL_CACHE_KEY, map);
  },
  getCachedDetail(id: string): FarmMemory | null {
    return read<Record<string, FarmMemory>>(MEMORY_DETAIL_CACHE_KEY)[id] ?? null;
  },

  // --- Local provider store: memories per farm (newest first) ---
  localMemories(farmId: string): FarmMemory[] {
    return read<Record<string, FarmMemory[]>>(MEMORY_LOCAL_KEY)[farmId] ?? [];
  },
  setLocalMemories(farmId: string, memories: FarmMemory[]): void {
    const map = read<Record<string, FarmMemory[]>>(MEMORY_LOCAL_KEY);
    map[farmId] = memories;
    appStorage.setJSON(MEMORY_LOCAL_KEY, map);
  },
  getLocalMemory(id: string): FarmMemory | null {
    const map = read<Record<string, FarmMemory[]>>(MEMORY_LOCAL_KEY);
    for (const list of Object.values(map)) {
      const found = list.find((m) => m.id === id);
      if (found) return found;
    }
    return null;
  },

  clear(): void {
    appStorage.remove(MEMORY_DASHBOARD_CACHE_KEY);
    appStorage.remove(MEMORY_HISTORY_CACHE_KEY);
    appStorage.remove(MEMORY_SUMMARY_CACHE_KEY);
    appStorage.remove(MEMORY_DETAIL_CACHE_KEY);
    appStorage.remove(MEMORY_LOCAL_KEY);
  },
};
