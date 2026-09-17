import { Image } from "expo-image";
import dayjs from "dayjs";
import { Activity, Trash2 } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgBadge, AgCard, AgPressable, AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import { STAGE_LABEL_KEY, VIGOR_LABEL_KEY, VIGOR_TONE } from "../constants";
import type { GrowthImage } from "../types";

/** A single uploaded growth photo with its AI observation (history + session). */
export function GrowthCard({
  image,
  onPress,
  onDelete,
  busy,
}: {
  image: GrowthImage;
  onPress?: (image: GrowthImage) => void;
  onDelete?: (image: GrowthImage) => void;
  busy?: boolean;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const analysis = image.analysis;
  const summary =
    analysis?.growthSummaryTamil || analysis?.growthSummaryEnglish || null;

  return (
    <AgCard style={styles.card}>
      <View className="flex-row gap-3">
        <AgPressable
          onPress={() => onPress?.(image)}
          accessibilityRole="imagebutton"
          accessibilityLabel={t("growth.viewPhoto")}
        >
          <Image
            source={{ uri: image.imageUrl }}
            style={{ width: 76, height: 76, borderRadius: 12 }}
            contentFit="cover"
          />
        </AgPressable>
        <View className="flex-1">
          <View className="flex-row items-center justify-between">
            <AgText variant="body" weight="bold" style={styles.ink}>
              {t("growth.weekLabel", { count: image.weekNumber })}
            </AgText>
            {onDelete ? (
              <AgPressable
                onPress={() => onDelete(image)}
                disabled={busy}
                accessibilityRole="button"
                accessibilityLabel={t("growth.deletePhoto")}
                className="h-9 w-9 items-center justify-center"
              >
                <Trash2 size={17} color={colors.textMuted} />
              </AgPressable>
            ) : null}
          </View>
          <AgText variant="caption" style={styles.muted}>
            {dayjs(image.capturedAt).format("ddd, DD MMM YYYY")}
          </AgText>
          <View className="mt-1.5 flex-row flex-wrap items-center gap-2">
            {analysis ? (
              <>
                <AgBadge
                  label={t(STAGE_LABEL_KEY[analysis.growthStage])}
                  tone="info"
                />
                <AgBadge
                  label={t(VIGOR_LABEL_KEY[analysis.plantVigor])}
                  tone={VIGOR_TONE[analysis.plantVigor]}
                />
                {analysis.healthScore != null ? (
                  <View className="flex-row items-center gap-1">
                    <Activity size={13} color={colors.primary} />
                    <AgText
                      variant="caption"
                      weight="semibold"
                      style={styles.ink}
                    >
                      {analysis.healthScore}
                    </AgText>
                  </View>
                ) : null}
              </>
            ) : (
              <AgText variant="caption" style={styles.muted}>
                {t("growth.noAnalysis")}
              </AgText>
            )}
          </View>
        </View>
      </View>
      {summary ? (
        <AgText
          variant="bodySmall"
          style={styles.body}
          numberOfLines={2}
          className="mt-3"
        >
          {summary}
        </AgText>
      ) : null}
    </AgCard>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",
    borderColor: "#D7DDCF",
    borderRadius: 12,
  },
  ink: { color: "#101713" },
  body: { color: "#26332B" },
  muted: { color: "#536158" },
});
