import { useMutation, useQuery } from "@tanstack/react-query";
import {
  getWaterloggingAssessment,
  getWaterloggingHistory,
  refreshWaterloggingAssessment,
  repairSatelliteImages,
  getSatelliteReadiness,
} from "../services/apiSatelliteProvider";

import { queryClient } from "@/lib/queryClient";

import { satelliteKeys } from "../constants";
import { getSatelliteProvider } from "../services/satelliteProvider";
import { isOfflineError, satelliteOutbox } from "../services/satelliteSync";

const STALE = 5 * 60 * 1000;

export function useSatelliteReadiness() {
  return useQuery({
    queryKey: ["satellite", "readiness"],
    queryFn: getSatelliteReadiness,
    staleTime: STALE,
  });
}

export function useSatelliteDashboard(
  farmId: string | undefined,
  hasPolygon = true,
) {
  return useQuery({
    queryKey: satelliteKeys.dashboard(farmId ?? ""),
    enabled: Boolean(farmId),
    queryFn: () =>
      getSatelliteProvider().dashboard(farmId as string, hasPolygon),
    staleTime: STALE,
  });
}

export function useWaterloggingAssessment(farmId: string | undefined) {
  return useQuery({
    queryKey: satelliteKeys.waterlogging(farmId ?? ""),
    queryFn: () => getWaterloggingAssessment(farmId!),
    enabled: Boolean(farmId),
  });
}

export function useWaterloggingHistory(farmId: string | undefined) {
  return useQuery({
    queryKey: satelliteKeys.waterloggingHistory(farmId ?? ""),
    queryFn: () => getWaterloggingHistory(farmId!),
    enabled: Boolean(farmId),
    staleTime: STALE,
  });
}

export function useRefreshWaterlogging() {
  return useMutation({
    mutationFn: (farmId: string) => refreshWaterloggingAssessment(farmId),
    onSuccess: (_result, farmId) => {
      void queryClient.invalidateQueries({
        queryKey: satelliteKeys.waterlogging(farmId),
      });
      void queryClient.invalidateQueries({
        queryKey: satelliteKeys.waterloggingHistory(farmId),
      });
    },
  });
}

export function useSatelliteHistory(farmId: string | undefined) {
  return useQuery({
    queryKey: satelliteKeys.history(farmId ?? ""),
    enabled: Boolean(farmId),
    queryFn: () => getSatelliteProvider().history(farmId as string),
    staleTime: STALE,
  });
}

export function useSatelliteTimeline(
  farmId: string | undefined,
  range: string,
) {
  return useQuery({
    queryKey: satelliteKeys.timeline(farmId ?? "", range),
    enabled: Boolean(farmId),
    queryFn: () => getSatelliteProvider().timeline(farmId as string, range),
    staleTime: STALE,
  });
}

export function useSatelliteAlerts(farmId: string | undefined) {
  return useQuery({
    queryKey: satelliteKeys.alerts(farmId ?? ""),
    enabled: Boolean(farmId),
    queryFn: () => getSatelliteProvider().alerts(farmId as string),
    staleTime: STALE,
  });
}

function invalidateFarm(farmId: string): void {
  void queryClient.invalidateQueries({
    queryKey: satelliteKeys.dashboard(farmId),
  });
  void queryClient.invalidateQueries({
    queryKey: satelliteKeys.history(farmId),
  });
  void queryClient.invalidateQueries({
    queryKey: satelliteKeys.alerts(farmId),
  });
}

export interface RefreshResult {
  offline: boolean;
}

export function useRefreshSatellite() {
  return useMutation<
    RefreshResult,
    unknown,
    { farmId: string; hasPolygon: boolean }
  >({
    mutationFn: async ({ farmId, hasPolygon }) => {
      try {
        await getSatelliteProvider().refresh(farmId, hasPolygon);
        return { offline: false };
      } catch (error) {
        if (isOfflineError(error)) {
          satelliteOutbox.enqueue(farmId);
          return { offline: true };
        }
        throw error;
      }
    },
    onSuccess: (_res, vars) => invalidateFarm(vars.farmId),
  });
}

export function useRepairSatelliteImages() {
  return useMutation({
    mutationFn: (farmId: string) => repairSatelliteImages(farmId),
    onSuccess: (_result, farmId) => {
      // Rendering runs in the worker. Refresh while it replaces the broken URLs.
      for (const delay of [2000, 6000, 12000, 25000, 45000]) {
        setTimeout(() => {
          void queryClient.invalidateQueries({
            queryKey: satelliteKeys.dashboard(farmId),
          });
        }, delay);
      }
    },
  });
}
