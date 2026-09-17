import { useMutation } from '@tanstack/react-query';

import { queryClient } from '@/lib/queryClient';
import { uuid } from '@/utils/id';

import { farmKeys } from '../constants';
import { assembleFarm } from '../services/farmMapper';
import { getFarmProvider } from '../services/farmProvider';
import { farmStorage } from '../services/farmStorage';
import { farmOutbox, isOfflineError } from '../services/farmSync';
import type { Farm, FarmInput } from '../types';

export interface FarmMutationResult {
  farm: Farm;
  offline: boolean;
}

/**
 * Create a farm. When offline, the farm is stored locally with a `pending`
 * status and queued in the outbox for sync on reconnect.
 */
export function useCreateFarm() {
  return useMutation<FarmMutationResult, unknown, FarmInput>({
    mutationFn: async (input) => {
      try {
        const farm = await getFarmProvider().create(input);
        farmStorage.upsert(farm);
        return { farm, offline: false };
      } catch (error) {
        if (isOfflineError(error)) {
          const farm = assembleFarm(input, { id: uuid(), syncStatus: 'pending' });
          farmStorage.upsert(farm);
          farmOutbox.enqueue({ op: 'create', farmId: farm.id, input });
          return { farm, offline: true };
        }
        throw error;
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: farmKeys.all });
    },
  });
}

export function useUpdateFarm(id: string) {
  return useMutation<FarmMutationResult, unknown, FarmInput>({
    mutationFn: async (input) => {
      try {
        const farm = await getFarmProvider().update(id, input);
        farmStorage.upsert(farm);
        return { farm, offline: false };
      } catch (error) {
        if (isOfflineError(error)) {
          const farm = assembleFarm(input, {
            id,
            existing: farmStorage.get(id) ?? undefined,
            syncStatus: 'pending',
          });
          farmStorage.upsert(farm);
          farmOutbox.enqueue({ op: 'update', farmId: id, input });
          return { farm, offline: true };
        }
        throw error;
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: farmKeys.all });
      void queryClient.invalidateQueries({ queryKey: farmKeys.detail(id) });
    },
  });
}

export function useDeleteFarm() {
  return useMutation<{ offline: boolean }, unknown, string>({
    mutationFn: async (id) => {
      try {
        await getFarmProvider().remove(id);
        farmStorage.remove(id);
        return { offline: false };
      } catch (error) {
        if (isOfflineError(error)) {
          farmStorage.remove(id);
          farmOutbox.enqueue({ op: 'delete', farmId: id });
          return { offline: true };
        }
        throw error;
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: farmKeys.all });
    },
  });
}
