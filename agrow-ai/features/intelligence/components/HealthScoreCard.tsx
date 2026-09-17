import {
  Bug,
  CloudSun,
  FlaskConical,
  Layers3,
  Satellite,
  Sprout,
} from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, useWindowDimensions, View } from "react-native";

import { AgPressable, AgText } from "@/components/ui";

import {
  HEALTH_MODULES,
  MODULE_LABEL_KEY,
  RISK_LABEL_KEY,
  RISK_TONE,
  scoreTone,
} from "../constants";
import type { HealthScores, RiskLevel } from "../types";
import { INTELLIGENCE_COLORS as C } from "../design";

const MODULE_ICONS = {
  disease: Bug,
  nutrient: FlaskConical,
  soil: Layers3,
  satellite: Satellite,
  weather: CloudSun,
  growth: Sprout,
} as const;

const toneColor = (tone: ReturnType<typeof scoreTone>) => {
  if (tone === "success") return C.primary;
  if (tone === "warning") return C.warning;
  if (tone === "danger") return C.danger;
  return C.muted;
};

/**
 * Overall farm-health visualization: the aggregated score, the overall risk, the
 * confidence meter, and the per-module health sub-scores as bars. A module with no
 * data renders as "—" (an empty bar) — never invented.
 */
export function HealthScoreCard({
  health,
  overall,
  risk,
  confidence,
  onModulePress,
}: {
  health: HealthScores | null;
  overall: number | null;
  risk: RiskLevel;
  confidence: number;
  onModulePress?: (module: keyof typeof MODULE_ICONS) => void;
}) {
  const { t } = useTranslation();
  const { width, fontScale } = useWindowDimensions();
  const narrow = width < 390 || fontScale > 1.15;
  const overallTone = scoreTone(overall);

  const moduleScore = (module: string): number | null => {
    if (!health) return null;
    switch (module) {
      case "disease":
        return health.diseaseScore;
      case "nutrient":
        return health.nutrientScore;
      case "soil":
        return health.soilScore;
      case "satellite":
        return health.satelliteScore;
      case "weather":
        return health.weatherScore;
      case "growth":
        return health.growthScore;
      default:
        return null;
    }
  };

  const ringColor = toneColor(overallTone);

  return (
    <View style={styles.card}>
      <View style={[styles.heroRow, { flexDirection: narrow ? "column" : "row" }]}>
        <View
          style={[styles.scoreRing, { borderColor: ringColor }]}
          accessible
          accessibilityLabel={`${t("intelligence.overallHealth")}: ${overall ?? t("intelligence.noData")}`}
        >
          <AgText
            variant="headingXL"
            weight="bold"
            style={{ color: ringColor }}
          >
            {overall == null ? "—" : overall}
          </AgText>
          <AgText variant="caption" style={styles.mutedText}>
            / 100
          </AgText>
        </View>
        <View style={styles.summary}>
          <AgText variant="caption" weight="semibold" style={styles.eyebrow}>
            {t("intelligence.overallHealth")}
          </AgText>
          <View
            style={[styles.riskPill, { backgroundColor: `${ringColor}18` }]}
          >
            <View style={[styles.statusDot, { backgroundColor: ringColor }]} />
            <AgText
              variant="bodySmall"
              weight="semibold"
              style={{ color: ringColor }}
            >
              {overall == null
                ? t("intelligence.insufficientEvidence")
                : t(RISK_LABEL_KEY[risk])}
            </AgText>
          </View>
          <View style={styles.confidenceHeader}>
            <AgText variant="caption" style={styles.mutedText}>
              {t("intelligence.confidence")}
            </AgText>
            <AgText variant="caption" weight="bold" style={styles.inkText}>
              {confidence}%
            </AgText>
          </View>
          <View style={styles.track}>
            <View
              style={[
                styles.fill,
                { width: `${Math.max(0, Math.min(100, confidence))}%` },
              ]}
            />
          </View>
          {confidence < 60 ? (
            <AgText variant="caption" style={styles.mutedText}>
              {t("intelligence.lowConfidenceHint")}
            </AgText>
          ) : null}
        </View>
      </View>

      <View style={styles.divider} />
      <AgText variant="label" weight="semibold" style={styles.inkText}>
        {t("intelligence.moduleScores")}
      </AgText>
      <View style={styles.moduleGrid}>
        {HEALTH_MODULES.map((module) => {
          const score = moduleScore(module);
          const tone = scoreTone(score);
          const pct = score == null ? 0 : Math.max(0, Math.min(100, score));
          const color = toneColor(tone);
          const Icon = MODULE_ICONS[module];
          return (
            <AgPressable
              key={module}
              accessibilityRole="button"
              accessibilityLabel={t(MODULE_LABEL_KEY[module])}
              onPress={() => onModulePress?.(module)}
              style={[
                styles.moduleCard,
                narrow && styles.moduleCardNarrow,
                score == null && styles.moduleCardMissing,
              ]}
            >
              <View style={styles.moduleTop}>
                <View
                  style={[styles.iconBox, { backgroundColor: `${color}14` }]}
                >
                  <Icon size={18} color={color} strokeWidth={2} />
                </View>
                <AgText variant="body" weight="bold" style={{ color }}>
                  {score == null ? "—" : score}
                </AgText>
              </View>
              <AgText
                variant="caption"
                weight="semibold"
                style={styles.inkText}
              >
                {t(MODULE_LABEL_KEY[module])}
              </AgText>
              <AgText variant="caption" style={styles.mutedText}>
                {score == null ? t("intelligence.noData") : `${score}/100`}
              </AgText>
              <View style={styles.moduleTrack}>
                <View
                  style={[
                    styles.moduleFill,
                    { width: `${pct}%`, backgroundColor: color },
                  ]}
                />
              </View>
            </AgPressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: C.surface,
    borderColor: C.border,
    borderWidth: 1,
    borderRadius: 28,
    padding: 18,
    gap: 14,
    shadowColor: "#24452E",
    shadowOpacity: 0.08,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 5 },
    elevation: 3,
  },
  heroRow: { flexDirection: "row", alignItems: "center", gap: 18 },
  scoreRing: {
    width: 128,
    height: 128,
    borderRadius: 64,
    borderWidth: 11,
    backgroundColor: C.white,
    alignItems: "center",
    justifyContent: "center",
  },
  summary: { flex: 1, gap: 7 },
  eyebrow: { color: C.gold, letterSpacing: 0.7, textTransform: "uppercase" },
  riskPill: {
    alignSelf: "flex-start",
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 6,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  confidenceHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 8,
  },
  track: {
    height: 8,
    overflow: "hidden",
    borderRadius: 99,
    backgroundColor: C.border,
  },
  fill: { height: "100%", borderRadius: 99, backgroundColor: C.primary },
  divider: { height: 1, backgroundColor: C.border },
  moduleGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  moduleCard: {
    width: "48%",
    flexGrow: 1,
    minWidth: 132,
    borderRadius: 18,
    padding: 12,
    gap: 5,
    backgroundColor: C.surfaceSoft,
    borderWidth: 1,
    borderColor: "#E1E9DD",
  },
  moduleCardMissing: { backgroundColor: C.white, borderStyle: "dashed" },
  moduleCardNarrow: { width: "100%", minWidth: "100%" },
  moduleTop: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  iconBox: {
    width: 34,
    height: 34,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  moduleTrack: {
    height: 5,
    overflow: "hidden",
    borderRadius: 99,
    backgroundColor: C.border,
    marginTop: 3,
  },
  moduleFill: { height: "100%", borderRadius: 99 },
  inkText: { color: C.ink },
  mutedText: { color: C.muted },
});
