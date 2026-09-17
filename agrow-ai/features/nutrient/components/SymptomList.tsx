import { useTranslation } from "react-i18next";
import { CheckCircle2 } from "lucide-react-native";
import { StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";

import { symptomLabelKey } from "../constants";
import { NUTRIENT_SHADOW, NUTRIENT_UI } from "../design";

/** The visible leaf symptoms the model observed (localized from their codes). */
export function SymptomList({ symptoms }: { symptoms: string[] }) {
  const { t } = useTranslation();
  if (symptoms.length === 0) return null;

  return (
    <View style={styles.card}>
      <AgText variant="label" weight="semibold" style={styles.mutedText}>
        {t("nutrient.symptomsTitle")}
      </AgText>
      {symptoms.map((code) => (
        <View key={code} style={styles.row}>
          <CheckCircle2 size={17} color={NUTRIENT_UI.leaf} />
          <AgText variant="bodySmall" className="flex-1" style={styles.primaryText}>
            {t(symptomLabelKey(code))}
          </AgText>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: 11,
    padding: 17,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: NUTRIENT_UI.border,
    backgroundColor: NUTRIENT_UI.surface,
    ...NUTRIENT_SHADOW,
  },
  row: { flexDirection: "row", alignItems: "flex-start", gap: 9 },
  primaryText: { color: NUTRIENT_UI.text },
  mutedText: { color: NUTRIENT_UI.muted },
});
