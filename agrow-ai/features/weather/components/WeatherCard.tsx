import { Clock3 } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";

import { CONDITION_LABEL_KEY } from "../constants";
import type { CurrentWeather, WeatherLocation } from "../types";
import { formatHHmm, formatTempUnit } from "../utils/format";
import { conditionIcon } from "../utils/weatherIcons";
import { WeatherFreshnessNote } from "./WeatherFreshnessNote";
import { WEATHER_SHADOW, WEATHER_UI } from "../design";

/** Dynamic current-conditions hero; no advisory is inferred in this component. */
export function WeatherCard({
  current,
  location: _location,
  fetchedAt,
  cached,
  stale,
}: {
  current: CurrentWeather;
  location: WeatherLocation;
  fetchedAt: string;
  cached?: boolean;
  stale?: boolean;
}) {
  const { t } = useTranslation();
  const Icon = conditionIcon(current.condition, current.isDay);

  return (
    <View testID="weather-current-hero" style={styles.card}>
      <View style={styles.mainRow}>
        <View style={styles.iconWell}>
          <Icon size={68} color={WEATHER_UI.sun} strokeWidth={1.6} />
        </View>
        <View style={styles.conditions}>
          <AgText
            variant="headingXL"
            weight="bold"
            style={styles.primaryText}
            adjustsFontSizeToFit
            numberOfLines={1}
          >
            {formatTempUnit(current.temperatureC)}
          </AgText>
          <AgText
            variant="bodyLarge"
            weight="semibold"
            style={[styles.conditionText, styles.primaryText]}
          >
            {t(CONDITION_LABEL_KEY[current.condition])}
          </AgText>
          {current.apparentTemperatureC != null ? (
            <AgText variant="body" style={styles.feelsLike}>
              {t("weather.feelsLike")}{" "}
              {formatTempUnit(current.apparentTemperatureC)}
            </AgText>
          ) : null}
        </View>
      </View>
      <View style={styles.updatedRow}>
        <Clock3 size={16} color={WEATHER_UI.sky} />
        <AgText variant="bodySmall" style={styles.updatedText}>
          {t("weather.updated")} {formatHHmm(fetchedAt)}
        </AgText>
      </View>
      <WeatherFreshnessNote
        fetchedAt={fetchedAt}
        cached={cached}
        stale={stale}
        inverse
      />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    width: "100%",
    borderRadius: 26,
    padding: 20,
    overflow: "hidden",
    backgroundColor: WEATHER_UI.field,
    ...WEATHER_SHADOW,
  },
  mainRow: { flexDirection: "row", alignItems: "center", gap: 18 },
  iconWell: {
    width: 112,
    minHeight: 112,
    borderRadius: 56,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#FFFFFF14",
    borderWidth: 1,
    borderColor: "#FFFFFF2E",
  },
  conditions: { flex: 1, minWidth: 0 },
  conditionText: { marginTop: 2 },
  primaryText: { color: WEATHER_UI.white },
  feelsLike: { marginTop: 3, color: "#DCEBE1" },
  updatedText: { color: "#DCEBE1" },
  updatedRow: {
    marginTop: 18,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: "#FFFFFF2E",
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
});
