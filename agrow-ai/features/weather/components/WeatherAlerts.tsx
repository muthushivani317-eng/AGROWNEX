import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgBadge, AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import {
  CATEGORY_LABEL_KEY,
  INSIGHT_MESSAGE_KEY,
  SEVERITY_TONE,
} from "../constants";
import type { WeatherInsight } from "../types";
import { CATEGORY_ICON } from "../utils/weatherIcons";
import { WeatherFreshnessNote } from "./WeatherFreshnessNote";
import { WEATHER_UI } from "../design";

function severityKey(severity: string): string {
  return `weather.severity${severity.charAt(0).toUpperCase()}${severity.slice(1)}`;
}

function InsightCard({ insight }: { insight: WeatherInsight }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const Icon = CATEGORY_ICON[insight.category];
  const messageKey = INSIGHT_MESSAGE_KEY[insight.code];
  const message = messageKey ? t(messageKey, insight.params) : insight.message;

  return (
    <View style={styles.card}>
      <View style={styles.iconTile}>
        <Icon size={18} color={colors.primary} />
      </View>
      <View style={styles.copy}>
        <View style={styles.titleRow}>
          <AgText variant="body" weight="semibold" style={styles.title}>
            {t(CATEGORY_LABEL_KEY[insight.category])}
          </AgText>
          <AgBadge
            label={t(severityKey(insight.severity))}
            tone={SEVERITY_TONE[insight.severity]}
            textStyle={styles.badgeText}
          />
        </View>
        <AgText variant="bodySmall" style={styles.message}>
          {message}
        </AgText>
      </View>
    </View>
  );
}

/** Deterministic, rule-based agricultural advice (docs: AI-ready insights). */
export function WeatherAlerts({
  insights,
  fetchedAt,
  cached,
  stale,
}: {
  insights: WeatherInsight[];
  fetchedAt?: string;
  cached?: boolean;
  stale?: boolean;
}) {
  const { t } = useTranslation();
  if (!insights.length) return null;
  return (
    <View style={styles.section}>
      <AgText variant="headingS" weight="semibold" style={styles.heading}>
        {t("weather.advice")}
      </AgText>
      <WeatherFreshnessNote
        fetchedAt={fetchedAt}
        cached={cached}
        stale={stale}
      />
      {insights.map((insight) => (
        <InsightCard key={insight.code} insight={insight} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  section: { gap: 10 },
  heading: { color: WEATHER_UI.text },
  card: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
    padding: 15,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: WEATHER_UI.border,
    backgroundColor: WEATHER_UI.surface,
  },
  iconTile: {
    width: 44,
    height: 44,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 14,
    backgroundColor: WEATHER_UI.surfaceSoft,
  },
  copy: { flex: 1, gap: 6 },
  titleRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  title: { flexGrow: 1, flexShrink: 1, color: WEATHER_UI.text },
  message: { color: WEATHER_UI.muted, lineHeight: 21 },
  badgeText: { color: WEATHER_UI.text },
});
