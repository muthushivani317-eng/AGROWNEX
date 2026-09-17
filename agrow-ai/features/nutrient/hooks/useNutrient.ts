import { useMutation, useQuery } from '@tanstack/react-query';

import { queryClient } from '@/lib/queryClient';

import { nutrientKeys } from '../constants';
import { getNutrientProvider } from '../services/nutrientProvider';
import { isOfflineError, nutrientOutbox } from '../services/nutrientSync';
import type { AnalyzeInput, NutrientReport } from '../types';

const STALE = 5 * 60 * 1000;

export interface AnalyzeResult {
  report: NutrientReport | null;
  offline: boolean;
}

/** Analyse a validated crop photo → corroborated nutrient report. */
export function useAnalyzeNutrient() {
  return useMutation<AnalyzeResult, unknown, AnalyzeInput>({
    mutationFn: async (input) => {
      try {
        const report = await getNutrientProvider().analyze(input);
        return { report, offline: false };
      } catch (error) {
        if (isOfflineError(error)) {
          nutrientOutbox.enqueue(input);
          return { report: null, offline: true };
        }
        throw error;
      }
    },
    onSuccess: (result, vars) => {
      void queryClient.invalidateQueries({ queryKey: nutrientKeys.history(vars.farmId) });
      void queryClient.invalidateQueries({ queryKey: nutrientKeys.latest(vars.farmId) });
      void queryClient.invalidateQueries({
        queryKey: nutrientKeys.recommendations(vars.farmId),
      });
    },
  });
}

export function useNutrientHistory(farmId: string | undefined) {
  return useQuery({
    queryKey: nutrientKeys.history(farmId ?? ''),
    enabled: Boolean(farmId),
    queryFn: () => getNutrientProvider().history(farmId as string),
    staleTime: STALE,
  });
}

export function useNutrientLatest(farmId: string | undefined) {
  return useQuery({
    queryKey: nutrientKeys.latest(farmId ?? ''),
    enabled: Boolean(farmId),
    queryFn: () => getNutrientProvider().latest(farmId as string),
    staleTime: STALE,
  });
}

export function useNutrientRecommendations(farmId: string | undefined) {
  return useQuery({
    queryKey: nutrientKeys.recommendations(farmId ?? ''),
    enabled: Boolean(farmId),
    queryFn: () => getNutrientProvider().recommendations(farmId as string),
    staleTime: STALE,
  });
}

export function useNutrientReport(id: string | null) {
  return useQuery({
    queryKey: nutrientKeys.report(id ?? 'none'),
    enabled: Boolean(id),
    queryFn: () => getNutrientProvider().getReport(id as string),
  });
}
