import { appStorage } from '@/lib/storage';

import { WEATHER_CACHE_PREFIX } from '../constants';
import type { WeatherBundle } from '../types';

/**
 * Offline cache for the last successful weather bundle per farm (docs: offline
 * cache). Keyed by farm id (or a coordinate key for ad-hoc lookups).
 */
function keyFor(id: string): string {
  return `${WEATHER_CACHE_PREFIX}${id}`;
}

export const weatherCache = {
  get(id: string): WeatherBundle | null {
    return appStorage.getJSON<WeatherBundle>(keyFor(id));
  },
  set(id: string, bundle: WeatherBundle): void {
    appStorage.setJSON(keyFor(id), bundle);
  },
};
