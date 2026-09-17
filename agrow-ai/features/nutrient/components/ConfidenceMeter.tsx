import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";

import { CONFIDENCE_CONFIRM, CONFIDENCE_POSSIBLE } from "../constants";
import { NUTRIENT_UI } from "../design";

/** Confidence bar (0-100) coloured by band. A visual finding is never 100% certain. */
export function ConfidenceMeter({ value }: { value: number | null }) {
  const { t } = useTranslation();
  const pct = Math.max(0, Math.min(100, value ?? 0));
  const tone =
    pct >= CONFIDENCE_CONFIRM
      ? NUTRIENT_UI.leaf
      : pct >= CONFIDENCE_POSSIBLE
        ? NUTRIENT_UI.amber
        : NUTRIENT_UI.danger;

  return (
    <View
      accessibilityRole="progressbar"
      accessibilityValue={{ min: 0, max: 100, now: Math.round(pct) }}
      accessibilityLabel={`${t("nutrient.confidence")} ${Math.round(pct)}%`}
    >
      <View style={styles.header}>
        <AgText variant="caption" style={styles.mutedText}>
          {t("nutrient.confidence")}
        </AgText>
        <AgText variant="caption" weight="semibold" style={styles.primaryText}>
          {value == null ? "—" : `${Math.round(pct)}%`}
        </AgText>
      </View>
      <View style={styles.track}>
        <View
          style={[styles.fill, { width: `${pct}%`, backgroundColor: tone }]}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    marginBottom: 6,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  track: {
    width: "100%",
    height: 10,
    overflow: "hidden",
    borderRadius: 5,
    backgroundColor: NUTRIENT_UI.border,
  },
  fill: { height: 10, borderRadius: 5 },
  primaryText: { color: NUTRIENT_UI.text },
  mutedText: { color: NUTRIENT_UI.muted },
});
