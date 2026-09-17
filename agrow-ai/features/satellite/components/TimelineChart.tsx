import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import type { TimelinePoint } from "../types";
import { SATELLITE_SHADOW, SATELLITE_UI } from "../design";

type IndexKey = "ndvi" | "ndre" | "ndmi";

/** A lightweight bar chart of one vegetation index across the timeline (no chart
 * library — pure views). Missing values render as an empty slot, never invented. */
export function TimelineChart({
  points,
  indexKey,
  titleKey,
}: {
  points: TimelinePoint[];
  indexKey: IndexKey;
  titleKey: string;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const recent = points.slice(-8);

  return (
    <View style={styles.card}>
      <AgText variant="bodySmall" weight="semibold" style={styles.title}>
        {t(titleKey)}
      </AgText>
      {recent.length === 0 ? (
        <AgText variant="caption" style={styles.axisLabel}>
          {t("satellite.noTimeline")}
        </AgText>
      ) : (
        <View style={styles.chart}>
          {recent.map((p) => {
            const value = p[indexKey];
            const pct =
              value === null
                ? 0
                : Math.max(2, Math.min(100, ((value + 1) / 2) * 100));
            const color =
              value === null
                ? colors.border
                : value >= 0.5
                  ? colors.success
                  : colors.warning;
            return (
              <View key={p.period} style={styles.column}>
                <View style={styles.barSpace}>
                  <View
                    style={[
                      styles.bar,
                      { height: `${pct}%`, backgroundColor: color },
                    ]}
                    accessibilityLabel={`${p.period}: ${value ?? "n/a"}`}
                  />
                </View>
                <AgText variant="caption" style={styles.axisLabel} numberOfLines={1}>
                  {p.period.slice(-3)}
                </AgText>
              </View>
            );
          })}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: 10,
    padding: 17,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: SATELLITE_UI.border,
    backgroundColor: SATELLITE_UI.surface,
    ...SATELLITE_SHADOW,
  },
  title: { color: SATELLITE_UI.text },
  axisLabel: { color: SATELLITE_UI.muted },
  chart: {
    height: 130,
    flexDirection: "row",
    alignItems: "flex-end",
    justifyContent: "space-between",
    gap: 5,
    paddingTop: 8,
  },
  column: { flex: 1, alignItems: "center", gap: 5 },
  barSpace: {
    width: "100%",
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: SATELLITE_UI.surfaceSoft,
    borderRadius: 6,
    overflow: "hidden",
  },
  bar: { width: "100%", borderTopLeftRadius: 5, borderTopRightRadius: 5 },
});
