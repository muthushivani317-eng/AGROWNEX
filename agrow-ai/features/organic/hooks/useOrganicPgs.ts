import { useMutation, useQuery } from '@tanstack/react-query';
import { queryClient } from '@/lib/queryClient';
import { organicKeys } from '../constants';
import {
  organicPgsApi,
  type PgsChecklistInput,
} from '../services/organicPgsApi';

export function useOrganicPgsStatus(farmId: string) {
  return useQuery({
    queryKey: organicKeys.pgsStatus(farmId),
    queryFn: () => organicPgsApi.getStatus(farmId),
    enabled: Boolean(farmId),
  });
}

export function useUpdatePgsChecklist(farmId: string) {
  return useMutation({
    mutationFn: (input: PgsChecklistInput) =>
      organicPgsApi.updateChecklist(farmId, input),
    onSuccess: () =>
      void queryClient.invalidateQueries({
        queryKey: organicKeys.pgsStatus(farmId),
      }),
  });
}

export function useOrganicPeerAssignments() {
  return useQuery({
    queryKey: organicKeys.pgsPeerAssignments,
    queryFn: () => organicPgsApi.listPeerAssignments(),
  });
}

export function useSubmitPeerAppraisal() {
  return useMutation({
    mutationFn: ({ appraisalId, note }: { appraisalId: string; note: string }) =>
      organicPgsApi.submitPeerAppraisal(appraisalId, note),
    onSuccess: () =>
      void queryClient.invalidateQueries({
        queryKey: organicKeys.pgsPeerAssignments,
      }),
  });
}
