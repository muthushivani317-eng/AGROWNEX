import {
  AlertTriangle,
  Clock3,
  Database,
  ShieldCheck,
  Target,
  WifiOff,
} from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgBadge, AgCard, AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import {
  INSIGHT_MESSAGE_KEY,
  MISSION_ACTION_KEY,
  MISSION_AVOID_KEY,
} from "../constants";
import type { WeatherInsight, WeatherMission } from "../types";
import { WEATHER_SHADOW, WEATHER_UI } from "../design";

interface Props {
  mission: WeatherMission;
  insights: WeatherInsight[];
  cached?: boolean;
  stale?: boolean;
}

function timingKey(code: string): string {
  if (code.startsWith("heavy_rain.") || code === "irrigation.hold") {
    return "weather.forecastNext24Hours";
  }
  if (code.startsWith("spraying.")) return "weather.forecastNextFewHours";
  return "weather.forecastToday";
}

export function TodayMissionCard({
  mission,
  insights,
  cached = false,
  stale = false,
}: Props) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const code = mission.sourceInsightCode ?? "";
  const source = insights.find((insight) => insight.code === code);
  const crop = mission.crop || t("weather.yourCrop");
  const actionKey = stale
    ? "weather.missionActionReview"
    : (MISSION_ACTION_KEY[code] ?? "weather.missionActionReview");
  const reasonKey = INSIGHT_MESSAGE_KEY[code];
  const avoidKey = MISSION_AVOID_KEY[code];

  return (
    <AgCard
      testID="weather-today-mission"
      style={[
        styles.card,
        { backgroundColor: WEATHER_UI.surface, borderColor: WEATHER_UI.border },
      ]}
    >
      <View style={styles.headingRow}>
        <View style={styles.iconTile}>
          <Target size={25} color={WEATHER_UI.field} />
        </View>
        <View style={styles.headingCopy}>
          <AgText variant="label" color="inherit" weight="semibold" style={styles.missionLabel}>
            {t("weather.todayMission")}
          </AgText>
        </View>
        {stale ? (
          <AgBadge label={t("weather.stale")} tone="warning" textStyle={styles.badgeText} />
        ) : cached ? (
          <AgBadge label={t("weather.cached")} tone="neutral" textStyle={styles.badgeText} />
        ) : (
          <AgBadge label={t("weather.live")} tone="info" textStyle={styles.badgeText} />
        )}
      </View>

      <AgText testID="weather-mission-action" variant="headingS" color="inherit" weight="bold" style={styles.action}>
        {t(actionKey, { crop })}
      </AgText>

      <View style={styles.detailList}>
        <View style={styles.detailRow}>
          <Clock3 size={16} color={WEATHER_UI.text} />
          <AgText variant="caption" color="inherit" style={[styles.confidenceText, styles.darkText]}>
            {t("weather.forecastTiming")}: {t(timingKey(code))}
          </AgText>
        </View>
        <View style={styles.detailRow}>
          <Database size={16} color={WEATHER_UI.text} />
          <AgText variant="caption" color="inherit" style={[styles.confidenceText, styles.darkText]}>
            {t("weather.dataSource")}:{" "}
            {t(
              stale
                ? "weather.stale"
                : cached
                  ? "weather.cached"
                  : "weather.live",
            )}
          </AgText>
        </View>
      </View>

      <View
        style={[
          styles.reasonBox,
          {
            backgroundColor: WEATHER_UI.surfaceSoft,
            borderColor: WEATHER_UI.border,
          },
        ]}
      >
        <AgText variant="caption" color="inherit" weight="semibold" style={styles.darkText}>
          {t("weather.missionReason")}
        </AgText>
        <AgText variant="bodySmall" color="inherit" style={styles.reasonText}>
          {stale
            ? t("weather.staleActionReason")
            : reasonKey
              ? t(reasonKey, source?.params ?? {})
              : t("weather.missionReasonFallback")}
        </AgText>
      </View>

      {avoidKey && !stale ? (
        <View style={styles.avoidRow}>
          <AlertTriangle size={19} color={colors.warning} />
          <View style={styles.avoidCopy}>
            <AgText
              variant="caption"
              weight="semibold"
              style={{ color: colors.warning }}
            >
              {t("weather.missionAvoid")}
            </AgText>
            <AgText variant="bodySmall" color="inherit" style={styles.darkText}>
              {t(avoidKey)}
            </AgText>
          </View>
        </View>
      ) : null}

      <View style={styles.confidenceRow}>
        {cached ? <WifiOff size={16} color={WEATHER_UI.text} /> : null}
        <AgText variant="caption" color="inherit" style={[styles.confidenceText, styles.darkText]}>
          {stale
            ? t("weather.staleReliabilityNote")
            : cached
              ? t("weather.cachedReliabilityNote")
              : code
                ? t("weather.liveReliabilityNote")
                : t("weather.lowReliabilityNote")}
        </AgText>
      </View>
      <View style={styles.verificationRow}>
        <ShieldCheck size={16} color={WEATHER_UI.text} />
        <AgText variant="caption" color="inherit" style={[styles.confidenceText, styles.darkText]}>
          {t("weather.expertVerificationNote")}
        </AgText>
      </View>
    </AgCard>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, borderRadius: 24, padding: 18, ...WEATHER_SHADOW },
  headingRow: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: 12 },
  iconTile: {
    width: 48,
    height: 48,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: WEATHER_UI.surfaceSoft,
  },
  headingCopy: { flex: 1 },
  missionLabel: { color: WEATHER_UI.fieldBright },
  action: { marginTop: 14, color: WEATHER_UI.text },
  badgeText: { color: "#111111" },
  darkText: { color: "#111111" },
  reasonBox: { marginTop: 16, borderWidth: 1, borderRadius: 16, padding: 14 },
  reasonText: { marginTop: 5, color: "#111111" },
  avoidRow: {
    marginTop: 14,
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
  },
  avoidCopy: { flex: 1, gap: 2 },
  confidenceRow: {
    marginTop: 14,
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
  },
  confidenceText: { flex: 1 },
  detailList: { marginTop: 12, gap: 7 },
  detailRow: { flexDirection: "row", alignItems: "center", gap: 7 },
  verificationRow: {
    marginTop: 10,
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 7,
  },
});
