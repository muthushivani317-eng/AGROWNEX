import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";

export function DocumentReadinessProgress({
  ready,
  total,
  light = false,
}: {
  ready: number;
  total: number;
  light?: boolean;
}) {
  const { t } = useTranslation();
  const percent = total > 0 ? Math.round((ready / total) * 100) : 0;
  return (
    <View className="mb-3 gap-1.5">
      <AgText
        variant="bodySmall"
        weight="semibold"
        color={light ? "inherit" : "default"}
        style={light ? styles.label : undefined}
      >
        {t("schemes.documentsReady", { ready, total })}
      </AgText>
      <View
        className="h-2 overflow-hidden rounded-full bg-border"
        style={light ? styles.track : undefined}
      >
        <View
          className="h-full rounded-full bg-success"
          style={[
            light ? styles.fill : undefined,
            { width: `${Math.max(0, Math.min(100, percent))}%` },
          ]}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  label: { color: "#4F605C" },
  track: {
    height: 8,
    borderRadius: 4,
    backgroundColor: "#DFE5D9",
    overflow: "hidden",
  },
  fill: { height: 8, borderRadius: 4, backgroundColor: "#238546" },
});
