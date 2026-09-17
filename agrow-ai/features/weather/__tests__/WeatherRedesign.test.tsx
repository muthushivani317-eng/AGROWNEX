const React = require("react");
const TestRenderer = require("react-test-renderer");
const fs = require("fs");
const path = require("path");

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, string>) =>
      params?.name ? `${key}:${params.name}` : key,
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
      ReactLocal.createElement(Text, null, label),
    AgCard: View,
    AgSkeleton: View,
    AgScreen: View,
    AgEmptyState: View,
    AgErrorState: View,
  };
});
jest.mock("lucide-react-native", () => {
  const { View } = require("react-native");
  return new Proxy({}, { get: () => View });
});

import { FarmSelector } from "../components/FarmSelector";
import { TodayMissionCard } from "../components/TodayMissionCard";
import { WeatherCard } from "../components/WeatherCard";
import { WeatherMetrics } from "../components/WeatherMetrics";
import { WeeklyForecast } from "../components/WeeklyForecast";
import type { CurrentWeather, DailyPoint } from "../types";
import { en } from "../../../localization/locales/en";
import { ta } from "../../../localization/locales/ta";

const current: CurrentWeather = {
  time: "2026-08-11T12:00:00Z",
  temperatureC: 23,
  apparentTemperatureC: 24,
  humidityPct: 61,
  precipitationMm: 0,
  rainMm: 0,
  weatherCode: 3,
  condition: "cloudy",
  isDay: true,
  cloudCoverPct: 80,
  windSpeedKmh: 12,
  windDirectionDeg: 90,
  windGustsKmh: 15,
  uvIndex: 2,
};

const daily: DailyPoint[] = [
  {
    date: "2026-08-11",
    weatherCode: 3,
    condition: "cloudy",
    tempMaxC: 29,
    tempMinC: 21,
    sunrise: null,
    sunset: null,
    uvIndexMax: 3,
    precipitationSumMm: 1,
    precipitationProbabilityMaxPct: 42,
    windSpeedMaxKmh: 14,
  },
  {
    date: "2026-08-12",
    weatherCode: 61,
    condition: "rain",
    tempMaxC: 27,
    tempMinC: 20,
    sunrise: null,
    sunset: null,
    uvIndexMax: 2,
    precipitationSumMm: 8,
    precipitationProbabilityMaxPct: 76,
    windSpeedMaxKmh: 18,
  },
];

test("current hero and forecast render supplied weather data dynamically", async () => {
  let hero: any;
  let forecast: any;
  await TestRenderer.act(async () => {
    hero = TestRenderer.create(
      React.createElement(WeatherCard, {
        current,
        location: {
          latitude: 10,
          longitude: 78,
          timezone: "Asia/Kolkata",
          name: "Dynamic farm",
        },
        fetchedAt: "2026-08-11T17:49:00",
      }),
    );
    forecast = TestRenderer.create(
      React.createElement(WeeklyForecast, { daily }),
    );
  });

  expect(hero.root.findAllByProps({ children: "23°C" })).not.toHaveLength(0);
  expect(
    hero.root.findAllByProps({ children: "weather.conditionCloudy" }),
  ).not.toHaveLength(0);
  expect(
    forecast.root.findByProps({ testID: "weather-forecast-row-2026-08-11" }),
  ).toBeTruthy();
  expect(
    forecast.root.findByProps({ testID: "weather-forecast-row-2026-08-12" }),
  ).toBeTruthy();
});

test("daily precipitation probability is labelled as a chance, not rainfall", async () => {
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(
      React.createElement(WeatherMetrics, { current, today: daily[0] }),
    );
  });

  const rainTile = tree.root.findByProps({ testID: "weather-metric-rain" });
  expect(
    rainTile.findAllByProps({ children: "weather.rainChanceToday" }),
  ).not.toHaveLength(0);
  expect(rainTile.findAllByProps({ children: "42%" })).not.toHaveLength(0);
  expect(en.weather.rainChanceToday).toBe("Rain chance today");
  expect(ta.weather.rainChanceToday).toBe("இன்று மழைக்கான வாய்ப்பு");
});

test("missing weather metrics are omitted instead of showing invented values", async () => {
  let tree: any;
  const sparse = { ...current, windSpeedKmh: null, uvIndex: null };
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(
      React.createElement(WeatherMetrics, { current: sparse, today: null }),
    );
  });
  expect(
    tree.root.findByProps({ testID: "weather-metric-humidity" }),
  ).toBeTruthy();
  expect(
    tree.root.findAllByProps({ testID: "weather-metric-wind" }),
  ).toHaveLength(0);
  expect(
    tree.root.findAllByProps({ testID: "weather-metric-rain" }),
  ).toHaveLength(0);
});

test("existing selected-farm callback remains tappable", async () => {
  const onSelect = jest.fn();
  const base = {
    crop: null,
    status: "active",
    areaHectares: null,
    district: null,
    hasBoundary: false,
    centroidLat: null,
    centroidLng: null,
    latitude: 10,
    longitude: 78,
    imageCount: 0,
    updatedAt: null,
    syncStatus: "synced",
  };
  const farms = [
    { ...base, id: "farm-a", name: "Farm A" },
    { ...base, id: "farm-b", name: "Farm B" },
  ];
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(
      React.createElement(FarmSelector, {
        farms,
        selectedId: "farm-a",
        onSelect,
      }),
    );
  });
  await TestRenderer.act(async () => {
    tree.root.findByProps({ testID: "weather-farm-selector" }).props.onPress();
  });
  const option = tree.root
    .findAllByProps({ accessibilityRole: "button" })
    .find((node: any) => node.props.accessibilityState?.selected === false);
  await TestRenderer.act(async () => {
    option.props.onPress();
  });
  expect(onSelect).toHaveBeenCalledWith("farm-b");
  const selector = tree.root.findByProps({ testID: "weather-farm-selector" });
  expect(typeof selector.props.style).not.toBe("function");
  expect(require("react-native").StyleSheet.flatten(selector.props.style).flexDirection).toBe("row");
});

test("today mission renders localized action and cached state", async () => {
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(
      React.createElement(TodayMissionCard, {
        mission: {
          primaryAction: "backend fallback",
          reason: "backend fallback",
          avoid: "backend fallback",
          secondaryActions: [],
          confidenceNote: "backend fallback",
          sourceInsightCode: "heavy_rain.expected",
          crop: "paddy",
        },
        insights: [
          {
            code: "heavy_rain.expected",
            category: "heavy_rain",
            severity: "warning",
            title: "",
            message: "",
            params: { mm: 48, prob: 80 },
          },
        ],
        cached: true,
        stale: false,
      }),
    );
  });

  expect(
    tree.root.findByProps({ testID: "weather-today-mission" }),
  ).toBeTruthy();
  expect(
    tree.root.findAllByProps({ children: "weather.cached" }),
  ).not.toHaveLength(0);
  expect(
    tree.root.findAllByProps({ children: "weather.missionActionRainExpected" }),
  ).not.toHaveLength(0);
  expect(
    tree.root.findAllByProps({ children: "weather.msgRainExpected" }),
  ).not.toHaveLength(0);
  expect(JSON.stringify(tree.toJSON())).toContain(
    "weather.forecastNext24Hours",
  );
  const action = tree.root.findByProps({ testID: "weather-mission-action" });
  expect(action.props.variant).toBe("headingS");
  expect(action.parent.props.testID).toBe("weather-today-mission");
  expect(
    tree.root.findAllByProps({ children: "weather.cachedReliabilityNote" }),
  ).not.toHaveLength(0);
  expect(
    tree.root.findAllByProps({ children: "weather.expertVerificationNote" }),
  ).not.toHaveLength(0);
});

test("stale cached mission is clearly cautious and never presented as current", async () => {
  let tree: any;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(
      React.createElement(TodayMissionCard, {
        mission: {
          primaryAction: "backend fallback",
          reason: "backend fallback",
          avoid: null,
          secondaryActions: [],
          confidenceNote: "backend fallback",
          sourceInsightCode: "wind.strong",
          crop: "paddy",
        },
        insights: [],
        cached: true,
        stale: true,
      }),
    );
  });

  expect(
    tree.root.findAllByProps({ children: "weather.stale" }),
  ).not.toHaveLength(0);
  expect(
    tree.root.findAllByProps({ children: "weather.staleReliabilityNote" }),
  ).not.toHaveLength(0);
  expect(
    tree.root.findAllByProps({ children: "weather.missionActionReview" }),
  ).not.toHaveLength(0);
  expect(
    tree.root.findAllByProps({ children: "weather.missionActionWindStrong" }),
  ).toHaveLength(0);
  expect(tree.root.findAllByProps({ children: "weather.missionAvoidWind" })).toHaveLength(0);
});

test("single route, refresh wiring, provider hook, and Tamil keys remain present", () => {
  const route = fs.readFileSync(
    path.join(process.cwd(), "app/weather.tsx"),
    "utf8",
  );
  const screen = fs.readFileSync(
    path.join(process.cwd(), "features/weather/screens/WeatherScreen.tsx"),
    "utf8",
  );
  expect(route).toContain("import { WeatherScreen } from '@/features/weather'");
  expect(screen).toContain("onRefresh={() => void refetch()}");
  expect(screen).toContain("useWeather(");
  expect(screen).toMatch(/<AgEmptyState\s+light/);
  expect(screen).toMatch(/<AgErrorState\s+light/);
  expect(screen).toContain("backgroundColor: WEATHER_UI.surface");
  expect(ta.weather.refresh).toBeTruthy();
  expect(ta.weather.selectedFarm).toBeTruthy();
  expect(ta.weather.todayMission).toBeTruthy();
  expect(ta.weather.cachedMissionNote).toBeTruthy();
  const requiredKeys = [
    "forecastTiming",
    "forecastNext24Hours",
    "dataSource",
    "live",
    "stale",
    "liveReliabilityNote",
    "cachedReliabilityNote",
    "staleReliabilityNote",
    "staleActionReason",
    "expertVerificationNote",
  ] as const;
  for (const key of requiredKeys) {
    expect(en.weather[key]).toBeTruthy();
    expect(ta.weather[key]).toBeTruthy();
  }
});
