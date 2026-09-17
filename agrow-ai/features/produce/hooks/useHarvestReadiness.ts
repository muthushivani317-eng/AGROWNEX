import { useMutation, useQuery } from "@tanstack/react-query";

import { queryClient } from "@/lib/queryClient";

import {
  confirmReadiness,
  evaluateReadiness,
  getCurrentReadiness,
  getReadinessHistory,
} from "../services/harvestReadinessApi";

const key = (farmId?: string | null, cycleId?: string | null) => [
  "harvest-readiness",
  farmId,
  cycleId,
];

export function useHarvestReadiness(
  farmId?: string | null,
  cycleId?: string | null,
) {
  return useQuery({
    queryKey: key(farmId, cycleId),
    queryFn: () => getCurrentReadiness(farmId!, cycleId!),
    enabled: Boolean(farmId && cycleId),
    retry: false,
  });
}

export function useEvaluateHarvestReadiness() {
  return useMutation({
    mutationFn: ({ farmId, cycleId }: { farmId: string; cycleId: string }) =>
      evaluateReadiness(farmId, cycleId),
    retry: false,
    onSuccess: (value) => {
      queryClient.setQueryData(key(value.farmId!, value.cropCycleId!), value);
      void queryClient.invalidateQueries({ queryKey: ["harvest-readiness-history", value.id] });
    },
  });
}

export function useConfirmHarvestReadiness() {
  return useMutation({
    mutationFn: ({ id, ready }: { id: string; ready: boolean }) =>
      confirmReadiness(id, ready),
    retry: false,
    onSuccess: (value) => {
      queryClient.setQueryData(key(value.farmId!, value.cropCycleId!), value);
      void queryClient.invalidateQueries({
        queryKey: ["harvest-readiness-history", value.id],
      });
    },
  });
}

export function useHarvestReadinessHistory(readinessId?: string | null) {
  return useQuery({
    queryKey: ["harvest-readiness-history", readinessId],
    queryFn: () => getReadinessHistory(readinessId!),
    enabled: Boolean(readinessId),
  });
}
