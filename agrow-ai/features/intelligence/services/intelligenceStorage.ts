import { appStorage } from '@/lib/storage';

import {
  INTEL_DASHBOARD_CACHE_KEY,
  INTEL_HISTORY_CACHE_KEY,
  INTEL_LOCAL_KEY,
  INTEL_REPORT_CACHE_KEY,
} from '../constants';
import type {
  IntelligenceDashboard,
  IntelligenceHistoryEntry,
  IntelligenceReport,
} from '../types';

/**
 * Local Crop Intelligence store in MMKV:
 *  - an offline **cache** of the last-seen API dashboard / history / report, and
 *  - the **local-provider** reports (per farm) used in dev / without a backend.
 */
function read<T>(key: string): T {
  return (appStorage.getJSON<T>(key) ?? {}) as T;
}

export const intelligenceStorage = {
  // --- Offline cache (API provider) ---
  cacheDashboard(farmId: string, dashboard: IntelligenceDashboard): void {
    const map = read<Record<string, IntelligenceDashboard>>(INTEL_DASHBOARD_CACHE_KEY);
    map[farmId] = dashboard;
    appStorage.setJSON(INTEL_DASHBOARD_CACHE_KEY, map);
  },
  getCachedDashboard(farmId: string): IntelligenceDashboard | null {
    return read<Record<string, IntelligenceDashboard>>(INTEL_DASHBOARD_CACHE_KEY)[farmId] ?? null;
  },
  cacheHistory(farmId: string, items: IntelligenceHistoryEntry[]): void {
    const map = read<Record<string, IntelligenceHistoryEntry[]>>(INTEL_HISTORY_CACHE_KEY);
    map[farmId] = items;
    appStorage.setJSON(INTEL_HISTORY_CACHE_KEY, map);
  },
  getCachedHistory(farmId: string): IntelligenceHistoryEntry[] | null {
    return read<Record<string, IntelligenceHistoryEntry[]>>(INTEL_HISTORY_CACHE_KEY)[farmId] ?? null;
  },
  cacheReport(report: IntelligenceReport): void {
    const map = read<Record<string, IntelligenceReport>>(INTEL_REPORT_CACHE_KEY);
    map[report.id] = report;
    appStorage.setJSON(INTEL_REPORT_CACHE_KEY, map);
  },
  getCachedReport(id: string): IntelligenceReport | null {
    return read<Record<string, IntelligenceReport>>(INTEL_REPORT_CACHE_KEY)[id] ?? null;
  },

  // --- Local provider store: reports per farm (newest first) ---
  localReports(farmId: string): IntelligenceReport[] {
    return read<Record<string, IntelligenceReport[]>>(INTEL_LOCAL_KEY)[farmId] ?? [];
  },
  addLocalReport(farmId: string, report: IntelligenceReport): void {
    const map = read<Record<string, IntelligenceReport[]>>(INTEL_LOCAL_KEY);
    map[farmId] = [report, ...(map[farmId] ?? [])];
    appStorage.setJSON(INTEL_LOCAL_KEY, map);
  },
  getLocalReport(id: string): IntelligenceReport | null {
    const map = read<Record<string, IntelligenceReport[]>>(INTEL_LOCAL_KEY);
    for (const list of Object.values(map)) {
      const found = list.find((r) => r.id === id);
      if (found) return found;
    }
    return null;
  },

  clear(): void {
    appStorage.remove(INTEL_DASHBOARD_CACHE_KEY);
    appStorage.remove(INTEL_HISTORY_CACHE_KEY);
    appStorage.remove(INTEL_REPORT_CACHE_KEY);
    appStorage.remove(INTEL_LOCAL_KEY);
  },
};
