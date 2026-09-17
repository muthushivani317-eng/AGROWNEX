import { useMemo } from 'react';

import { useAuth } from '@/features/auth';
import { useFarmSync } from '@/features/farm';
import { useSelectedFarm, useWeather } from '@/features/weather';

import { buildRecentActivity } from '../utils/activity';
import { generateTasks } from '../utils/tasks';

/**
 * Aggregates everything the Home Dashboard needs from the existing modules
 * (auth, farms, weather). Shares React Query caches and the persisted farm
 * selection with the Weather screen, so switching a farm is consistent app-wide.
 */
export function useDashboard() {
  const { user } = useAuth();
  useFarmSync(); // drain any offline farm mutations on reconnect

  const {
    farms,
    selected,
    select,
    isLoading: farmsLoading,
    isError: farmsError,
    refetch: refetchFarms,
  } = useSelectedFarm();

  const hasCoords = selected?.latitude != null && selected?.longitude != null;
  const weatherQuery = selected
    ? {
        farmId: selected.id,
        latitude: selected.latitude,
        longitude: selected.longitude,
        name: selected.name,
      }
    : {};
  const {
    data: weather,
    isLoading: weatherLoading,
    isError: weatherError,
    refetch: refetchWeather,
  } = useWeather(weatherQuery, Boolean(selected) && hasCoords);

  const tasks = useMemo(
    () => generateTasks(weather ?? null, selected),
    [weather, selected],
  );
  const activity = useMemo(
    () => buildRecentActivity(farms, user, weather ?? null),
    [farms, user, weather],
  );

  const refresh = () => {
    void refetchFarms();
    if (hasCoords) void refetchWeather();
  };

  return {
    user,
    farms,
    selected,
    select,
    hasCoords,
    weather: weather ?? null,
    tasks,
    activity,
    farmsLoading,
    farmsError,
    weatherLoading,
    weatherError,
    refresh,
  };
}
