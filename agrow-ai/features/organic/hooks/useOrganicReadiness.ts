import { useMutation, useQuery } from '@tanstack/react-query';
import { queryClient } from '@/lib/queryClient';
import { organicKeys } from '../constants';
import { organicReadinessApi } from '../services/organicReadinessApi';

/** Admin-approved readiness question set (or a "not ready yet" status -- see organic_mvp's own review workflow). */
export function useOrganicReadinessQuestions() {
  return useQuery({
    queryKey: organicKeys.readinessQuestions,
    queryFn: () => organicReadinessApi.getQuestions(),
  });
}

/** Submits one assessment. Online-only (first-run flow) -- no offline outbox, unlike the profile/practice hooks. */
export function useSubmitOrganicReadiness(farmId: string) {
  return useMutation({
    mutationFn: (answers: Record<string, string>) =>
      organicReadinessApi.submit(farmId, answers),
    onSuccess: () =>
      void queryClient.invalidateQueries({
        queryKey: organicKeys.readinessHistory(farmId),
      }),
  });
}
