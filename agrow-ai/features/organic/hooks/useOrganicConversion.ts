import { useMutation, useQuery } from '@tanstack/react-query';
import { queryClient } from '@/lib/queryClient';
import { organicKeys } from '../constants';
import {
  organicConversionApi,
  type OrganicCropCycleInput,
  type OrganicPlotInput,
} from '../services/organicConversionApi';

export function useOrganicPlots(farmId: string) {
  return useQuery({
    queryKey: organicKeys.plots(farmId),
    queryFn: () => organicConversionApi.listPlots(farmId),
  });
}

export function useCreateOrganicPlot(farmId: string) {
  return useMutation({
    mutationFn: (input: OrganicPlotInput) =>
      organicConversionApi.createPlot(farmId, input),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: organicKeys.plots(farmId) }),
  });
}

export function useOrganicCropCycles(plotId: string) {
  return useQuery({
    queryKey: organicKeys.cropCycles(plotId),
    queryFn: () => organicConversionApi.listCropCycles(plotId),
    enabled: Boolean(plotId),
  });
}

export function useCreateOrganicCropCycle(plotId: string) {
  return useMutation({
    mutationFn: (input: OrganicCropCycleInput) =>
      organicConversionApi.createCropCycle(plotId, input),
    onSuccess: () =>
      void queryClient.invalidateQueries({
        queryKey: organicKeys.cropCycles(plotId),
      }),
  });
}

export function useOrganicCropCyclePlan(cycleId: string | null) {
  return useQuery({
    queryKey: organicKeys.cropCyclePlan(cycleId ?? 'none'),
    queryFn: () => organicConversionApi.getCropCyclePlan(cycleId as string),
    enabled: Boolean(cycleId),
  });
}

export function useOrganicTodayTask(farmId: string) {
  return useQuery({
    queryKey: organicKeys.todayTask(farmId),
    queryFn: () => organicConversionApi.getTodayTasks(farmId),
    enabled: Boolean(farmId),
  });
}
