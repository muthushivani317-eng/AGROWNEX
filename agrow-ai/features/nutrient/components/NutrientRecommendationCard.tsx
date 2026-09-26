import {
  FlaskConical,
  Info,
  Leaf,
  Sprout,
  TriangleAlert,
  UserCog,
} from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgBadge, AgText } from "@/components/ui";

import { REC_SEVERITY_TONE } from "../constants";
import type { NutrientRecommendation } from "../types";
import { NUTRIENT_UI } from "../design";

/** A single generic agronomic recommendation (localized from its code; no brands). */
export function NutrientRecommendationCard({
  rec,
}: {
  rec: NutrientRecommendation;
}) {
  const { t } = useTranslation();

  const Icon =
    rec.category === "test"
      ? FlaskConical
      : rec.category === "expert"
        ? UserCog
        : rec.severity === "critical" || rec.severity === "warning"
          ? TriangleAlert
          : rec.category === "nutrient"
            ? Sprout
            : Info;
  const iconColor =
    rec.severity === "critical"
      ? NUTRIENT_UI.danger
      : rec.severity === "warning"
        ? NUTRIENT_UI.amber
        : NUTRIENT_UI.leaf;

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
            label={t(`nutrient.recSeverity.${rec.severity}`)}
            tone={REC_SEVERITY_TONE[rec.severity] ?? "info"}
          />
        </View>
        <AgText variant="bodySmall" style={styles.body}>
          {t(`${rec.code}.body`)}
        </AgText>
        {rec.category === "nutrient" ? (
          <View style={styles.organicTip}>
            <Leaf size={14} color={NUTRIENT_UI.leaf} />
            <AgText variant="bodySmall" style={styles.organicTipText}>
              <AgText
                variant="bodySmall"
                weight="semibold"
                style={styles.organicTipText}
              >
                {t("nutrient.organicWay")}{" "}
              </AgText>
              {t(`${rec.code}.organicTip`)}
            </AgText>
          </View>
        ) : null}
        {rec.category === "nutrient" ? (
          <View style={styles.chemicalTip}>
            <FlaskConical size={14} color={NUTRIENT_UI.muted} />
            <AgText variant="bodySmall" style={styles.chemicalTipText}>
              <AgText
                variant="bodySmall"
                weight="semibold"
                style={styles.chemicalTipText}
              >
                {t("nutrient.chemicalWay")}{" "}
              </AgText>
              {t(`${rec.code}.chemicalTip`)}
            </AgText>
          </View>
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
    borderColor: NUTRIENT_UI.border,
    backgroundColor: NUTRIENT_UI.surface,
  },
  icon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  copy: { flex: 1, gap: 6 },
  organicTip: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 6,
    marginTop: 2,
    padding: 10,
    borderRadius: 12,
    backgroundColor: NUTRIENT_UI.surfaceSoft,
  },
  organicTipText: { flex: 1, color: NUTRIENT_UI.text },
  chemicalTip: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 6,
    padding: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: NUTRIENT_UI.border,
  },
  chemicalTipText: { flex: 1, color: NUTRIENT_UI.muted },
  titleRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  title: { flexGrow: 1, flexShrink: 1, color: NUTRIENT_UI.text },
  body: { color: NUTRIENT_UI.muted },
});
