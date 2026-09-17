import { useRouter } from "expo-router";
import { ArrowLeft, Wheat } from "lucide-react-native";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Pressable, StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";

import { PRODUCE_COLORS as C } from "../produceTheme";

/** A back row with a title and optional right accessory, reused by produce screens. */
export function ProduceBackHeader({
  title,
  right,
}: {
  title: string;
  right?: ReactNode;
}) {
  const { t } = useTranslation();
  const router = useRouter();
  return (
    <View style={styles.row}>
      <Pressable
        onPress={() => router.back()}
        hitSlop={8}
        accessibilityRole="button"
        accessibilityLabel={t("common.back")}
        style={styles.back}
      >
        <ArrowLeft size={25} color={C.ink} />
      </Pressable>
      <View style={styles.mark}>
        <Wheat size={24} color={C.paper} />
      </View>
      <AgText
        variant="headingS"
        weight="bold"
        numberOfLines={2}
        style={styles.title}
      >
        {title}
      </AgText>
      {right ?? null}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    paddingTop: 12,
    paddingBottom: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  back: {
    width: 48,
    height: 48,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.paper,
    alignItems: "center",
    justifyContent: "center",
  },
  mark: {
    width: 48,
    height: 48,
    borderRadius: 16,
    backgroundColor: C.green,
    alignItems: "center",
    justifyContent: "center",
  },
  title: { flex: 1, color: C.ink },
});
