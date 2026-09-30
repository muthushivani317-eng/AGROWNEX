import { useQuery } from '@tanstack/react-query';

import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';

import type { FarmCatalog } from '../components/onboardingData';

export function useFarmCatalog() {
  return useQuery({
    queryKey: ['farmCatalog'],
    queryFn: () => api.get<FarmCatalog>(endpoints.farmers.farmCatalog),
    staleTime: 30 * 60 * 1000,
  });
}
