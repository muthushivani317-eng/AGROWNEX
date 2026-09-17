import { useState } from 'react';

import { useFarms, type FarmSummary } from '@/features/farm';
import { appStorage } from '@/lib/storage';

import { SELECTED_FARM_KEY } from '../constants';

/**
 * Farm selection for the Weather screen: lists the farmer's farms and remembers
 * the chosen one (docs: support multiple farms, users can switch farms).
 */
export function useSelectedFarm() {
  const { data, error, isLoading, isError, refetch } = useFarms({}, {
    refetchOnMount: 'always',
  });
  const farms: FarmSummary[] = data?.items ?? [];

  const [selectedId, setSelectedId] = useState<string | null>(() =>
    appStorage.getString(SELECTED_FARM_KEY),
  );

  const select = (id: string) => {
    appStorage.set(SELECTED_FARM_KEY, id);
    setSelectedId(id);
  };

  const selected: FarmSummary | null =
    farms.find((f) => f.id === selectedId) ?? farms[0] ?? null;

  return { farms, selected, select, error, isLoading, isError, refetch };
}
