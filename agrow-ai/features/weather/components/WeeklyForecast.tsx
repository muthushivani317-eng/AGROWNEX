import { Droplet } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, useWindowDimensions, View } from "react-native";

import { AgText } from "@/components/ui";

import type { DailyPoint } from "../types";
import { formatTemp, weekdayKey } from "../utils/format";
import { conditionIcon } from "../utils/weatherIcons";
import { WeatherFreshnessNote } from "./WeatherFreshnessNote";
import { WEATHER_SHADOW, WEATHER_UI } from "../design";

function numericTemperatures(daily: DailyPoint[]): number[] {
  return daily
    .flatMap((day) => [day.tempMinC, day.tempMaxC])
    .filter((value): value is number => value != null);
}

/** Compact dynamic 7-day forecast, one horizontal row per API day. */
export function WeeklyForecast({
  daily,
  fetchedAt,
  cached,
  stale,
}: {
  daily: DailyPoint[];
  fetchedAt?: string;
  cached?: boolean;
  stale?: boolean;
}) {
  const { t } = useTranslation();
  const { width, fontScale } = useWindowDimensions();
  const compact = width < 370 || fontScale > 1.2;
  if (!daily.length) return null;

  const temperatures = numericTemperatures(daily);
  const overallMin = temperatures.length ? Math.min(...temperatures) : 0;
  const overallMax = temperatures.length ? Math.max(...temperatures) : 1;
  const spread = Math.max(overallMax - overallMin, 1);

  return (
    <View style={styles.section}>
      <AgText variant="headingS" weight="semibold" style={styles.heading}>
        {t("weather.next7d")}
      </AgText>
      <WeatherFreshnessNote
        fetchedAt={fetchedAt}
        cached={cached}
        stale={stale}
      />
      <View testID="weather-weekly-forecast" style={styles.card}>
        {daily.map((day, index) => {
          const Icon = conditionIcon(day.condition, true);
          const left =
            day.tempMinC == null
              ? 0
              : ((day.tempMinC - overallMin) / spread) * 42;
          const width =
            day.tempMinC == null || day.tempMaxC == null
              ? 0
              : Math.max(((day.tempMaxC - day.tempMinC) / spread) * 58, 16);
          return (
            <View
              key={day.date}
              testID={`weather-forecast-row-${day.date}`}
              style={[
                styles.row,
                compact && styles.rowCompact,
                index > 0 && styles.rowDivider,
              ]}
            >
              <AgText
                variant="body"
                color="inherit"
                weight="medium"
                style={styles.day}
                numberOfLines={1}
              >
                {index === 0 ? t("weather.today") : t(weekdayKey(day.date))}
              </AgText>
              <Icon size={25} color={WEATHER_UI.field} />
              <View style={styles.rain}>
                {day.precipitationProbabilityMaxPct != null ? (
                  <>
                    <Droplet size={13} color={WEATHER_UI.rain} />
                    <AgText variant="caption" color="inherit" style={styles.secondaryText}>
                      {Math.round(day.precipitationProbabilityMaxPct)}%
                    </AgText>
                  </>
                ) : null}
              </View>
              <AgText
                variant="bodySmall"
                color="inherit"
                style={styles.temperature}
              >
                {formatTemp(day.tempMinC)}
              </AgText>
              {!compact ? (
                <View style={styles.rangeTrack}>
                  <View
                    style={[
                      styles.rangeFill,
                      { left: `${left}%`, width: `${width}%` },
                    ]}
                  />
                </View>
              ) : null}
              <AgText
                variant="bodySmall"
                color="inherit"
                weight="semibold"
                style={styles.temperature}
              >
                {formatTemp(day.tempMaxC)}
              </AgText>
            </View>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  section: { gap: 10 },
  heading: { color: WEATHER_UI.text },
  card: {
    borderWidth: 1,
    borderColor: WEATHER_UI.border,
    borderRadius: 24,
    paddingHorizontal: 16,
    overflow: "hidden",
    backgroundColor: WEATHER_UI.surface,
    ...WEATHER_SHADOW,
  },
  row: { minHeight: 70, flexDirection: "row", alignItems: "center", gap: 8 },
  rowCompact: { gap: 5 },
  rowDivider: { borderTopColor: WEATHER_UI.border, borderTopWidth: 1 },
  day: { width: 62, color: WEATHER_UI.text },
  rain: {
    width: 46,
    minHeight: 20,
    flexDirection: "row",
    alignItems: "center",
    gap: 2,
  },
  temperature: { width: 30, textAlign: "center", color: WEATHER_UI.text },
  secondaryText: { color: WEATHER_UI.text },
  rangeTrack: {
    flex: 1,
    minWidth: 30,
    height: 7,
    borderRadius: 4,
    overflow: "hidden",
    backgroundColor: WEATHER_UI.border,
  },
  rangeFill: {
    position: "absolute",
    height: 7,
    borderRadius: 4,
    backgroundColor: WEATHER_UI.sun,
  },
});
