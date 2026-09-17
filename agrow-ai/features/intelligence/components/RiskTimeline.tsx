import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgCard, AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import { scoreTone } from "../constants";
import type { IntelligenceHistoryEntry, RiskLevel } from "../types";
import { INTELLIGENCE_COLORS as C } from "../design";

/**
 * A lightweight bar chart of the farm's overall health score over time (no chart
 * library — pure views). The most recent entries are shown; a missing score renders as
 * an empty slot, never invented. This is the farm-health / risk trend ("risk timeline").
 */
export function RiskTimeline({
  entries,
}: {
  entries: IntelligenceHistoryEntry[];
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();

  // History arrives newest-first; show oldest→newest left→right.
  const recent = entries.slice(0, 10).reverse();

  const toneHex = (tone: "success" | "warning" | "danger" | "neutral") => {
    if (tone === "success") return C.primary;
    if (tone === "warning") return C.warning;
    if (tone === "danger") return C.danger;
    return C.border;
  };

  const riskHex: Record<RiskLevel, string> = {
    low: C.primary,
    medium: C.info,
    high: C.warning,
    critical: C.danger,
  };

  return (
    <AgCard style={styles.card}>
      <AgText variant="bodySmall" weight="semibold" style={styles.ink}>
        {t("intelligence.healthTrend")}
      </AgText>
      {recent.length === 0 ? (
        <AgText variant="caption" color="muted">
          {t("intelligence.noTrend")}
        </AgText>
      ) : (
        <View className="h-28 flex-row items-end justify-between gap-1">
          {recent.map((entry) => {
            const score = entry.overallHealthScore;
            const pct = score === null ? 2 : Math.max(4, Math.min(100, score));
            const color =
              score === null ? colors.border : toneHex(scoreTone(score));
            return (
              <View key={entry.id} className="flex-1 items-center gap-1">
                <View className="w-full flex-1 justify-end">
                  <View
                    style={{ height: `${pct}%`, backgroundColor: color }}
                    className="w-full rounded-t-sm"
                    accessibilityLabel={`${entry.recordedAt.slice(0, 10)}: ${
                      score ?? t("intelligence.noData")
                    }, ${t(`intelligence.risk${entry.overallRisk[0].toUpperCase()}${entry.overallRisk.slice(1)}`)}`}
                  />
                </View>
                <View
                  className="h-1.5 w-1.5 rounded-full"
                  style={{ backgroundColor: riskHex[entry.overallRisk] }}
                />
              </View>
            );
          })}
        </View>
      )}
    </AgCard>
  );
}

const styles = StyleSheet.create({
  card: { gap: 10, backgroundColor: C.surface, borderColor: C.border },
  ink: { color: C.ink },
});
