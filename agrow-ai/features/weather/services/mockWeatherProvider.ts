import dayjs from "dayjs";

import type {
  CurrentWeather,
  DailyPoint,
  HourlyPoint,
  WeatherBundle,
  WeatherInsight,
  WeatherQuery,
} from "../types";
import type { WeatherProvider } from "./weatherProvider";

/**
 * Deterministic, offline sample used until a backend is configured. Produces a
 * plausible mild day so the Weather screen is fully functional in development.
 * The rule-based insights are computed on the backend; here we return a small
 * representative set.
 */
const DEFAULT = { latitude: 10.79, longitude: 78.7 };

function buildHourly(): HourlyPoint[] {
  const start = dayjs().startOf("hour");
  const points: HourlyPoint[] = [];
  for (let i = 0; i < 24; i++) {
    const at = start.add(i, "hour");
    const hour = at.hour();
    const isDay = hour >= 6 && hour <= 18;
    const temp =
      Math.round((26 + 4 * Math.sin(((hour - 15) / 24) * Math.PI * 2)) * 10) /
      10;
    const rainy = hour >= 14 && hour <= 17;
    points.push({
      time: at.toISOString(),
      temperatureC: temp,
      humidityPct: 65,
      precipitationProbabilityPct: rainy ? 40 : 10,
      precipitationMm: 0,
      weatherCode: 2,
      condition: "partly_cloudy",
      windSpeedKmh: 10,
      uvIndex: isDay ? 6 : 0,
      isDay,
    });
  }
  return points;
}

function buildDaily(): DailyPoint[] {
  const points: DailyPoint[] = [];
  for (let i = 0; i < 7; i++) {
    const day = dayjs().add(i, "day");
    points.push({
      date: day.format("YYYY-MM-DD"),
      weatherCode: 2,
      condition: "partly_cloudy",
      tempMaxC: 33,
      tempMinC: 24,
      sunrise: day.hour(6).minute(0).second(0).toISOString(),
      sunset: day.hour(18).minute(30).second(0).toISOString(),
      uvIndexMax: 8,
      precipitationSumMm: i === 3 ? 6 : 0,
      precipitationProbabilityMaxPct: i === 3 ? 55 : 20,
      windSpeedMaxKmh: 14,
    });
  }
  return points;
}

const INSIGHTS: WeatherInsight[] = [
  {
    code: "irrigation.normal",
    category: "irrigation",
    severity: "info",
    title: "Irrigation normal",
    message: "Irrigate as per your crop schedule.",
    params: {},
  },
  {
    code: "spraying.good_window",
    category: "spraying",
    severity: "advice",
    title: "Good to spray",
    message: "Calm and dry — a good window for spraying.",
    params: {},
  },
  {
    code: "field_work.favorable",
    category: "field_work",
    severity: "info",
    title: "Good for field work",
    message: "Conditions are favourable for field work today.",
    params: {},
  },
];

export const mockWeatherProvider: WeatherProvider = {
  async getWeather(query: WeatherQuery): Promise<WeatherBundle> {
    const now = dayjs();
    const hour = now.hour();
    const isDay = hour >= 6 && hour <= 18;
    const current: CurrentWeather = {
      time: now.toISOString(),
      temperatureC: 30,
      apparentTemperatureC: 32,
      humidityPct: 65,
      precipitationMm: 0,
      rainMm: 0,
      weatherCode: 2,
      condition: "partly_cloudy",
      isDay,
      cloudCoverPct: 30,
      windSpeedKmh: 10,
      windDirectionDeg: 200,
      windGustsKmh: 18,
      uvIndex: isDay ? 6 : 0,
    };
    return {
      location: {
        latitude: query.latitude ?? DEFAULT.latitude,
        longitude: query.longitude ?? DEFAULT.longitude,
        timezone: "Asia/Kolkata",
        name: query.name ?? null,
      },
      current,
      hourly: buildHourly(),
      daily: buildDaily(),
      insights: INSIGHTS,
      mission: {
        primaryAction: "Complete planned field work today",
        reason: "Conditions are favourable for field work today.",
        avoid: null,
        secondaryActions: INSIGHTS.slice(0, 2).map((item) => item.message),
        confidenceNote: "Today's guidance has higher confidence.",
        sourceInsightCode: "field_work.favorable",
        crop: null,
      },
      fetchedAt: now.toISOString(),
      source: "mock",
    };
  },
};
