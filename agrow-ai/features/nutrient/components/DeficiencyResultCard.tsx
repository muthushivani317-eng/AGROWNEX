import { FlaskConical, Leaf, ShieldQuestion } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgBadge, AgText } from "@/components/ui";
import { useLanguage } from "@/hooks/useLanguage";

import {
  SEVERITY_LABEL_KEY,
  SEVERITY_TONE,
  STATUS_LABEL_KEY,
  STATUS_TONE,
  nutrientLabelKey,
} from "../constants";
import type { NutrientAnalysis } from "../types";
import {
  mayDisplayNutrientFinding,
  safeDisplayStatus,
} from "../services/nutrientPresentation";
import { ConfidenceMeter } from "./ConfidenceMeter";
import { NUTRIENT_SHADOW, NUTRIENT_UI } from "../design";

/** The headline verdict: primary/secondary deficiency, status, confidence, severity.
 * A "not confirmed" result is shown honestly, never as a fabricated deficiency. */
export function DeficiencyResultCard({
  analysis,
}: {
  analysis: NutrientAnalysis;
}) {
  const { t } = useTranslation();
  const { language } = useLanguage();

  const displayFinding = mayDisplayNutrientFinding(analysis.resultCode);
  const displayStatus = safeDisplayStatus(analysis.resultCode, analysis.status);
  const confirmedish = displayFinding && analysis.primaryDeficiency;
  const explanation =
    language === "ta" ? analysis.explanationTamil : analysis.explanationEnglish;

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <View style={styles.titleRow}>
          {confirmedish ? (
            <Leaf size={20} color={NUTRIENT_UI.leaf} />
          ) : (
            <ShieldQuestion size={20} color={NUTRIENT_UI.muted} />
          )}
          <AgText variant="label" weight="semibold" style={styles.mutedText}>
            {t("nutrient.resultTitle")}
          </AgText>
        </View>
        <AgBadge
          light
          label={t(STATUS_LABEL_KEY[displayStatus])}
          tone={STATUS_TONE[displayStatus]}
        />
      </View>

      {displayFinding && analysis.primaryDeficiency ? (
        <View style={styles.finding}>
          <AgText variant="headingS" weight="bold" style={styles.primaryText}>
            {t(nutrientLabelKey(analysis.primaryDeficiency))}
          </AgText>
          <View style={styles.badges}>
            <AgBadge
              light
              label={t(SEVERITY_LABEL_KEY[analysis.severity])}
              tone={SEVERITY_TONE[analysis.severity]}
            />
            {analysis.affectedArea ? (
              <AgText variant="caption" style={styles.mutedText}>
                {t(`nutrient.area.${analysis.affectedArea}`)}
              </AgText>
            ) : null}
          </View>
          {analysis.secondaryDeficiency ? (
            <AgText variant="bodySmall" style={styles.mutedText}>
              {t("nutrient.secondaryLabel")}:{" "}
              {t(nutrientLabelKey(analysis.secondaryDeficiency))}
            </AgText>
          ) : null}
        </View>
      ) : (
        <View style={styles.unconfirmed}>
          <FlaskConical size={18} color={NUTRIENT_UI.muted} />
          <AgText variant="bodySmall" style={styles.mutedText} className="flex-1">
            {t("nutrient.notConfirmedMessage")}
          </AgText>
        </View>
      )}

      {displayFinding ? <ConfidenceMeter value={analysis.confidence} /> : null}

      {displayFinding && explanation ? (
        <AgText variant="bodySmall" style={styles.mutedText}>
          {explanation}
        </AgText>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: 14,
    padding: 17,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: NUTRIENT_UI.border,
    backgroundColor: NUTRIENT_UI.surface,
    ...NUTRIENT_SHADOW,
  },
  header: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  titleRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  finding: { gap: 7 },
  badges: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    gap: 8,
  },
  unconfirmed: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 9,
    borderRadius: 16,
    padding: 13,
    backgroundColor: NUTRIENT_UI.surfaceSoft,
  },
  primaryText: { color: NUTRIENT_UI.text },
  mutedText: { color: NUTRIENT_UI.muted },
});
