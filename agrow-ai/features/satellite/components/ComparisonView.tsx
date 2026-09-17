import { ArrowRight } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";

import { INDEX_LABEL_KEY } from "../constants";
import type { SatelliteHistoryEntry } from "../types";
import { SATELLITE_SHADOW, SATELLITE_UI } from "../design";

/** Compares the earliest vs latest available scene for the key indices. */
export function ComparisonView({
  entries,
}: {
  entries: SatelliteHistoryEntry[];
}) {
  const { t } = useTranslation();
  if (entries.length < 2) return null;

  // History is newest-first from the API.
  const latest = entries[0];
  const first = entries[entries.length - 1];

  const rows: { key: string; from: number | null; to: number | null }[] = [
    { key: "ndvi", from: first.ndvi, to: latest.ndvi },
    { key: "ndre", from: first.ndre, to: latest.ndre },
    { key: "ndmi", from: first.ndmi, to: latest.ndmi },
  ];

  return (
    <View style={styles.card}>
      <AgText variant="label" weight="semibold" style={styles.mutedText}>
        {t("satellite.comparison")}
      </AgText>
      <AgText variant="caption" style={styles.mutedText}>
        {(first.captureDate ?? "").slice(0, 10)} →{" "}
        {(latest.captureDate ?? "").slice(0, 10)}
      </AgText>
      {rows.map((row) => {
        const delta =
          row.from !== null && row.to !== null ? row.to - row.from : null;
        const deltaColor =
          delta === null
            ? SATELLITE_UI.muted
            : delta >= 0
              ? SATELLITE_UI.spectral
              : SATELLITE_UI.danger;
        return (
          <View key={row.key} style={styles.row}>
            <AgText
              variant="bodySmall"
              weight="semibold"
              style={styles.indexName}
            >
              {t(INDEX_LABEL_KEY[row.key])}
            </AgText>
            <AgText variant="bodySmall" style={styles.mutedText}>
              {row.from?.toFixed(2) ?? "—"}
            </AgText>
            <ArrowRight size={14} color={SATELLITE_UI.muted} />
            <AgText variant="bodySmall" weight="semibold" style={styles.primaryText}>
              {row.to?.toFixed(2) ?? "—"}
            </AgText>
            {delta !== null ? (
              <AgText variant="caption" style={{ color: deltaColor }}>
                ({delta >= 0 ? "+" : ""}
                {delta.toFixed(2)})
              </AgText>
            ) : null}
          </View>
        );
      })}
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
  row: {
    minHeight: 46,
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    gap: 8,
    paddingVertical: 5,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: SATELLITE_UI.border,
  },
  indexName: { width: 64, color: SATELLITE_UI.text },
  primaryText: { color: SATELLITE_UI.text },
  mutedText: { color: SATELLITE_UI.muted },
});
