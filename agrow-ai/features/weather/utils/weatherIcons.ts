import {
  Cloud,
  CloudDrizzle,
  CloudFog,
  CloudLightning,
  CloudRain,
  CloudSnow,
  CloudSun,
  Droplets,
  Moon,
  Sprout,
  Sun,
  ThermometerSun,
  Tractor,
  Wind,
  type LucideIcon,
} from 'lucide-react-native';

import type { InsightCategory, WeatherCondition } from '../types';

const CONDITION_ICON: Record<WeatherCondition, LucideIcon> = {
  clear: Sun,
  partly_cloudy: CloudSun,
  cloudy: Cloud,
  fog: CloudFog,
  drizzle: CloudDrizzle,
  rain: CloudRain,
  snow: CloudSnow,
  thunderstorm: CloudLightning,
};

/** Weather condition → icon (clear swaps to a moon at night). */
export function conditionIcon(condition: WeatherCondition, isDay = true): LucideIcon {
  if (condition === 'clear' && !isDay) return Moon;
  return CONDITION_ICON[condition];
}

export const CATEGORY_ICON: Record<InsightCategory, LucideIcon> = {
  irrigation: Droplets,
  spraying: Sprout,
  heat_stress: ThermometerSun,
  heavy_rain: CloudRain,
  wind: Wind,
  field_work: Tractor,
};
