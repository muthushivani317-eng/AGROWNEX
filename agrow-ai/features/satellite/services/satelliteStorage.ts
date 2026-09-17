import { appStorage } from "@/lib/storage";

import {
  SAT_DASHBOARD_CACHE_KEY,
  SAT_HISTORY_CACHE_KEY,
  SAT_LOCAL_KEY,
  SAT_TIMELINE_CACHE_KEY,
  SAT_WATERLOGGING_CACHE_KEY,
  SAT_WATERLOGGING_HISTORY_CACHE_KEY,
} from "../constants";
import type {
  SatelliteDashboard,
  SatelliteHistoryEntry,
  SatelliteSession,
  SatelliteTimeline,
  WaterloggingAssessment,
} from "../types";

/**
 * Local Satellite store in MMKV:
 *  - an offline **cache** of the last-seen API dashboard / history / timeline
 *    (per farm), and
 *  - the **local-provider** sessions (per farm) used in dev / without a backend.
 */
function read<T>(key: string): T {
  return (appStorage.getJSON<T>(key) ?? {}) as T;
}

export const satelliteStorage = {
  cacheDashboard(farmId: string, dashboard: SatelliteDashboard): void {
    const map = read<Record<string, SatelliteDashboard>>(
      SAT_DASHBOARD_CACHE_KEY,
    );
    map[farmId] = dashboard;
    appStorage.setJSON(SAT_DASHBOARD_CACHE_KEY, map);
  },
  getCachedDashboard(farmId: string): SatelliteDashboard | null {
    return (
      read<Record<string, SatelliteDashboard>>(SAT_DASHBOARD_CACHE_KEY)[
        farmId
      ] ?? null
    );
  },
  cacheHistory(farmId: string, items: SatelliteHistoryEntry[]): void {
    const map = read<Record<string, SatelliteHistoryEntry[]>>(
      SAT_HISTORY_CACHE_KEY,
    );
    map[farmId] = items;
    appStorage.setJSON(SAT_HISTORY_CACHE_KEY, map);
  },
  getCachedHistory(farmId: string): SatelliteHistoryEntry[] | null {
    return (
      read<Record<string, SatelliteHistoryEntry[]>>(SAT_HISTORY_CACHE_KEY)[
        farmId
      ] ?? null
    );
  },
  cacheTimeline(key: string, timeline: SatelliteTimeline): void {
    const map = read<Record<string, SatelliteTimeline>>(SAT_TIMELINE_CACHE_KEY);
    map[key] = timeline;
    appStorage.setJSON(SAT_TIMELINE_CACHE_KEY, map);
  },
  getCachedTimeline(key: string): SatelliteTimeline | null {
    return (
      read<Record<string, SatelliteTimeline>>(SAT_TIMELINE_CACHE_KEY)[key] ??
      null
    );
  },
  cacheWaterlogging(farmId: string, assessment: WaterloggingAssessment): void {
    const map = read<Record<string, WaterloggingAssessment>>(
      SAT_WATERLOGGING_CACHE_KEY,
    );
    map[farmId] = assessment;
    appStorage.setJSON(SAT_WATERLOGGING_CACHE_KEY, map);
  },
  getCachedWaterlogging(farmId: string): WaterloggingAssessment | null {
    return (
      read<Record<string, WaterloggingAssessment>>(SAT_WATERLOGGING_CACHE_KEY)[
        farmId
      ] ?? null
    );
  },
  cacheWaterloggingHistory(
    farmId: string,
    items: WaterloggingAssessment[],
  ): void {
    const map = read<Record<string, WaterloggingAssessment[]>>(
      SAT_WATERLOGGING_HISTORY_CACHE_KEY,
    );
    map[farmId] = items;
    appStorage.setJSON(SAT_WATERLOGGING_HISTORY_CACHE_KEY, map);
  },
  getCachedWaterloggingHistory(
    farmId: string,
  ): WaterloggingAssessment[] | null {
    return (
      read<Record<string, WaterloggingAssessment[]>>(
        SAT_WATERLOGGING_HISTORY_CACHE_KEY,
      )[farmId] ?? null
    );
  },

  // --- Local provider store: sessions per farm (newest first) ---
  localSessions(farmId: string): SatelliteSession[] {
    return (
      read<Record<string, SatelliteSession[]>>(SAT_LOCAL_KEY)[farmId] ?? []
    );
  },
  addLocalSession(farmId: string, session: SatelliteSession): void {
    const map = read<Record<string, SatelliteSession[]>>(SAT_LOCAL_KEY);
    map[farmId] = [session, ...(map[farmId] ?? [])];
    appStorage.setJSON(SAT_LOCAL_KEY, map);
  },

  clear(): void {
    appStorage.remove(SAT_DASHBOARD_CACHE_KEY);
    appStorage.remove(SAT_HISTORY_CACHE_KEY);
    appStorage.remove(SAT_TIMELINE_CACHE_KEY);
    appStorage.remove(SAT_WATERLOGGING_CACHE_KEY);
    appStorage.remove(SAT_WATERLOGGING_HISTORY_CACHE_KEY);
    appStorage.remove(SAT_LOCAL_KEY);
  },
};
