import { useMutation, useQuery } from '@tanstack/react-query';

import { queryClient } from '@/lib/queryClient';

import { diseaseKeys } from '../constants';
import { getDiseaseProvider } from '../services/diseaseProvider';
/** Past diagnoses (most recent first). */
export function useDiseaseHistory(farmId?: string | null, unassignedOnly = false) {
  return useQuery({
    queryKey: diseaseKeys.history(farmId ?? null, unassignedOnly),
    queryFn: () => getDiseaseProvider().listReports(farmId, unassignedOnly),
  });
}

export function useDiseaseReport(id: string | null) {
  return useQuery({
    queryKey: diseaseKeys.report(id ?? 'none'),
    enabled: Boolean(id),
    queryFn: () => getDiseaseProvider().getReport(id as string),
  });
}

export function useDeleteReport() {
  return useMutation({
    mutationFn: (id: string) => getDiseaseProvider().deleteReport(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: diseaseKeys.all });
    },
  });
}
