import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import { INDEX_LABEL_KEY } from "../constants";
import type { SatelliteIndex } from "../types";
import { SATELLITE_SHADOW, SATELLITE_UI } from "../design";

/** Vegetation index gauges (NDVI/NDRE/EVI/NDMI) — the field mean as a bar + value.
 * A missing index is shown honestly, never fabricated. */
export function IndexGauges({ indices }: { indices: SatelliteIndex[] }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();

  if (indices.length === 0) {
    return (
      <View style={styles.card}>
        <AgText variant="bodySmall" style={styles.mutedText}>
          {t("satellite.noIndices")}
        </AgText>
      </View>
    );
  }

  return (
    <View style={styles.card}>
      <AgText variant="label" weight="semibold" style={styles.mutedText}>
        {t("satellite.indices")}
      </AgText>
      {indices.map((idx) => {
        const value = idx.mean;
        // NDVI/NDRE/NDMI ∈ [-1, 1]; map to a 0-100% bar width.
        const pct =
          value === null
            ? 0
            : Math.max(0, Math.min(100, ((value + 1) / 2) * 100));
        const barColor =
          value === null
            ? colors.border
            : value >= 0.6
              ? colors.success
              : value >= 0.3
                ? colors.warning
                : colors.danger;
        return (
          <View key={idx.indexName} style={styles.indexRow}>
            <View style={styles.labelRow}>
              <AgText variant="bodySmall" weight="semibold" style={styles.primaryText}>
                {t(INDEX_LABEL_KEY[idx.indexName] ?? idx.indexName)}
              </AgText>
              <AgText variant="bodySmall" style={styles.mutedText}>
                {value === null
                  ? t("satellite.notAvailable")
                  : value.toFixed(2)}
              </AgText>
            </View>
            <View
              style={styles.track}
              accessibilityLabel={`${idx.indexName} ${value ?? "n/a"}`}
            >
              <View
                style={[
                  styles.fill,
                  { width: `${pct}%`, backgroundColor: barColor },
                ]}
              />
            </View>
          </View>
        );
      })}
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
  indexRow: { gap: 7 },
  labelRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  track: {
    height: 10,
    borderRadius: 5,
    overflow: "hidden",
    backgroundColor: SATELLITE_UI.border,
  },
  fill: { height: 10, borderRadius: 5 },
  primaryText: { color: SATELLITE_UI.text },
  mutedText: { color: SATELLITE_UI.muted },
});
