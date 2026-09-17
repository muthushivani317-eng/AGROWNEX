import { useRouter } from "expo-router";
import { ArrowLeft, Orbit } from "lucide-react-native";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgPressable, AgText } from "@/components/ui";
import { SATELLITE_SHADOW, SATELLITE_UI } from "../design";

/** A back row with a title and optional right accessory, reused by the screens. */
export function SatelliteBackHeader({
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
      <AgPressable
        onPress={() => router.back()}
        hitSlop={8}
        accessibilityRole="button"
        accessibilityLabel={t("common.back")}
        style={styles.backButton}
      >
        <ArrowLeft size={23} color={SATELLITE_UI.text} />
      </AgPressable>
      <View style={styles.titleGroup}>
        <View style={styles.orbitIcon}>
          <Orbit size={20} color={SATELLITE_UI.spectral} />
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
    backgroundColor: SATELLITE_UI.surface,
    ...SATELLITE_SHADOW,
  },
  titleGroup: { flex: 1, flexDirection: "row", alignItems: "center", gap: 9 },
  orbitIcon: {
    width: 38,
    height: 38,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: SATELLITE_UI.orbit,
  },
  title: { flex: 1, color: SATELLITE_UI.text },
});
