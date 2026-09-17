import { useMutation, useQuery } from '@tanstack/react-query';

import { useAuthStore } from '@/features/auth/store/authStore';
import { offlineQueue } from '@/lib/db';
import { queryClient } from '@/lib/queryClient';
import { endpoints } from '@/services/endpoints';
import { ApiError } from '@/types';
import { uuid } from '@/utils/id';

import { profileKeys } from '../constants';
import {
  profileInputToApi,
  profileInputToUserPatch,
  userToProfile,
} from '../services/profileMapper';
import { getProfileProvider } from '../services/profileProvider';
import type { FarmerProfile, FarmerProfileInput } from '../types';

/** Load the current farmer's profile (server state; cached by React Query). */
export function useProfile() {
  return useQuery({
    queryKey: profileKeys.me,
    queryFn: () => getProfileProvider().getProfile(),
  });
}

export interface UpdateProfileResult {
  profile: FarmerProfile;
  offline: boolean;
}

/**
 * Save the farmer's profile. On a network failure the edit is persisted locally
 * and queued in the offline outbox so it is never lost, then synced later
 * (docs/FRONTEND_ARCHITECTURE.md → OFFLINE STRATEGY).
 */
export function useUpdateProfile() {
  return useMutation<UpdateProfileResult, unknown, FarmerProfileInput>({
    mutationFn: async (input) => {
      try {
        const profile = await getProfileProvider().updateProfile(input);
        return { profile, offline: false };
      } catch (e) {
        if (e instanceof ApiError && e.isNetwork) {
          await offlineQueue.enqueue({
            id: uuid(),
            endpoint: endpoints.farmers.me,
            method: 'PUT',
            payload: profileInputToApi(input),
            entityType: 'farmer_profile',
          });
          await useAuthStore.getState().updateUser(profileInputToUserPatch(input));
          const user = useAuthStore.getState().user;
          const profile = user
            ? userToProfile(user)
            : { ...input, phone: null, email: null };
          return { profile, offline: true };
        }
        throw e;
      }
    },
    onSuccess: ({ profile }) => {
      // Mirror core fields into the auth store (app-wide source of truth) and
      // refresh any cached profile queries.
      void useAuthStore.getState().updateUser(profileInputToUserPatch(profile));
      queryClient.setQueryData(profileKeys.me, profile);
    },
  });
}
