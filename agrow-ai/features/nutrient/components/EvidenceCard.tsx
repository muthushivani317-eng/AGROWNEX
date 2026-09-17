import {
  Droplets,
  Layers,
  Satellite,
  Stethoscope,
  TriangleAlert,
} from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";

import type { NutrientAnalysis } from "../types";
import { NUTRIENT_SHADOW, NUTRIENT_UI } from "../design";

/** Shows how the visual finding was cross-checked with the other modules — the
 * corroboration is transparent, not a black box (docs: combine with Soil/Satellite/
 * Weather; never override another module without evidence). */
export function EvidenceCard({ analysis }: { analysis: NutrientAnalysis }) {
  const { t } = useTranslation();

  const rows: {
    key: string;
    icon: typeof Layers;
    color: string;
    label: string;
  }[] = [];
  if (analysis.soilReference) {
    rows.push({
      key: "soil",
      icon: Layers,
      color: NUTRIENT_UI.leaf,
      label: t("nutrient.evidenceSoil"),
    });
  }
  if (analysis.satelliteReference) {
    rows.push({
      key: "satellite",
      icon: Satellite,
      color: NUTRIENT_UI.mineral,
      label: t("nutrient.evidenceSatellite"),
    });
  }
  if (analysis.weatherReference) {
    rows.push({
      key: "weather",
      icon: Droplets,
      color: NUTRIENT_UI.mineral,
      label: t("nutrient.evidenceWeather"),
    });
  }

  const hasEvidence =
    rows.length > 0 ||
    analysis.diseaseConflict ||
    analysis.evidenceMissing.length > 0;
  if (!hasEvidence) return null;

  return (
    <View style={styles.card}>
      <AgText variant="label" weight="semibold" style={styles.mutedText}>
        {t("nutrient.evidenceTitle")}
      </AgText>
      {rows.map((row) => {
        const Icon = row.icon;
        return (
          <View key={row.key} style={styles.evidenceRow}>
            <Icon size={16} color={row.color} />
            <AgText variant="bodySmall" className="flex-1" style={styles.primaryText}>
              {row.label}
            </AgText>
          </View>
        );
      })}
      {analysis.diseaseConflict ? (
        <View style={styles.warningRow}>
          <Stethoscope size={16} color={NUTRIENT_UI.amber} />
          <AgText variant="caption" style={styles.mutedText} className="flex-1">
            {t("nutrient.diseaseConflict")}
          </AgText>
        </View>
      ) : null}
      {analysis.needsTest ? (
        <View style={styles.evidenceRow}>
          <TriangleAlert size={14} color={NUTRIENT_UI.muted} />
          <AgText variant="caption" style={styles.mutedText} className="flex-1">
            {t("nutrient.needsTest")}
          </AgText>
        </View>
      ) : null}
      {analysis.evidenceMissing.length > 0 ? (
        <View style={styles.missingGroup}>
          <AgText variant="caption" weight="semibold" style={styles.mutedText}>
            {t("nutrient.evidenceMissing")}
          </AgText>
          {analysis.evidenceMissing.map((code) => (
            <AgText key={code} variant="caption" style={styles.mutedText}>
              • {t(`nutrient.evidenceCode.${code}`)}
            </AgText>
          ))}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: 11,
    padding: 17,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: NUTRIENT_UI.mineral,
    backgroundColor: NUTRIENT_UI.surface,
    ...NUTRIENT_SHADOW,
  },
  evidenceRow: { flexDirection: "row", alignItems: "flex-start", gap: 9 },
  warningRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 9,
    borderRadius: 14,
    padding: 11,
    backgroundColor: "#FFF3D8",
  },
  missingGroup: { gap: 5, paddingTop: 3 },
  primaryText: { color: NUTRIENT_UI.text },
  mutedText: { color: NUTRIENT_UI.muted },
});
