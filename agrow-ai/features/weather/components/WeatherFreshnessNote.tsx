import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgBadge, AgText } from "@/components/ui";

import { WEATHER_UI } from "../design";
import { relativeTimeKey } from "../utils/time";

interface Props {
  fetchedAt?: string | null;
  cached?: boolean;
  stale?: boolean;
  inverse?: boolean;
}

/**
 * Small "this isn't live data" note for the secondary weather cards
 * (metrics, hourly, alerts, weekly). Silent when the data is live — only
 * appears when the screen fell back to an offline cache, so a farmer can
 * tell they might be looking at yesterday's forecast instead of today's
 * (2026-08 pre-release audit: a dropped connection previously left cached
 * weather on screen with no visual difference from a live fetch).
 *
 * Reuses the exact badge convention already shipped in TodayMissionCard
 * (weather.stale / weather.cached, warning / neutral tone) plus the
 * relative-time convention from features/home and features/notifications —
 * no new translation strings needed.
 */
export function WeatherFreshnessNote({
  fetchedAt,
  cached,
  stale,
  inverse = false,
}: Props) {
  const { t } = useTranslation();
  if (!cached && !stale) return null;
  const { key, params } = relativeTimeKey(fetchedAt ?? null);

  return (
    <View style={styles.row} testID="weather-freshness-note">
      <AgBadge
        label={t(stale ? "weather.stale" : "weather.cached")}
        tone={stale ? "warning" : "neutral"}
        textStyle={inverse ? undefined : styles.lightSurfaceText}
      />
      <AgText
        variant="caption"
        color="inherit"
        style={inverse ? styles.inverseText : styles.lightSurfaceText}
      >
        {t(key, params)}
      </AgText>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { marginTop: 8, flexDirection: "row", alignItems: "center", gap: 8 },
  inverseText: { color: "#E7F2EA" },
  lightSurfaceText: { color: WEATHER_UI.text },
});
