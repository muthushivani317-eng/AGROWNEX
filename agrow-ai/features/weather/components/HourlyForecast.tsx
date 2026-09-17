import { Droplet } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { FlatList, StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";

import type { HourlyPoint } from "../types";
import { formatHHmm, formatTemp } from "../utils/format";
import { conditionIcon } from "../utils/weatherIcons";
import { WeatherFreshnessNote } from "./WeatherFreshnessNote";
import { WEATHER_UI } from "../design";

/** Horizontally-scrolling 24-hour forecast. */
export function HourlyForecast({
  hourly,
  fetchedAt,
  cached,
  stale,
}: {
  hourly: HourlyPoint[];
  fetchedAt?: string;
  cached?: boolean;
  stale?: boolean;
}) {
  const { t } = useTranslation();

  return (
    <View style={styles.section}>
      <AgText variant="headingS" weight="semibold" style={styles.heading}>
        {t("weather.next24h")}
      </AgText>
      <WeatherFreshnessNote
        fetchedAt={fetchedAt}
        cached={cached}
        stale={stale}
      />
      <FlatList
        horizontal
        showsHorizontalScrollIndicator={false}
        data={hourly}
        keyExtractor={(item) => item.time}
        contentContainerStyle={styles.list}
        renderItem={({ item }) => {
          const Icon = conditionIcon(item.condition, item.isDay);
          return (
            <View
              style={[
                styles.hourCard,
                item.isDay ? styles.dayCard : styles.nightCard,
              ]}
            >
              <AgText variant="caption" color="inherit" style={styles.time}>
                {formatHHmm(item.time)}
              </AgText>
              <Icon
                size={25}
                color={item.isDay ? WEATHER_UI.sun : WEATHER_UI.rain}
                style={styles.weatherIcon}
              />
              <AgText
                variant="bodySmall"
                color="inherit"
                weight="semibold"
                style={styles.temperature}
              >
                {formatTemp(item.temperatureC)}
              </AgText>
              <View style={styles.rainRow}>
                <Droplet size={12} color={WEATHER_UI.rain} />
                <AgText variant="caption" color="inherit" style={styles.time}>
                  {item.precipitationProbabilityPct ?? 0}%
                </AgText>
              </View>
            </View>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  section: { gap: 10 },
  heading: { color: WEATHER_UI.text },
  list: { gap: 10, paddingRight: 4 },
  hourCard: {
    width: 76,
    minHeight: 132,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: WEATHER_UI.border,
    paddingVertical: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  dayCard: { backgroundColor: WEATHER_UI.surface },
  nightCard: { backgroundColor: "#E9EEF0" },
  time: { color: WEATHER_UI.muted },
  weatherIcon: { marginVertical: 8 },
  temperature: { color: WEATHER_UI.text },
  rainRow: { marginTop: 5, flexDirection: "row", alignItems: "center", gap: 3 },
});
