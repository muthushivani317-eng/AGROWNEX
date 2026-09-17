import { ArrowLeft, Layers3 } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgPressable, AgText } from "@/components/ui";

import { SOIL_UI } from "../design";

export function SoilFeatureHeader({
  title,
  subtitle,
  onBack,
}: {
  title: string;
  subtitle?: string;
  onBack: () => void;
}) {
  const { t } = useTranslation();
  return (
    <View style={styles.header}>
      <View style={styles.topRow}>
        <AgPressable
          onPress={onBack}
          accessibilityRole="button"
          accessibilityLabel={t("common.back")}
          style={({ pressed }) => [
            styles.backButton,
            pressed && styles.pressed,
          ]}
        >
          <ArrowLeft size={24} color={SOIL_UI.green} />
        </AgPressable>
        <View style={styles.featureMark} accessible={false}>
          <Layers3 size={23} color={SOIL_UI.white} />
        </View>
        <AgText variant="label" weight="bold" style={styles.eyebrow}>
          {t("soil.title")}
        </AgText>
      </View>
      <AgText
        variant="headingL"
        weight="bold"
        style={styles.title}
        accessibilityRole="header"
      >
        {title}
      </AgText>
      {subtitle ? (
        <AgText variant="body" style={styles.subtitle}>
          {subtitle}
        </AgText>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  header: { width: "100%", gap: 8, paddingTop: 8, paddingBottom: 8 },
  topRow: {
    minHeight: 48,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  backButton: {
    width: 48,
    height: 48,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: SOIL_UI.border,
    backgroundColor: SOIL_UI.surface,
    alignItems: "center",
    justifyContent: "center",
  },
  featureMark: {
    width: 40,
    height: 40,
    borderRadius: 13,
    backgroundColor: SOIL_UI.green,
    alignItems: "center",
    justifyContent: "center",
  },
  eyebrow: { color: SOIL_UI.earth, letterSpacing: 0.5, flex: 1 },
  title: { color: SOIL_UI.text, lineHeight: 36 },
  subtitle: { color: SOIL_UI.muted, lineHeight: 23, maxWidth: 560 },
  pressed: { opacity: 0.74 },
});
