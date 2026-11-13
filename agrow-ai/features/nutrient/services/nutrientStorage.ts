import { appStorage } from '@/lib/storage';

import {
  NUT_HISTORY_CACHE_KEY,
  NUT_LATEST_CACHE_KEY,
  NUT_LOCAL_KEY,
  NUT_REPORT_CACHE_KEY,
} from '../constants';
import type { NutrientReport } from '../types';
import { applyGroundnutNutrientSafety } from './nutrientMapper';

/**
 * Local Nutrient store in MMKV:
 *  - an offline **cache** of the last-seen API history / latest / report, and
 *  - the **local-provider** reports (per farm) used in dev / without a backend.
 */
function read<T>(key: string): T {
  return (appStorage.getJSON<T>(key) ?? {}) as T;
}

export const nutrientStorage = {
  // --- Offline cache (API provider) ---
  cacheHistory(farmId: string, items: NutrientReport[]): void {
    const map = read<Record<string, NutrientReport[]>>(NUT_HISTORY_CACHE_KEY);
    map[farmId] = items;
    appStorage.setJSON(NUT_HISTORY_CACHE_KEY, map);
  },
  getCachedHistory(farmId: string): NutrientReport[] | null {
    const reports = read<Record<string, NutrientReport[]>>(NUT_HISTORY_CACHE_KEY)[farmId];
    return reports?.map(applyGroundnutNutrientSafety) ?? null;
  },
  cacheLatest(farmId: string, report: NutrientReport | null): void {
    const map = read<Record<string, NutrientReport | null>>(NUT_LATEST_CACHE_KEY);
    map[farmId] = report;
    appStorage.setJSON(NUT_LATEST_CACHE_KEY, map);
  },
  getCachedLatest(farmId: string): NutrientReport | null {
    const report = read<Record<string, NutrientReport | null>>(NUT_LATEST_CACHE_KEY)[farmId];
    return report ? applyGroundnutNutrientSafety(report) : null;
  },
  cacheReport(report: NutrientReport): void {
    const map = read<Record<string, NutrientReport>>(NUT_REPORT_CACHE_KEY);
    map[report.id] = report;
    appStorage.setJSON(NUT_REPORT_CACHE_KEY, map);
  },
  getCachedReport(id: string): NutrientReport | null {
    const report = read<Record<string, NutrientReport>>(NUT_REPORT_CACHE_KEY)[id];
    return report ? applyGroundnutNutrientSafety(report) : null;
  },

  // --- Local provider store: reports per farm (newest first) ---
  localReports(farmId: string): NutrientReport[] {
    return (read<Record<string, NutrientReport[]>>(NUT_LOCAL_KEY)[farmId] ?? []).map(
      applyGroundnutNutrientSafety,
    );
  },
  addLocalReport(farmId: string, report: NutrientReport): void {
    const map = read<Record<string, NutrientReport[]>>(NUT_LOCAL_KEY);
    map[farmId] = [applyGroundnutNutrientSafety(report), ...(map[farmId] ?? [])];
    appStorage.setJSON(NUT_LOCAL_KEY, map);
  },
  getLocalReport(id: string): NutrientReport | null {
    const map = read<Record<string, NutrientReport[]>>(NUT_LOCAL_KEY);
    for (const list of Object.values(map)) {
      const found = list.find((r) => r.id === id);
      if (found) return applyGroundnutNutrientSafety(found);
    }
    return null;
  },

  clear(): void {
    appStorage.remove(NUT_HISTORY_CACHE_KEY);
    appStorage.remove(NUT_LATEST_CACHE_KEY);
    appStorage.remove(NUT_REPORT_CACHE_KEY);
    appStorage.remove(NUT_LOCAL_KEY);
  },
};
