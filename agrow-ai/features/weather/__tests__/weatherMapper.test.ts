import type { ApiWeatherBundle } from "../types";
import { apiToBundle } from "../services/weatherMapper";

const dto: ApiWeatherBundle = {
  location: {
    latitude: 9.9,
    longitude: 78.1,
    timezone: "Asia/Kolkata",
    name: "North Field",
  },
  current: {
    time: "2026-07-10T09:00",
    temperature_c: 30,
    apparent_temperature_c: 32,
    humidity_pct: 70,
    precipitation_mm: 0,
    rain_mm: 0,
    weather_code: 1,
    condition: "partly_cloudy",
    is_day: true,
    cloud_cover_pct: 20,
    wind_speed_kmh: 8,
    wind_direction_deg: 180,
    wind_gusts_kmh: 15,
    uv_index: 6,
  },
  hourly: [
    {
      time: "2026-07-10T09:00",
      temperature_c: 28,
      humidity_pct: 70,
      precipitation_probability_pct: 10,
      precipitation_mm: 0,
      weather_code: 1,
      condition: "partly_cloudy",
      wind_speed_kmh: 8,
      uv_index: 5,
      is_day: true,
    },
  ],
  daily: [
    {
      date: "2026-07-10",
      weather_code: 1,
      condition: "partly_cloudy",
      temp_max_c: 34,
      temp_min_c: 24,
      sunrise: "2026-07-10T05:55",
      sunset: "2026-07-10T18:35",
      uv_index_max: 8,
      precipitation_sum_mm: 0,
      precipitation_probability_max_pct: 10,
      wind_speed_max_kmh: 12,
    },
  ],
  insights: [
    {
      code: "spraying.good_window",
      category: "spraying",
      severity: "advice",
      title: "Good to spray",
      message: "Calm and dry.",
      params: {},
    },
  ],
  mission: {
    primary_action: "Complete planned field work",
    reason: "Conditions are favourable.",
    avoid: null,
    secondary_actions: [],
    confidence_note: "Higher confidence for today.",
    source_insight_code: "field_work.favorable",
    crop: "paddy",
  },
  fetched_at: "2026-07-10T09:00:00Z",
  source: "open-meteo",
  data_state: "cached",
};

describe("weatherMapper", () => {
  it("maps the bundle envelope to the domain model", () => {
    const bundle = apiToBundle(dto);
    expect(bundle.location.name).toBe("North Field");
    expect(bundle.current.temperatureC).toBe(30);
    expect(bundle.current.apparentTemperatureC).toBe(32);
    expect(bundle.current.condition).toBe("partly_cloudy");
    expect(bundle.hourly[0].precipitationProbabilityPct).toBe(10);
    expect(bundle.daily[0].tempMaxC).toBe(34);
    expect(bundle.daily[0].sunrise).toBe("2026-07-10T05:55");
    expect(bundle.insights[0].code).toBe("spraying.good_window");
    expect(bundle.mission.sourceInsightCode).toBe("field_work.favorable");
    // A normal backend cache hit is fresh online data; only useWeather's
    // persisted offline fallback should activate the cached-data warning.
    expect(bundle.isCached).toBe(false);
    expect(bundle.mission.crop).toBe("paddy");
    expect(bundle.source).toBe("open-meteo");
  });
});
