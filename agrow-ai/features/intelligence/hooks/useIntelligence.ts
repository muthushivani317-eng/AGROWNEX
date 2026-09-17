import { useMutation, useQuery } from '@tanstack/react-query';

import { queryClient } from '@/lib/queryClient';

import { intelligenceKeys } from '../constants';
import { getIntelligenceProvider } from '../services/intelligenceProvider';
import { intelligenceOutbox, isOfflineError } from '../services/intelligenceSync';

const STALE = 5 * 60 * 1000;

export function useIntelligenceDashboard(farmId: string | undefined) {
  return useQuery({
    queryKey: intelligenceKeys.dashboard(farmId ?? ''),
    enabled: Boolean(farmId),
    queryFn: () => getIntelligenceProvider().dashboard(farmId as string),
    staleTime: STALE,
  });
}

export function useIntelligenceHistory(farmId: string | undefined) {
  return useQuery({
    queryKey: intelligenceKeys.history(farmId ?? ''),
    enabled: Boolean(farmId),
    queryFn: () => getIntelligenceProvider().history(farmId as string),
    staleTime: STALE,
  });
}

export function useIntelligenceReport(reportId: string | undefined) {
  return useQuery({
    queryKey: intelligenceKeys.report(reportId ?? ''),
    enabled: Boolean(reportId),
    queryFn: () => getIntelligenceProvider().getReport(reportId as string),
    staleTime: STALE,
  });
}

function invalidateFarm(farmId: string): void {
  void queryClient.invalidateQueries({ queryKey: intelligenceKeys.dashboard(farmId) });
  void queryClient.invalidateQueries({ queryKey: intelligenceKeys.history(farmId) });
}

export interface RefreshResult {
  offline: boolean;
}

export function useRefreshIntelligence() {
  return useMutation<RefreshResult, unknown, { farmId: string }>({
    mutationFn: async ({ farmId }) => {
      try {
        await getIntelligenceProvider().refresh(farmId);
        return { offline: false };
      } catch (error) {
        if (isOfflineError(error)) {
          intelligenceOutbox.enqueue(farmId);
          return { offline: true };
        }
        throw error;
      }
    },
    onSuccess: (_res, vars) => invalidateFarm(vars.farmId),
  });
}
