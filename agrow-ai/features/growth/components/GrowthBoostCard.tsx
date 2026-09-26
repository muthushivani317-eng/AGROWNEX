import { FlaskConical, Leaf, Sprout } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";

import type { GrowthAnalysis, GrowthStage } from "../types";

/** Stages that get a growth boost; maturity/harvest only get a "stop" note. */
const BOOST_STAGES: Partial<Record<GrowthStage, string>> = {
  germination: "early",
  seedling: "early",
  vegetative: "vegetative",
  flowering: "flowering",
  fruiting: "fruiting",
  maturity: "late",
  harvest: "late",
};

const C = {
  card: "#FFFFFF",
  border: "#D7DDCF",
  ink: "#101713",
  muted: "#536158",
  primary: "#176B36",
  pale: "#E8F3E5",
} as const;

/**
 * Growth boost for the latest analysed photo: the AI's own tips, then an
 * organic option (shown first and highlighted) and a chemical option. Content
 * is fixed per growth stage (no doses) so nothing is invented by the AI.
 */
export function GrowthBoostCard({ analysis }: { analysis: GrowthAnalysis }) {
  const { t } = useTranslation();
  const group = BOOST_STAGES[analysis.growthStage];
  if (!group && analysis.recommendations.length === 0) return null;
  const late = group === "late";

  return (
    <View style={styles.card}>
      <View style={styles.heading}>
        <Sprout size={20} color={C.primary} />
        <AgText variant="body" weight="bold" style={styles.ink}>
          {t("growth.boost.title")}
        </AgText>
      </View>

      {analysis.recommendations.map((tip) => (
        <AgText key={tip} variant="bodySmall" style={styles.muted}>
          {"• "}
          {tip}
        </AgText>
      ))}

      {group ? (
        <View style={styles.organic}>
          <Leaf size={15} color={C.primary} />
          <AgText variant="bodySmall" style={styles.ink}>
            <AgText variant="bodySmall" weight="semibold" style={styles.ink}>
              {t("growth.boost.organicLabel")}{" "}
            </AgText>
            {t(`growth.boost.${group}.organic`)}
          </AgText>
        </View>
      ) : null}

      {group && !late ? (
        <View style={styles.chemical}>
          <FlaskConical size={15} color={C.muted} />
          <AgText variant="bodySmall" style={styles.muted}>
            <AgText variant="bodySmall" weight="semibold" style={styles.muted}>
              {t("growth.boost.chemicalLabel")}{" "}
            </AgText>
            {t(`growth.boost.${group}.chemical`)}
          </AgText>
        </View>
      ) : null}

      {group ? (
        <AgText variant="caption" style={styles.muted}>
          {t("growth.boost.notice")}
        </AgText>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    marginBottom: 16,
    padding: 15,
    gap: 8,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.card,
  },
  heading: { flexDirection: "row", alignItems: "center", gap: 8 },
  organic: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
    padding: 10,
    borderRadius: 12,
    backgroundColor: C.pale,
  },
  chemical: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
    padding: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: C.border,
  },
  ink: { flex: 1, color: C.ink },
  muted: { flexShrink: 1, color: C.muted },
});
