import { useMutation, useQuery } from '@tanstack/react-query';

import { queryClient } from '@/lib/queryClient';

import { memoryKeys } from '../constants';
import { getMemoryProvider } from '../services/memoryProvider';
import { isOfflineError, memoryOutbox } from '../services/memorySync';
import type { MemoryHistoryFilter } from '../types';

const STALE = 5 * 60 * 1000;

function filterKey(filter?: MemoryHistoryFilter): string {
  if (!filter) return 'all';
  return JSON.stringify({
    s: filter.sourceModule ?? '',
    se: filter.season ?? '',
    c: filter.crop ?? '',
    i: filter.importance ?? '',
    q: filter.q ?? '',
  });
}

export function useMemoryDashboard(farmId: string | undefined) {
  return useQuery({
    queryKey: memoryKeys.dashboard(farmId ?? ''),
    enabled: Boolean(farmId),
    queryFn: () => getMemoryProvider().dashboard(farmId as string),
    staleTime: STALE,
  });
}

export function useMemoryHistory(farmId: string | undefined, filter?: MemoryHistoryFilter) {
  return useQuery({
    queryKey: memoryKeys.history(farmId ?? '', filterKey(filter)),
    enabled: Boolean(farmId),
    queryFn: () => getMemoryProvider().history(farmId as string, filter),
    staleTime: STALE,
  });
}

export function useMemorySummary(farmId: string | undefined) {
  return useQuery({
    queryKey: memoryKeys.summary(farmId ?? ''),
    enabled: Boolean(farmId),
    queryFn: () => getMemoryProvider().summary(farmId as string),
    staleTime: STALE,
  });
}

export function useMemoryDetail(id: string | undefined) {
  return useQuery({
    queryKey: memoryKeys.detail(id ?? ''),
    enabled: Boolean(id),
    queryFn: () => getMemoryProvider().getMemory(id as string),
    staleTime: STALE,
  });
}

function invalidateFarm(farmId: string): void {
  void queryClient.invalidateQueries({ queryKey: memoryKeys.dashboard(farmId) });
  void queryClient.invalidateQueries({ queryKey: memoryKeys.summary(farmId) });
  void queryClient.invalidateQueries({ queryKey: ['memory', 'history', farmId] });
}

export interface RebuildResult {
  offline: boolean;
  created?: number;
}

export function useRebuildMemory() {
  return useMutation<RebuildResult, unknown, { farmId: string }>({
    mutationFn: async ({ farmId }) => {
      try {
        const res = await getMemoryProvider().rebuild(farmId);
        return { offline: false, created: res.created };
      } catch (error) {
        if (isOfflineError(error)) {
          memoryOutbox.enqueue(farmId);
          return { offline: true };
        }
        throw error;
      }
    },
    onSuccess: (_res, vars) => invalidateFarm(vars.farmId),
  });
}
