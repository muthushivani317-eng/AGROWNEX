import { Image } from "expo-image";
import { ArrowRight } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgBadge, AgCard, AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import { STAGE_LABEL_KEY } from "../constants";
import type { GrowthImage } from "../types";
import { HealthDelta } from "./HealthDelta";

/** Side-by-side comparison of the first and latest photo in a session. */
export function GrowthComparison({
  first,
  latest,
}: {
  first: GrowthImage;
  latest: GrowthImage;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();

  const firstHealth = first.analysis?.healthScore ?? null;
  const latestHealth = latest.analysis?.healthScore ?? null;
  const delta =
    firstHealth != null && latestHealth != null
      ? latestHealth - firstHealth
      : null;

  return (
    <AgCard style={styles.card}>
      <AgText
        variant="body"
        weight="semibold"
        style={styles.ink}
        className="mb-3"
      >
        {t("growth.comparisonTitle")}
      </AgText>
      <View className="flex-row items-center gap-2">
        <Column
          image={first}
          label={t("growth.weekLabel", { count: first.weekNumber })}
        />
        <ArrowRight size={20} color={colors.textMuted} />
        <Column
          image={latest}
          label={t("growth.weekLabel", { count: latest.weekNumber })}
        />
      </View>
      <View className="mt-3 flex-row items-center justify-between border-t border-border pt-3">
        <AgText variant="bodySmall" style={styles.muted}>
          {t("growth.healthChange")}
        </AgText>
        <HealthDelta delta={delta} />
      </View>
    </AgCard>
  );
}

function Column({ image, label }: { image: GrowthImage; label: string }) {
  const { t } = useTranslation();
  const stage = image.analysis?.growthStage ?? "unknown";
  return (
    <View className="flex-1 items-center gap-1.5">
      <Image
        source={{ uri: image.imageUrl }}
        style={{ width: "100%", aspectRatio: 1, borderRadius: 12 }}
        contentFit="cover"
      />
      <AgText variant="caption" weight="semibold" style={styles.ink}>
        {label}
      </AgText>
      <AgBadge label={t(STAGE_LABEL_KEY[stage])} tone="info" />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",
    borderColor: "#D7DDCF",
    borderRadius: 12,
  },
  ink: { color: "#101713" },
  muted: { color: "#536158" },
});
