import { appStorage } from "@/lib/storage";

import {
  SOIL_DASHBOARD_CACHE_KEY,
  SOIL_HISTORY_CACHE_KEY,
  SOIL_LOCAL_KEY,
  SOIL_SCAN_CACHE_KEY,
  SOIL_SCAN_HISTORY_CACHE_KEY,
} from "../constants";
import type {
  SoilDashboard,
  SoilHistoryEntry,
  SoilReport,
  SoilScan,
} from "../types";

/**
 * Local Soil Intelligence store in MMKV:
 *  - an offline **cache** of the last-seen API dashboard/history (per farm), and
 *  - the **local-provider** soil reports (per farm) used in dev / without a backend.
 */
function read<T>(key: string): T {
  return (appStorage.getJSON<T>(key) ?? {}) as T;
}

export const soilStorage = {
  // --- Offline cache (API provider) ---
  cacheDashboard(farmId: string, dashboard: SoilDashboard): void {
    const map = read<Record<string, SoilDashboard>>(SOIL_DASHBOARD_CACHE_KEY);
    map[farmId] = dashboard;
    appStorage.setJSON(SOIL_DASHBOARD_CACHE_KEY, map);
  },
  getCachedDashboard(farmId: string): SoilDashboard | null {
    return (
      read<Record<string, SoilDashboard>>(SOIL_DASHBOARD_CACHE_KEY)[farmId] ??
      null
    );
  },
  cacheHistory(farmId: string, items: SoilHistoryEntry[]): void {
    const map = read<Record<string, SoilHistoryEntry[]>>(
      SOIL_HISTORY_CACHE_KEY,
    );
    map[farmId] = items;
    appStorage.setJSON(SOIL_HISTORY_CACHE_KEY, map);
  },
  getCachedHistory(farmId: string): SoilHistoryEntry[] | null {
    return (
      read<Record<string, SoilHistoryEntry[]>>(SOIL_HISTORY_CACHE_KEY)[
        farmId
      ] ?? null
    );
  },
  cacheScan(userId: string, farmId: string, scan: SoilScan): void {
    const map = read<Record<string, SoilScan>>(SOIL_SCAN_CACHE_KEY);
    map[`${userId}:${farmId}`] = scan;
    appStorage.setJSON(SOIL_SCAN_CACHE_KEY, map);
  },
  getCachedScan(userId: string, farmId: string): SoilScan | null {
    return (
      read<Record<string, SoilScan>>(SOIL_SCAN_CACHE_KEY)[
        `${userId}:${farmId}`
      ] ?? null
    );
  },
  cacheScanHistory(userId: string, farmId: string, scans: SoilScan[]): void {
    const map = read<Record<string, SoilScan[]>>(SOIL_SCAN_HISTORY_CACHE_KEY);
    map[`${userId}:${farmId}`] = scans;
    appStorage.setJSON(SOIL_SCAN_HISTORY_CACHE_KEY, map);
  },
  getCachedScanHistory(userId: string, farmId: string): SoilScan[] | null {
    return (
      read<Record<string, SoilScan[]>>(SOIL_SCAN_HISTORY_CACHE_KEY)[
        `${userId}:${farmId}`
      ] ?? null
    );
  },

  // --- Local provider store: reports per farm (newest first) ---
  localReports(farmId: string): SoilReport[] {
    return read<Record<string, SoilReport[]>>(SOIL_LOCAL_KEY)[farmId] ?? [];
  },
  addLocalReport(farmId: string, report: SoilReport): void {
    const map = read<Record<string, SoilReport[]>>(SOIL_LOCAL_KEY);
    map[farmId] = [report, ...(map[farmId] ?? [])];
    appStorage.setJSON(SOIL_LOCAL_KEY, map);
  },

  clear(): void {
    appStorage.remove(SOIL_DASHBOARD_CACHE_KEY);
    appStorage.remove(SOIL_HISTORY_CACHE_KEY);
    appStorage.remove(SOIL_LOCAL_KEY);
    appStorage.remove(SOIL_SCAN_CACHE_KEY);
    appStorage.remove(SOIL_SCAN_HISTORY_CACHE_KEY);
  },
};
