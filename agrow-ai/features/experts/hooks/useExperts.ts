import { useQuery } from '@tanstack/react-query';

import { DEFAULT_PAGE_SIZE, expertKeys } from '../constants';
import { getExpertProvider } from '../services/expertProvider';
import { expertListKey } from '../services/expertStorage';
import type { ExpertListParams } from '../types';

const STALE = 10 * 60 * 1000;

export function useExpertList(params: ExpertListParams = {}, enabled = true) {
  return useQuery({
    queryKey: expertKeys.list(expertListKey(params as Record<string, unknown>)),
    enabled,
    queryFn: () =>
      getExpertProvider().listExperts({ pageSize: DEFAULT_PAGE_SIZE, ...params }),
    staleTime: STALE,
  });
}

export function useExpertDetail(id: string | undefined) {
  return useQuery({
    queryKey: expertKeys.detail(id ?? ''),
    enabled: Boolean(id),
    queryFn: () => getExpertProvider().getExpert(id as string),
    staleTime: STALE,
  });
}
