import { CheckCircle2 } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgBadge, AgCard, AgPressable, AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import {
  MODULE_LABEL_KEY,
  PRIORITY_LABEL_KEY,
  PRIORITY_TONE,
} from "../constants";
import type { Recommendation } from "../types";
import { INTELLIGENCE_COLORS as C } from "../design";

const DOT_COLOR: Record<
  "high" | "medium" | "low",
  "danger" | "warning" | "muted"
> = {
  high: "danger",
  medium: "warning",
  low: "muted",
};

/**
 * The prioritized recommendations rendered as a vertical timeline (highest priority
 * first — the order the farmer should act). Every recommendation is a generic
 * localization code; none is invented when the evidence is absent.
 */
export function RecommendationTimeline({
  recommendations,
  onRecommendationPress,
}: {
  recommendations: Recommendation[];
  onRecommendationPress?: (recommendation: Recommendation) => void;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  if (recommendations.length === 0) return null;

  const dotHex = (p: Recommendation["priority"]) => {
    const tone = DOT_COLOR[p];
    if (tone === "danger") return colors.danger;
    if (tone === "warning") return colors.warning;
    return C.muted;
  };

  return (
    <View style={styles.section}>
      <View style={styles.heading}>
        <View style={styles.headingIcon}>
          <CheckCircle2 size={18} color={C.primary} />
        </View>
        <AgText variant="headingS" weight="bold" style={styles.ink}>
          {t("intelligence.recommendations")}
        </AgText>
      </View>
      <AgCard style={styles.card}>
        {recommendations.map((rec, index) => {
          const last = index === recommendations.length - 1;
          return (
            <AgPressable
              key={rec.code}
              className="flex-row gap-3"
              accessibilityRole="button"
              onPress={() => onRecommendationPress?.(rec)}
            >
              {/* Timeline rail */}
              <View className="items-center">
                <View
                  className="mt-1.5 h-3 w-3 rounded-full"
                  style={{ backgroundColor: dotHex(rec.priority) }}
                />
                {!last ? <View className="w-0.5 flex-1 bg-border" /> : null}
              </View>
              <View className={`flex-1 ${last ? "pb-1" : "pb-4"}`}>
                <View className="flex-row items-start justify-between gap-2">
                  <AgText
                    variant="bodySmall"
                    weight="semibold"
                    className="flex-1"
                    style={styles.ink}
                  >
                    {t(`${rec.code}.title`, {
                      defaultValue: t("intelligence.recFallback"),
                    })}
                  </AgText>
                  <AgBadge
                    label={t(PRIORITY_LABEL_KEY[rec.priority])}
                    tone={PRIORITY_TONE[rec.priority]}
                    light
                  />
                </View>
                <AgText
                  variant="caption"
                  className="mt-0.5"
                  style={styles.muted}
                >
                  {t(`${rec.code}.message`, { defaultValue: "" })}
                </AgText>
                {rec.modules.length > 0 ? (
                  <View className="mt-0.5 flex-row flex-wrap gap-1">
                    {rec.modules.map((m) => (
                      <AgText key={m} variant="caption" color="muted">
                        #{t(MODULE_LABEL_KEY[m] ?? m)}
                      </AgText>
                    ))}
                  </View>
                ) : null}
              </View>
            </AgPressable>
          );
        })}
      </AgCard>
    </View>
  );
}

const styles = StyleSheet.create({
  section: { gap: 10 },
  heading: { flexDirection: "row", alignItems: "center", gap: 10 },
  headingIcon: {
    width: 36,
    height: 36,
    borderRadius: 12,
    backgroundColor: C.surfaceSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  card: {
    backgroundColor: C.surface,
    borderColor: C.border,
    paddingVertical: 14,
  },
  ink: { color: C.ink },
  muted: { color: C.muted },
});
