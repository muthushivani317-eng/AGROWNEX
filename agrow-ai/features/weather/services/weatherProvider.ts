import { isBackendConfigured } from '@/config/env';
import { logger } from '@/lib/logger';

import type { WeatherBundle, WeatherQuery } from '../types';

/**
 * Weather data source contract. Backed by the AgrowAI weather API (Open-Meteo)
 * when configured, or a deterministic local mock otherwise — selected at runtime
 * (mirrors the auth/profile/farm providers) so the screen works in development.
 */
export interface WeatherProvider {
  getWeather(query: WeatherQuery): Promise<WeatherBundle>;
}

let provider: WeatherProvider | null = null;

export function getWeatherProvider(): WeatherProvider {
  if (provider) return provider;
  if (isBackendConfigured) {
    provider = require('./apiWeatherProvider').apiWeatherProvider as WeatherProvider;
    logger.info('weather', 'using api provider');
  } else {
    provider = require('./mockWeatherProvider').mockWeatherProvider as WeatherProvider;
    logger.info('weather', 'using mock provider');
  }
  return provider;
}
