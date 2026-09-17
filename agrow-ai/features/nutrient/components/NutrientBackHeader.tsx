import { useRouter } from "expo-router";
import { ArrowLeft, FlaskConical } from "lucide-react-native";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { StyleSheet, TouchableOpacity, View } from "react-native";

import { AgText } from "@/components/ui";
import { NUTRIENT_SHADOW, NUTRIENT_UI } from "../design";

/** A back row with a title and optional right accessory, reused by the screens. */
export function NutrientBackHeader({
  title,
  right,
}: {
  title: string;
  right?: ReactNode;
}) {
  const { t } = useTranslation();
  const router = useRouter();
  return (
    <View style={styles.header}>
      <TouchableOpacity
        onPress={() => router.back()}
        hitSlop={8}
        accessibilityRole="button"
        accessibilityLabel={t("common.back")}
        activeOpacity={0.7}
        style={styles.backButton}
      >
        <ArrowLeft size={23} color={NUTRIENT_UI.text} />
      </TouchableOpacity>
      <View style={styles.titleGroup}>
        <View style={styles.icon}>
          <FlaskConical size={20} color={NUTRIENT_UI.white} />
        </View>
        <AgText variant="headingS" weight="bold" style={styles.title}>
          {title}
        </AgText>
      </View>
      {right ?? null}
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    minHeight: 64,
    paddingTop: 8,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  backButton: {
    width: 48,
    height: 48,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: NUTRIENT_UI.surface,
    ...NUTRIENT_SHADOW,
  },
  titleGroup: { flex: 1, flexDirection: "row", alignItems: "center", gap: 9 },
  icon: {
    width: 38,
    height: 38,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: NUTRIENT_UI.chlorophyll,
  },
  title: { flex: 1, color: NUTRIENT_UI.text },
});
