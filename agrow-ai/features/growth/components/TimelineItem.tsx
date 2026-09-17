import { Image } from "expo-image";
import dayjs from "dayjs";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgBadge, AgPressable, AgText } from "@/components/ui";
import { RISK_LABEL_KEY, RISK_TONE, STAGE_LABEL_KEY } from "../constants";
import type { TimelineEntry } from "../types";
import { HealthDelta } from "./HealthDelta";

/**
 * One node in the Week 1 → Week 2 → … timeline: connector, photo, stage,
 * health delta and the AI summary. Tapping the photo opens the image viewer.
 */
export function TimelineItem({
  entry,
  isLast,
  onPressImage,
}: {
  entry: TimelineEntry;
  isLast: boolean;
  onPressImage?: (entry: TimelineEntry) => void;
}) {
  const { t } = useTranslation();
  return (
    <View style={styles.row}>
      {/* Connector rail */}
      <View style={styles.rail}>
        <View style={styles.dot} />
        {!isLast ? <View style={styles.line} /> : null}
      </View>

      <View style={styles.content}>
        <View className="flex-row items-center justify-between">
          <AgText variant="body" weight="bold" style={styles.ink}>
            {t("growth.weekLabel", { count: entry.weekNumber })}
          </AgText>
          <AgText variant="caption" style={styles.muted}>
            {dayjs(entry.recordedAt).format("DD MMM")}
          </AgText>
        </View>

        <View className="mt-2 flex-row gap-3">
          {entry.imageUrl ? (
            <AgPressable
              onPress={() => onPressImage?.(entry)}
              accessibilityRole="imagebutton"
              accessibilityLabel={t("growth.viewPhoto")}
            >
              <Image
                source={{ uri: entry.imageUrl }}
                style={{ width: 64, height: 64, borderRadius: 10 }}
                contentFit="cover"
              />
            </AgPressable>
          ) : null}
          <View className="flex-1 gap-1.5">
            <View className="flex-row flex-wrap items-center gap-2">
              <AgBadge
                light
                label={t(STAGE_LABEL_KEY[entry.growthStage])}
                tone="info"
              />
              <AgBadge
                light
                label={t(RISK_LABEL_KEY[entry.riskLevel])}
                tone={RISK_TONE[entry.riskLevel]}
              />
            </View>
            <View className="flex-row items-center gap-3">
              {entry.healthScore != null ? (
                <AgText variant="caption" style={styles.muted}>
                  {t("growth.healthScore")}:{" "}
                  <AgText
                    variant="caption"
                    weight="semibold"
                    style={styles.ink}
                  >
                    {entry.healthScore}
                  </AgText>
                </AgText>
              ) : null}
              <HealthDelta delta={entry.healthDelta} />
            </View>
          </View>
        </View>

        {entry.summary ? (
          <AgText variant="bodySmall" style={styles.summary} className="mt-2">
            {entry.summary}
          </AgText>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", gap: 12 },
  rail: { alignItems: "center" },
  dot: { width: 12, height: 12, borderRadius: 6, backgroundColor: "#176B36" },
  line: { width: 2, flex: 1, backgroundColor: "#D7DDCF" },
  content: { flex: 1, paddingBottom: 24 },
  ink: { color: "#101713" },
  muted: { color: "#536158" },
  summary: { color: "#26332B" },
});
