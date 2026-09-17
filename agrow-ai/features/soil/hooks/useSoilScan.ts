import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/features/auth/store/authStore";
import { api } from "@/services/apiClient";
import { endpoints } from "@/services/endpoints";
import type { ApiSoilScan, Paginated } from "../types";
import { mapSoilScan } from "../services/soilScan";
import { soilStorage } from "../services/soilStorage";
import { isOfflineError } from "../services/soilSync";
import { getSatelliteProvider } from "@/features/satellite/services/satelliteProvider";
import { satelliteKeys } from "@/features/satellite/constants";
import { refreshWaterloggingAssessment } from "@/features/satellite/services/apiSatelliteProvider";
import {
  runSoilScanWithSatellite,
  type SoilScanPhase,
} from "../services/soilScanOrchestrator";

const scanKey = (userId: string, farmId: string) =>
  ["soil-scan", userId, farmId] as const;

export function useSoilScan(farmId?: string) {
  const userId = useAuthStore((state) => state.user?.id ?? "anonymous");
  return useQuery({
    queryKey: scanKey(userId, farmId ?? ""),
    enabled: Boolean(farmId && userId !== "anonymous"),
    queryFn: async () => {
      try {
        const scan = mapSoilScan(
          await api.get<ApiSoilScan>(endpoints.soil.scanLatest, {
            params: { farm_id: farmId },
          }),
        );
        scan.cacheState = "live";
        soilStorage.cacheScan(userId, farmId as string, scan);
        return scan;
      } catch (error) {
        const cached = soilStorage.getCachedScan(userId, farmId as string);
        if (cached && isOfflineError(error))
          return { ...cached, cacheState: "cached" as const };
        throw error;
      }
    },
  });
}

export function useRunSoilScan(
  farmId?: string,
  onPhaseChange?: (phase: SoilScanPhase) => void,
) {
  const userId = useAuthStore((state) => state.user?.id ?? "anonymous");
  const client = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      if (!farmId) throw new Error("farm_required");
      const satellite = getSatelliteProvider();
      const scan = await runSoilScanWithSatellite({
        getDashboard: () => satellite.dashboard(farmId, true),
        refreshSatellite: async (hasPolygon) => {
          await satellite.refresh(farmId, hasPolygon);
          await Promise.all([
            client.invalidateQueries({ queryKey: satelliteKeys.dashboard(farmId) }),
            client.invalidateQueries({ queryKey: satelliteKeys.history(farmId) }),
            client.invalidateQueries({ queryKey: satelliteKeys.alerts(farmId) }),
          ]);
        },
        refreshWaterlogging: async () => {
          await refreshWaterloggingAssessment(farmId);
          await Promise.all([
            client.invalidateQueries({ queryKey: satelliteKeys.waterlogging(farmId) }),
            client.invalidateQueries({ queryKey: satelliteKeys.waterloggingHistory(farmId) }),
          ]);
        },
        runSoilScan: async () =>
          mapSoilScan(
            await api.post<ApiSoilScan>(endpoints.soil.scan, undefined, {
              params: { farm_id: farmId },
            }),
          ),
        onPhaseChange,
      });
      scan.cacheState = "live";
      soilStorage.cacheScan(userId, farmId, scan);
      return scan;
    },
    onSuccess: (scan) => {
      client.setQueryData(scanKey(userId, scan.farmId), scan);
      void client.invalidateQueries({
        queryKey: ["soil-scan-history", userId, scan.farmId],
      });
    },
    onSettled: () => onPhaseChange?.("idle"),
  });
}

export function useSoilScanHistory(farmId?: string) {
  const userId = useAuthStore((state) => state.user?.id ?? "anonymous");
  return useQuery({
    queryKey: ["soil-scan-history", userId, farmId],
    enabled: Boolean(farmId && userId !== "anonymous"),
    queryFn: async () => {
      try {
        const page = await api.get<Paginated<ApiSoilScan>>(
          endpoints.soil.scanHistory,
          {
            params: { farm_id: farmId },
          },
        );
        const scans = page.items.map(mapSoilScan);
        soilStorage.cacheScanHistory(userId, farmId as string, scans);
        return scans;
      } catch (error) {
        const cached = soilStorage.getCachedScanHistory(
          userId,
          farmId as string,
        );
        if (cached && isOfflineError(error))
          return cached.map((scan) => ({
            ...scan,
            cacheState: "cached" as const,
          }));
        throw error;
      }
    },
  });
}
