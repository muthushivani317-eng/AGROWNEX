import { FlaskConical, Leaf, Sprout, TriangleAlert } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import type { ChemicalPolicy } from "@/features/organic/chemicalPolicy";
import { StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";

import { STAGE_LABEL_KEY } from "../constants";
import type { GrowthAnalysis, GrowthScheduleStatus, GrowthStage } from "../types";

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
  amber: "#9A5B00",
  amberSoft: "#FFF4E0",
} as const;

/**
 * Growth boost for the latest analysed photo: the AI's own tips, then an
 * organic option (shown first and highlighted) and a chemical option. Content
 * is fixed per growth stage (no doses) so nothing is invented by the AI.
 */
export function GrowthBoostCard({
  analysis,
  chemicalPolicy = "show",
  scheduleStatus = null,
}: {
  analysis: GrowthAnalysis | null;
  /** Farm's organic mode decides whether the chemical option is shown. */
  chemicalPolicy?: ChemicalPolicy;
  /** Behind schedule → organic boost leads the card. */
  scheduleStatus?: GrowthScheduleStatus | null;
}) {
  const { t } = useTranslation();
  const behind = Boolean(scheduleStatus?.behind);
  const stage =
    analysis && BOOST_STAGES[analysis.growthStage]
      ? analysis.growthStage
      : behind
        ? (scheduleStatus?.observedStage ?? scheduleStatus?.expectedStage ?? null)
        : null;
  const group = stage ? BOOST_STAGES[stage] : undefined;
  const tips = analysis?.recommendations ?? [];
  if (!group && tips.length === 0 && !behind) return null;
  const late = group === "late";
  const stageLabel = (value: GrowthStage | null | undefined) =>
    value ? t(STAGE_LABEL_KEY[value]) : "";

  const organicBlock = group ? (
    <View style={[styles.organic, behind && styles.organicLead]}>
      <Leaf size={15} color={C.primary} />
      <AgText variant="bodySmall" style={styles.ink}>
        <AgText variant="bodySmall" weight="semibold" style={styles.ink}>
          {t("growth.boost.organicLabel")}{" "}
        </AgText>
        {t(`growth.boost.${group}.organic`)}
      </AgText>
    </View>
  ) : null;

  return (
    <View style={styles.card}>
      <View style={styles.heading}>
        <Sprout size={20} color={C.primary} />
        <AgText variant="body" weight="bold" style={styles.ink}>
          {t("growth.boost.title")}
        </AgText>
      </View>

      {behind && scheduleStatus ? (
        <View style={styles.behind} accessibilityRole="alert">
          <TriangleAlert size={16} color={C.amber} />
          <View style={styles.behindCopy}>
            <AgText variant="bodySmall" weight="bold" style={styles.amber}>
              {t("growth.boost.behindTitle")}
            </AgText>
            {scheduleStatus.reasons.includes("overdue_task") ? (
              <AgText variant="caption" style={styles.amber}>
                {t("growth.boost.behindOverdue", { count: scheduleStatus.overdueTasks })}
              </AgText>
            ) : null}
            {scheduleStatus.reasons.includes("stage_lagging") ? (
              <AgText variant="caption" style={styles.amber}>
                {t("growth.boost.behindStage", {
                  observed: stageLabel(scheduleStatus.observedStage),
                  expected: stageLabel(scheduleStatus.expectedStage),
                })}
              </AgText>
            ) : null}
          </View>
        </View>
      ) : null}

      {behind ? organicBlock : null}

      {tips.map((tip) => (
        <AgText key={tip} variant="bodySmall" style={styles.muted}>
          {"• "}
          {tip}
        </AgText>
      ))}

      {behind ? null : organicBlock}

      {group && !late && chemicalPolicy !== "hide" ? (
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

      {group && !late && chemicalPolicy !== "show" ? (
        <AgText variant="caption" style={styles.muted}>
          {t(chemicalPolicy === "hide" ? "organic.chemicalNotAllowed" : "organic.chemicalLastResort")}
        </AgText>
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
  behind: {
    flexDirection: "row",
    gap: 8,
    padding: 10,
    borderRadius: 12,
    backgroundColor: C.amberSoft,
  },
  behindCopy: { flex: 1, gap: 2 },
  amber: { color: C.amber },
  organicLead: { borderWidth: 1.5, borderColor: C.primary },
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
