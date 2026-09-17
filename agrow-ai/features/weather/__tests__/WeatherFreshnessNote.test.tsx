// Staleness-indicator coverage (2026-08-18 pre-release audit): the weather
// screens showed cached data with no indication of how old it was -- a
// dropped connection could silently leave yesterday's forecast on screen
// looking identical to a live one. This covers the shared note plus its
// wiring into the four secondary cards that previously had no cached/stale
// awareness at all (WeatherCard + TodayMissionCard already had it).
const React = require("react");
const TestRenderer = require("react-test-renderer");

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) =>
      params ? `${key}:${JSON.stringify(params)}` : key,
  }),
}));
jest.mock("@/hooks/useAppTheme", () => ({
  useAppTheme: () => ({
    colors: {
      primary: "#4CAF50",
      card: "#252525",
      surface: "#1E1E1E",
      border: "#333333",
      text: "#FFFFFF",
      textMuted: "#BDBDBD",
      info: "#42A5F5",
    },
  }),
}));
jest.mock("@/components/ui", () => {
  const ReactLocal = require("react");
  const { Text, View } = require("react-native");
  return {
    AgText: Text,
    AgBadge: ({ label }: { label: string }) =>
      ReactLocal.createElement(Text, { testID: "ag-badge" }, label),
    AgCard: View,
  };
});
jest.mock("lucide-react-native", () => {
  const { View } = require("react-native");
  return new Proxy({}, { get: () => View });
});

import { HourlyForecast } from "../components/HourlyForecast";
import { WeatherAlerts } from "../components/WeatherAlerts";
import { WeatherFreshnessNote } from "../components/WeatherFreshnessNote";
import { WeatherMetrics } from "../components/WeatherMetrics";
import { WeeklyForecast } from "../components/WeeklyForecast";
import type { CurrentWeather, DailyPoint, HourlyPoint, WeatherInsight } from "../types";

const NOW = "2026-08-18T12:00:00.000Z";
const TWO_HOURS_AGO = "2026-08-18T10:00:00.000Z";

async function render(element: any) {
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(element);
  });
  return tree;
}

describe("WeatherFreshnessNote", () => {
  it("renders nothing for live data", async () => {
    const tree = await render(
      React.createElement(WeatherFreshnessNote, { fetchedAt: NOW }),
    );
    expect(tree.toJSON()).toBeNull();
  });

  it("shows a neutral cached badge with a relative time when cached but not stale", async () => {
    const tree = await render(
      React.createElement(WeatherFreshnessNote, {
        fetchedAt: TWO_HOURS_AGO,
        cached: true,
        stale: false,
      }),
    );
    expect(
      tree.root.findAllByProps({ children: "weather.cached" }),
    ).not.toHaveLength(0);
    expect(tree.root.findByProps({ testID: "weather-freshness-note" })).toBeTruthy();
  });

  it("shows a warning stale badge when the cached data is old", async () => {
    const tree = await render(
      React.createElement(WeatherFreshnessNote, {
        fetchedAt: TWO_HOURS_AGO,
        cached: true,
        stale: true,
      }),
    );
    expect(
      tree.root.findAllByProps({ children: "weather.stale" }),
    ).not.toHaveLength(0);
  });
});

describe("secondary weather cards surface the same freshness note when stale", () => {
  const current: CurrentWeather = {
    time: NOW,
    temperatureC: 30,
    apparentTemperatureC: 32,
    humidityPct: 55,
    precipitationMm: 0,
    rainMm: 0,
    weatherCode: 1,
    condition: "clear",
    isDay: true,
    cloudCoverPct: 10,
    windSpeedKmh: 8,
    windDirectionDeg: 90,
    windGustsKmh: 10,
    uvIndex: 5,
  };
  const daily: DailyPoint[] = [
    {
      date: "2026-08-18",
      weatherCode: 1,
      condition: "clear",
      tempMaxC: 34,
      tempMinC: 24,
      sunrise: null,
      sunset: null,
      uvIndexMax: 6,
      precipitationSumMm: 0,
      precipitationProbabilityMaxPct: 10,
      windSpeedMaxKmh: 12,
    },
  ];
  const hourly: HourlyPoint[] = [
    {
      time: NOW,
      temperatureC: 30,
      humidityPct: 55,
      precipitationProbabilityPct: 10,
      precipitationMm: 0,
      weatherCode: 1,
      condition: "clear",
      windSpeedKmh: 8,
      uvIndex: 5,
      isDay: true,
    },
  ];
  const insights: WeatherInsight[] = [
    {
      code: "irrigation.normal",
      category: "irrigation",
      severity: "info",
      title: "",
      message: "fallback message",
      params: {},
    },
  ];

  it("WeatherMetrics shows the stale note", async () => {
    const tree = await render(
      React.createElement(WeatherMetrics, {
        current,
        today: daily[0],
        fetchedAt: TWO_HOURS_AGO,
        cached: true,
        stale: true,
      }),
    );
    expect(tree.root.findByProps({ testID: "weather-freshness-note" })).toBeTruthy();
  });

  it("HourlyForecast shows the stale note", async () => {
    const tree = await render(
      React.createElement(HourlyForecast, {
        hourly,
        fetchedAt: TWO_HOURS_AGO,
        cached: true,
        stale: true,
      }),
    );
    expect(tree.root.findByProps({ testID: "weather-freshness-note" })).toBeTruthy();
  });

  it("WeatherAlerts shows the stale note", async () => {
    const tree = await render(
      React.createElement(WeatherAlerts, {
        insights,
        fetchedAt: TWO_HOURS_AGO,
        cached: true,
        stale: true,
      }),
    );
    expect(tree.root.findByProps({ testID: "weather-freshness-note" })).toBeTruthy();
  });

  it("WeeklyForecast shows the stale note", async () => {
    const tree = await render(
      React.createElement(WeeklyForecast, {
        daily,
        fetchedAt: TWO_HOURS_AGO,
        cached: true,
        stale: true,
      }),
    );
    expect(tree.root.findByProps({ testID: "weather-freshness-note" })).toBeTruthy();
  });

  it("none of the secondary cards show the note for live data", async () => {
    const metrics = await render(
      React.createElement(WeatherMetrics, { current, today: daily[0] }),
    );
    const hourlyTree = await render(React.createElement(HourlyForecast, { hourly }));
    const alerts = await render(React.createElement(WeatherAlerts, { insights }));
    const weekly = await render(React.createElement(WeeklyForecast, { daily }));

    for (const tree of [metrics, hourlyTree, alerts, weekly]) {
      expect(
        tree.root.findAllByProps({ testID: "weather-freshness-note" }),
      ).toHaveLength(0);
    }
  });
});
