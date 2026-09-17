import { useMutation, useQuery } from '@tanstack/react-query';

import { queryClient } from '@/lib/queryClient';

import { profileKeys } from '../constants';
import { getProfileProvider } from '../services/profileProvider';
import type { FarmerPreferences } from '../types';

/** Load the farmer's app preferences. */
export function usePreferences() {
  return useQuery({
    queryKey: profileKeys.preferences,
    queryFn: () => getProfileProvider().getPreferences(),
  });
}

/** Update one or more preference fields (partial patch). */
export function useUpdatePreferences() {
  return useMutation({
    mutationFn: (patch: Partial<FarmerPreferences>) =>
      getProfileProvider().updatePreferences(patch),
    onSuccess: (preferences) => {
      queryClient.setQueryData(profileKeys.preferences, preferences);
    },
  });
}
