import { CalendarRange, Sparkles } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";

import { IMPORTANCE_LABEL_KEY, SEASON_LABEL_KEY } from "../constants";
import type { MemorySummary } from "../types";

const C = {
  surface: "#FFFDF7",
  text: "#173F30",
  muted: "#5F6D65",
  green: "#17633B",
  soft: "#E8F3E5",
  border: "#D8D2C2",
  amber: "#A96705",
  amberSoft: "#FFF4D8",
} as const;

export function MemorySummaryCard({ summary }: { summary: MemorySummary }) {
  const { t } = useTranslation();
  const heading =
    summary.periodType === "season" && summary.season
      ? `${t(SEASON_LABEL_KEY[summary.season] ?? summary.season)} ${summary.year}`
      : `${summary.year}`;

  return (
    <View style={styles.card}>
      <View style={styles.icon}>
        <Sparkles size={24} color={C.green} />
      </View>
      <View style={styles.copy}>
        <View style={styles.headingRow}>
          <AgText variant="headingS" weight="bold" style={styles.heading}>
            {heading}
          </AgText>
          <View style={styles.badge}>
            <AgText style={styles.badgeText} weight="semibold">
              {t(IMPORTANCE_LABEL_KEY[summary.importance])}
            </AgText>
          </View>
        </View>
        <AgText style={styles.line}>
          {t("memory.summaryLine", {
            count: summary.eventCount,
            crop: summary.crop ?? t("memory.cropUnknown"),
          })}
        </AgText>
        {typeof summary.params?.disease_count === "number" &&
        summary.params.disease_count > 0 ? (
          <View style={styles.extraRow}>
            <CalendarRange size={16} color={C.muted} />
            <AgText style={styles.extra}>
              {t("memory.summaryDisease", {
                count: summary.params.disease_count as number,
              })}
            </AgText>
          </View>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 14,
    padding: 18,
    borderRadius: 22,
    backgroundColor: C.surface,
    borderWidth: 1,
    borderColor: C.border,
  },
  icon: {
    width: 50,
    height: 50,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: C.soft,
  },
  copy: { flex: 1, gap: 8 },
  headingRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 8,
  },
  heading: { flex: 1, color: C.text },
  badge: {
    maxWidth: "46%",
    borderRadius: 14,
    paddingHorizontal: 10,
    paddingVertical: 5,
    backgroundColor: C.amberSoft,
  },
  badgeText: { color: C.amber, fontSize: 12 },
  line: { color: C.muted, fontSize: 15, lineHeight: 22 },
  extraRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  extra: { flex: 1, color: C.muted, fontSize: 13 },
});
