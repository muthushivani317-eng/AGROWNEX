/**
 * Weather Intelligence domain types (docs/API_CONTRACT.md → WEATHER MODULE).
 * Client-side camelCase mirror of the backend weather schemas.
 */

export type WeatherCondition =
  | "clear"
  | "partly_cloudy"
  | "cloudy"
  | "fog"
  | "drizzle"
  | "rain"
  | "snow"
  | "thunderstorm";

export type InsightCategory =
  | "irrigation"
  | "spraying"
  | "heat_stress"
  | "heavy_rain"
  | "wind"
  | "field_work";

export type InsightSeverity = "info" | "advice" | "warning" | "critical";

export interface WeatherLocation {
  latitude: number;
  longitude: number;
  timezone: string | null;
  name: string | null;
}

export interface CurrentWeather {
  time: string;
  temperatureC: number | null;
  apparentTemperatureC: number | null;
  humidityPct: number | null;
  precipitationMm: number | null;
  rainMm: number | null;
  weatherCode: number | null;
  condition: WeatherCondition;
  isDay: boolean;
  cloudCoverPct: number | null;
  windSpeedKmh: number | null;
  windDirectionDeg: number | null;
  windGustsKmh: number | null;
  uvIndex: number | null;
}

export interface HourlyPoint {
  time: string;
  temperatureC: number | null;
  humidityPct: number | null;
  precipitationProbabilityPct: number | null;
  precipitationMm: number | null;
  weatherCode: number | null;
  condition: WeatherCondition;
  windSpeedKmh: number | null;
  uvIndex: number | null;
  isDay: boolean;
}

export interface DailyPoint {
  date: string;
  weatherCode: number | null;
  condition: WeatherCondition;
  tempMaxC: number | null;
  tempMinC: number | null;
  sunrise: string | null;
  sunset: string | null;
  uvIndexMax: number | null;
  precipitationSumMm: number | null;
  precipitationProbabilityMaxPct: number | null;
  windSpeedMaxKmh: number | null;
}

export interface WeatherInsight {
  code: string;
  category: InsightCategory;
  severity: InsightSeverity;
  title: string;
  message: string;
  params: Record<string, number | string>;
}

export interface WeatherMission {
  primaryAction: string;
  reason: string;
  avoid: string | null;
  secondaryActions: string[];
  confidenceNote: string;
  sourceInsightCode: string | null;
  crop: string | null;
}

export interface WeatherBundle {
  location: WeatherLocation;
  current: CurrentWeather;
  hourly: HourlyPoint[];
  daily: DailyPoint[];
  insights: WeatherInsight[];
  mission: WeatherMission;
  fetchedAt: string;
  source: string;
  isCached?: boolean;
}

/** Where to read weather for (farm coords are resolved by the backend). */
export interface WeatherQuery {
  farmId?: string;
  latitude?: number | null;
  longitude?: number | null;
  name?: string | null;
}

// --------------------------------------------------------------------------- //
// Backend envelope shapes (snake_case) — used by the API provider/mapper.
// --------------------------------------------------------------------------- //
export interface ApiWeatherLocation {
  latitude: number;
  longitude: number;
  timezone: string | null;
  name: string | null;
}

export interface ApiCurrentWeather {
  time: string;
  temperature_c: number | null;
  apparent_temperature_c: number | null;
  humidity_pct: number | null;
  precipitation_mm: number | null;
  rain_mm: number | null;
  weather_code: number | null;
  condition: WeatherCondition;
  is_day: boolean;
  cloud_cover_pct: number | null;
  wind_speed_kmh: number | null;
  wind_direction_deg: number | null;
  wind_gusts_kmh: number | null;
  uv_index: number | null;
}

export interface ApiHourlyPoint {
  time: string;
  temperature_c: number | null;
  humidity_pct: number | null;
  precipitation_probability_pct: number | null;
  precipitation_mm: number | null;
  weather_code: number | null;
  condition: WeatherCondition;
  wind_speed_kmh: number | null;
  uv_index: number | null;
  is_day: boolean;
}

export interface ApiDailyPoint {
  date: string;
  weather_code: number | null;
  condition: WeatherCondition;
  temp_max_c: number | null;
  temp_min_c: number | null;
  sunrise: string | null;
  sunset: string | null;
  uv_index_max: number | null;
  precipitation_sum_mm: number | null;
  precipitation_probability_max_pct: number | null;
  wind_speed_max_kmh: number | null;
}

export interface ApiWeatherInsight {
  code: string;
  category: InsightCategory;
  severity: InsightSeverity;
  title: string;
  message: string;
  params: Record<string, number | string>;
}

export interface ApiWeatherMission {
  primary_action: string;
  reason: string;
  avoid: string | null;
  secondary_actions: string[];
  confidence_note: string;
  source_insight_code: string | null;
  crop: string | null;
}

export interface ApiWeatherBundle {
  location: ApiWeatherLocation;
  current: ApiCurrentWeather;
  hourly: ApiHourlyPoint[];
  daily: ApiDailyPoint[];
  insights: ApiWeatherInsight[];
  mission: ApiWeatherMission;
  fetched_at: string;
  source: string;
  data_state?: "live" | "cached";
}
