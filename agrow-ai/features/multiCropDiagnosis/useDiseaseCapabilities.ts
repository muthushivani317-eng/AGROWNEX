import { useQuery } from '@tanstack/react-query';

import { buildProfile } from '@/config/env';
import { fetchDiseaseCapabilities } from './cropRegistry';

export const diseaseCapabilityKeys = {
  current: (profile: string, sessionKey: string) =>
    ['disease-capabilities', profile, sessionKey] as const,
};

export function useDiseaseCapabilities(enabled: boolean, sessionKey = 'anonymous') {
  return useQuery({
    queryKey: diseaseCapabilityKeys.current(buildProfile, sessionKey),
    queryFn: () => fetchDiseaseCapabilities(buildProfile),
    enabled,
    staleTime: 30_000,
    retry: false,
    refetchOnMount: 'always',
    refetchOnReconnect: true,
  });
}
