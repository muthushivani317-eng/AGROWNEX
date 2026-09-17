import type {
  ApiCurrentWeather,
  ApiDailyPoint,
  ApiHourlyPoint,
  ApiWeatherBundle,
  ApiWeatherInsight,
  CurrentWeather,
  DailyPoint,
  HourlyPoint,
  WeatherBundle,
  WeatherInsight,
} from "../types";

/** Pure API-envelope → domain conversions (snake_case → camelCase). */

function mapCurrent(c: ApiCurrentWeather): CurrentWeather {
  return {
    time: c.time,
    temperatureC: c.temperature_c,
    apparentTemperatureC: c.apparent_temperature_c,
    humidityPct: c.humidity_pct,
    precipitationMm: c.precipitation_mm,
    rainMm: c.rain_mm,
    weatherCode: c.weather_code,
    condition: c.condition,
    isDay: c.is_day,
    cloudCoverPct: c.cloud_cover_pct,
    windSpeedKmh: c.wind_speed_kmh,
    windDirectionDeg: c.wind_direction_deg,
    windGustsKmh: c.wind_gusts_kmh,
    uvIndex: c.uv_index,
  };
}

function mapHourly(h: ApiHourlyPoint): HourlyPoint {
  return {
    time: h.time,
    temperatureC: h.temperature_c,
    humidityPct: h.humidity_pct,
    precipitationProbabilityPct: h.precipitation_probability_pct,
    precipitationMm: h.precipitation_mm,
    weatherCode: h.weather_code,
    condition: h.condition,
    windSpeedKmh: h.wind_speed_kmh,
    uvIndex: h.uv_index,
    isDay: h.is_day,
  };
}

function mapDaily(d: ApiDailyPoint): DailyPoint {
  return {
    date: d.date,
    weatherCode: d.weather_code,
    condition: d.condition,
    tempMaxC: d.temp_max_c,
    tempMinC: d.temp_min_c,
    sunrise: d.sunrise,
    sunset: d.sunset,
    uvIndexMax: d.uv_index_max,
    precipitationSumMm: d.precipitation_sum_mm,
    precipitationProbabilityMaxPct: d.precipitation_probability_max_pct,
    windSpeedMaxKmh: d.wind_speed_max_kmh,
  };
}

function mapInsight(i: ApiWeatherInsight): WeatherInsight {
  return {
    code: i.code,
    category: i.category,
    severity: i.severity,
    title: i.title,
    message: i.message,
    params: i.params ?? {},
  };
}

export function apiToBundle(dto: ApiWeatherBundle): WeatherBundle {
  return {
    location: {
      latitude: dto.location.latitude,
      longitude: dto.location.longitude,
      timezone: dto.location.timezone,
      name: dto.location.name,
    },
    current: mapCurrent(dto.current),
    hourly: dto.hourly.map(mapHourly),
    daily: dto.daily.map(mapDaily),
    insights: dto.insights.map(mapInsight),
    mission: {
      primaryAction: dto.mission.primary_action,
      reason: dto.mission.reason,
      avoid: dto.mission.avoid,
      secondaryActions: dto.mission.secondary_actions,
      confidenceNote: dto.mission.confidence_note,
      sourceInsightCode: dto.mission.source_insight_code,
      crop: dto.mission.crop,
    },
    fetchedAt: dto.fetched_at,
    source: dto.source,
    // `data_state=cached` means the backend reused its normal five-minute
    // Open-Meteo cache. It is still a successful online response with an
    // honest fetchedAt timestamp, not the mobile app's offline fallback.
    // useWeather marks only that offline fallback as isCached.
    isCached: false,
  };
}
