import { TrendingDown, TrendingUp, Minus } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, useWindowDimensions, View } from "react-native";

import { AgBadge, AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import {
  HEALTH_LABEL_KEY,
  HEALTH_TONE,
  MOISTURE_LABEL_KEY,
  MOISTURE_TONE,
  STRESS_LABEL_KEY,
  STRESS_TONE,
  TREND_LABEL_KEY,
} from "../constants";
import type {
  MoistureStatus,
  SatelliteSession,
  StressLevel,
  VegetationHealth,
} from "../types";
import { SATELLITE_SHADOW, SATELLITE_UI } from "../design";

/** Vegetation health card — health / stress / moisture with the capture date and
 * a clear "not available" when a value is missing (never fabricated). */
export function VegetationHealthCard({
  session,
}: {
  session: SatelliteSession;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const { width, fontScale } = useWindowDimensions();
  const compact = width < 370 || fontScale > 1.2;
  const health = (session.vegetationHealth ?? "unknown") as VegetationHealth;
  const stress = (session.stressLevel ?? "unknown") as StressLevel;
  const moisture = (session.moistureStatus ?? "unknown") as MoistureStatus;

  const TrendIcon =
    session.trend === "improving"
      ? TrendingUp
      : session.trend === "declining"
        ? TrendingDown
        : Minus;
  const trendColor =
    session.trend === "improving"
      ? colors.success
      : session.trend === "declining"
        ? colors.danger
        : colors.textMuted;

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <AgText variant="label" weight="semibold" style={styles.mutedText}>
          {t("satellite.vegetationHealth")}
        </AgText>
        <View style={styles.trend}>
          <TrendIcon size={16} color={trendColor} />
          <AgText variant="caption" style={styles.mutedText}>
            {t(TREND_LABEL_KEY[session.trend ?? "unknown"])}
          </AgText>
        </View>
      </View>

      <View style={[styles.metrics, compact && styles.metricsCompact]}>
        <Metric
          label={t("satellite.health")}
          tone={HEALTH_TONE[health]}
          value={t(HEALTH_LABEL_KEY[health])}
        />
        <Metric
          label={t("satellite.stress")}
          tone={STRESS_TONE[stress]}
          value={t(STRESS_LABEL_KEY[stress])}
        />
        <Metric
          label={t("satellite.moisture")}
          tone={MOISTURE_TONE[moisture]}
          value={t(MOISTURE_LABEL_KEY[moisture])}
        />
      </View>

      <View style={styles.metadata}>
        {session.captureDate ? (
          <AgText variant="caption" style={styles.mutedText}>
            {t("satellite.captured", { date: session.captureDate })}
          </AgText>
        ) : null}
        {session.cloudCover !== null ? (
          <AgText variant="caption" style={styles.mutedText}>
            {t("satellite.cloud", { value: Math.round(session.cloudCover) })}
          </AgText>
        ) : null}
        <AgText variant="caption" style={styles.mutedText}>
          {t("satellite.confidence", { value: session.confidence })}
        </AgText>
      </View>
    </View>
  );
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "success" | "warning" | "danger" | "info" | "neutral";
}) {
  return (
    <View style={styles.metric}>
      <AgText variant="caption" style={styles.mutedText}>
        {label}
      </AgText>
      <AgBadge light label={value} tone={tone} />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: 14,
    padding: 17,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: SATELLITE_UI.border,
    backgroundColor: SATELLITE_UI.surface,
    ...SATELLITE_SHADOW,
  },
  header: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  trend: { flexDirection: "row", alignItems: "center", gap: 5 },
  metrics: { flexDirection: "row", justifyContent: "space-between", gap: 8 },
  metricsCompact: { flexDirection: "column" },
  metric: {
    flex: 1,
    minHeight: 72,
    padding: 10,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    gap: 5,
    backgroundColor: SATELLITE_UI.surfaceSoft,
  },
  metadata: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    columnGap: 12,
    rowGap: 5,
    paddingTop: 2,
  },
  mutedText: { color: SATELLITE_UI.muted },
});
