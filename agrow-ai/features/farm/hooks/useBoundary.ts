import { useMutation } from '@tanstack/react-query';

import { queryClient } from '@/lib/queryClient';

import { farmKeys } from '../constants';
import { computeBoundary } from '../services/farmMapper';
import { getFarmProvider } from '../services/farmProvider';
import { farmStorage } from '../services/farmStorage';
import { isOfflineError } from '../services/farmSync';
import type { BoundaryInput, FarmBoundary } from '../types';

export interface BoundaryMutationResult {
  boundary: FarmBoundary;
  offline: boolean;
}

/** Mirror a saved boundary into the local farm record (keeps area in sync). */
function mirrorBoundary(id: string, boundary: FarmBoundary): void {
  const cached = farmStorage.get(id);
  if (!cached) return;
  farmStorage.upsert({
    ...cached,
    boundary,
    areaHectares:
      cached.areaSource === 'auto' ? boundary.areaHectares : cached.areaHectares,
    updatedAt: new Date().toISOString(),
  });
}

/** Save a farm's boundary via the dedicated boundary endpoint. */
export function useUpdateBoundary(id: string) {
  return useMutation<BoundaryMutationResult, unknown, BoundaryInput>({
    mutationFn: async (input) => {
      try {
        const boundary = await getFarmProvider().updateBoundary(id, input);
        mirrorBoundary(id, boundary);
        return { boundary, offline: false };
      } catch (error) {
        if (isOfflineError(error)) {
          const boundary = computeBoundary(input);
          mirrorBoundary(id, boundary);
          return { boundary, offline: true };
        }
        throw error;
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: farmKeys.detail(id) });
      void queryClient.invalidateQueries({ queryKey: farmKeys.boundary(id) });
      void queryClient.invalidateQueries({ queryKey: farmKeys.all });
    },
  });
}
