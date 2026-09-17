import { useMutation, useQuery } from '@tanstack/react-query';

import { queryClient } from '@/lib/queryClient';

import { soilKeys } from '../constants';
import { getSoilProvider } from '../services/soilProvider';
import { isOfflineError, soilOutbox } from '../services/soilSync';
import type { SoilReportInput } from '../types';

const STALE = 5 * 60 * 1000;

export function useSoilDashboard(farmId: string | undefined, soilTypeHint?: string | null) {
  return useQuery({
    queryKey: soilKeys.dashboard(farmId ?? ''),
    enabled: Boolean(farmId),
    queryFn: () => getSoilProvider().dashboard(farmId as string, soilTypeHint),
    staleTime: STALE,
  });
}

export function useSoilHistory(farmId: string | undefined) {
  return useQuery({
    queryKey: soilKeys.history(farmId ?? ''),
    enabled: Boolean(farmId),
    queryFn: () => getSoilProvider().history(farmId as string),
    staleTime: STALE,
  });
}

export function useSoilRecommendations(
  farmId: string | undefined,
  soilTypeHint?: string | null,
) {
  return useQuery({
    queryKey: soilKeys.recommendations(farmId ?? ''),
    enabled: Boolean(farmId),
    queryFn: () => getSoilProvider().recommendations(farmId as string, soilTypeHint),
    staleTime: STALE,
  });
}

function invalidateFarm(farmId: string): void {
  void queryClient.invalidateQueries({ queryKey: soilKeys.dashboard(farmId) });
  void queryClient.invalidateQueries({ queryKey: soilKeys.history(farmId) });
  void queryClient.invalidateQueries({ queryKey: soilKeys.recommendations(farmId) });
}

export interface SubmitResult {
  offline: boolean;
}

export function useSubmitSoilReport() {
  return useMutation<SubmitResult, unknown, SoilReportInput>({
    mutationFn: async (input) => {
      try {
        await getSoilProvider().submitReport(input);
        return { offline: false };
      } catch (error) {
        if (isOfflineError(error)) {
          soilOutbox.enqueue(input);
          return { offline: true };
        }
        throw error;
      }
    },
    onSuccess: (_res, input) => invalidateFarm(input.farmId),
  });
}
