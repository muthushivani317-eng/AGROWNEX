import { useQuery } from "@tanstack/react-query";

import {
  WEATHER_REFRESH_MS,
  WEATHER_STALE_MS,
  weatherKeys,
} from "../constants";
import { getWeatherProvider } from "../services/weatherProvider";
import { weatherCache } from "../services/weatherCache";
import type { WeatherQuery } from "../types";

/**
 * Load weather for a farm (or coordinates). Background-refreshes on an interval
 * and on reconnect; on a network failure it falls back to the last cached bundle
 * (docs: caching, offline cache, background refresh).
 */
export function useWeather(query: WeatherQuery, enabled: boolean) {
  const id = query.farmId ?? `${query.latitude ?? ""},${query.longitude ?? ""}`;
  return useQuery({
    queryKey: weatherKeys.farm(id),
    enabled,
    staleTime: WEATHER_STALE_MS,
    refetchInterval: WEATHER_REFRESH_MS,
    refetchOnReconnect: true,
    queryFn: async () => {
      try {
        const bundle = await getWeatherProvider().getWeather(query);
        const fresh = bundle;
        weatherCache.set(id, fresh);
        return fresh;
      } catch (error) {
        const cached = weatherCache.get(id);
        if (cached) return { ...cached, isCached: true }; // offline fallback
        throw error;
      }
    },
  });
}
