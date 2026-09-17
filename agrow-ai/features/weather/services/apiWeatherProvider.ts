import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';

import type { ApiWeatherBundle, WeatherBundle, WeatherQuery } from '../types';
import { apiToBundle } from './weatherMapper';
import type { WeatherProvider } from './weatherProvider';

/**
 * Backend weather provider (docs/API_CONTRACT.md → WEATHER MODULE). The backend
 * resolves the farm's GPS, calls Open-Meteo, caches, and returns the bundle.
 */
export const apiWeatherProvider: WeatherProvider = {
  async getWeather(query: WeatherQuery): Promise<WeatherBundle> {
    // Prefer the coordinates already resolved for the selected farm. This keeps
    // weather available while a farm edit is still syncing to the backend.
    const hasCoordinates = query.latitude != null && query.longitude != null;
    const params = hasCoordinates
      ? { latitude: query.latitude, longitude: query.longitude }
      : { farm_id: query.farmId };
    const dto = await api.get<ApiWeatherBundle>(endpoints.weather.bundle, { params });
    return apiToBundle(dto);
  },
};
