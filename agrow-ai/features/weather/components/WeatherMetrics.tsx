import {
  CloudRain,
  Droplets,
  type LucideIcon,
  Sun,
  Sunrise,
  Sunset,
  Wind,
} from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";

import type { CurrentWeather, DailyPoint } from "../types";
import { formatHHmm, formatInt, uvLabelKey } from "../utils/format";
import { WeatherFreshnessNote } from "./WeatherFreshnessNote";
import { WEATHER_SHADOW, WEATHER_UI } from "../design";

interface Metric {
  key: string;
  icon: LucideIcon;
  label: string;
  value: string;
  hint?: string;
}

function MetricTile({ metric }: { metric: Metric }) {
  const Icon = metric.icon;
  return (
    <View testID={`weather-metric-${metric.key}`} style={styles.tile}>
      <View style={styles.iconWell}>
        <Icon size={23} color={WEATHER_UI.rain} />
      </View>
      <AgText variant="headingS" color="inherit" weight="bold" style={styles.value}>
        {metric.value}
      </AgText>
      <AgText variant="bodySmall" color="inherit" style={styles.metricLabel}>
        {metric.label}
      </AgText>
      {metric.hint ? (
        <AgText variant="caption" color="inherit" style={styles.hint}>
          {metric.hint}
        </AgText>
      ) : null}
    </View>
  );
}

/** Compact two-column metric grid. Metrics without real data are omitted. */
export function WeatherMetrics({
  current,
  today,
  fetchedAt,
  cached,
  stale,
}: {
  current: CurrentWeather;
  today: DailyPoint | null;
  fetchedAt?: string;
  cached?: boolean;
  stale?: boolean;
}) {
  const { t } = useTranslation();
  const metrics: Metric[] = [];

  if (current.humidityPct != null)
    metrics.push({
      key: "humidity",
      icon: Droplets,
      label: t("weather.humidity"),
      value: `${formatInt(current.humidityPct)}%`,
    });
  if (current.windSpeedKmh != null)
    metrics.push({
      key: "wind",
      icon: Wind,
      label: t("weather.wind"),
      value: formatInt(current.windSpeedKmh),
      hint: t("weather.kmh"),
    });
  if (current.uvIndex != null)
    metrics.push({
      key: "uv",
      icon: Sun,
      label: t("weather.uvIndex"),
      value: formatInt(current.uvIndex),
      hint: t(uvLabelKey(current.uvIndex)),
    });
  if (today?.precipitationProbabilityMaxPct != null)
    metrics.push({
      key: "rain",
      icon: CloudRain,
      // Open-Meteo's daily field is the maximum forecast probability for any
      // hour today. It is not observed rainfall or the percentage of the day
      // that will be wet, so label it explicitly as a chance.
      label: t("weather.rainChanceToday"),
      value: `${formatInt(today.precipitationProbabilityMaxPct)}%`,
    });
  if (today?.sunrise)
    metrics.push({
      key: "sunrise",
      icon: Sunrise,
      label: t("weather.sunrise"),
      value: formatHHmm(today.sunrise),
    });
  if (today?.sunset)
    metrics.push({
      key: "sunset",
      icon: Sunset,
      label: t("weather.sunset"),
      value: formatHHmm(today.sunset),
    });

  if (!metrics.length) return null;

  return (
    <>
      <WeatherFreshnessNote
        fetchedAt={fetchedAt}
        cached={cached}
        stale={stale}
      />
      <View testID="weather-metrics" style={styles.grid}>
        {metrics.map((metric) => (
          <MetricTile key={metric.key} metric={metric} />
        ))}
        {metrics.length % 2 === 1 ? <View style={styles.emptyCell} /> : null}
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  tile: {
    flexBasis: "47%",
    flexGrow: 1,
    minWidth: 0,
    minHeight: 128,
    borderWidth: 1,
    borderColor: WEATHER_UI.border,
    borderRadius: 20,
    padding: 14,
    alignItems: "flex-start",
    justifyContent: "center",
    backgroundColor: WEATHER_UI.surface,
    ...WEATHER_SHADOW,
  },
  emptyCell: { flexBasis: "47%", flexGrow: 1 },
  iconWell: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: WEATHER_UI.sky,
  },
  value: { marginTop: 8, color: WEATHER_UI.text },
  metricLabel: { color: WEATHER_UI.muted, marginTop: 2 },
  hint: { color: WEATHER_UI.field, marginTop: 2 },
});
