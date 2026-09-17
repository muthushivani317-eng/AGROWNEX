import { Info, Sprout, TriangleAlert } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgBadge, AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import { PARAMETER_LABEL_KEY, SEVERITY_TONE } from "../constants";
import type { SoilRecommendation } from "../types";
import { SOIL_SHADOW, SOIL_UI } from "../design";

/** A single generic agronomic recommendation (localized from its code; no brands). */
export function SoilRecommendationCard({ rec }: { rec: SoilRecommendation }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const Icon =
    rec.severity === "critical" || rec.severity === "warning"
      ? TriangleAlert
      : rec.severity === "advice"
        ? Sprout
        : Info;
  const iconColor =
    rec.severity === "critical"
      ? colors.danger
      : rec.severity === "warning"
        ? colors.warning
        : colors.primary;

  return (
    <View style={styles.card}>
      <View style={[styles.icon, { backgroundColor: `${iconColor}1A` }]}>
        <Icon size={18} color={iconColor} />
      </View>
      <View style={styles.copy}>
        <View style={styles.titleRow}>
          <AgText variant="body" weight="semibold" style={styles.title}>
            {t(`${rec.code}.title`)}
          </AgText>
          <AgBadge
            light
            label={t(`soil.severity.${rec.severity}`)}
            tone={SEVERITY_TONE[rec.severity]}
          />
        </View>
        <AgText variant="bodySmall" style={styles.body}>
          {t(`${rec.code}.body`)}
        </AgText>
        {rec.parameter && rec.value !== null ? (
          <AgText variant="caption" style={styles.body}>
            {t(PARAMETER_LABEL_KEY[rec.parameter] ?? rec.parameter)}:{" "}
            {rec.value}
            {rec.unit ? ` ${rec.unit}` : ""}
          </AgText>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: "row",
    gap: 12,
    padding: 15,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: SOIL_UI.border,
    backgroundColor: SOIL_UI.surface,
    ...SOIL_SHADOW,
  },
  icon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  copy: { flex: 1, gap: 6 },
  titleRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  title: { flexGrow: 1, flexShrink: 1, color: SOIL_UI.text },
  body: { color: SOIL_UI.muted },
});
