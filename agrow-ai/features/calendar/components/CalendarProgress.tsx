import { CalendarCheck, CalendarClock, CircleAlert } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, View } from "react-native";

import { AgText } from "@/components/ui";

import type { CalendarSummary } from "../types";

const GREEN = "#0F5A2D";
const LIGHT_GREEN = "#82C95C";
const GOLD = "#FFC83D";
const RED = "#F0644B";

/** Real provider summary presented as the approved compact season progress card. */
export function CalendarProgress({ summary }: { summary: CalendarSummary }) {
  const { t } = useTranslation();
  const total = Math.max(summary.total, 0);
  const completedPercent =
    total > 0
      ? Math.min(100, Math.round((summary.completed / total) * 100))
      : 0;
  const stats = [
    {
      key: "done",
      label: t("calendar.statDone"),
      value: summary.completed,
      color: LIGHT_GREEN,
      icon: CalendarCheck,
    },
    {
      key: "pending",
      label: t("calendar.statPending"),
      value: summary.pending,
      color: GOLD,
      icon: CalendarClock,
    },
    {
      key: "missed",
      label: t("calendar.statMissed"),
      value: summary.missed,
      color: RED,
      icon: CircleAlert,
    },
  ];

  return (
    <View testID="calendar-progress" style={styles.card}>
      <View style={styles.titleRow}>
        <AgText variant="body" weight="semibold" style={styles.whiteText}>
          {t("calendar.progressTitle")}
        </AgText>
        <View style={styles.totalBadge}>
          <AgText variant="caption" weight="semibold" style={styles.whiteText}>
            {summary.total}
          </AgText>
          <AgText variant="caption" style={styles.statLabel}>
            {t("calendar.statTotal")}
          </AgText>
        </View>
      </View>
      <View style={styles.progressHeading}>
        <AgText variant="headingXL" weight="bold" style={styles.whiteText}>
          {completedPercent}%
        </AgText>
        <AgText variant="headingS" weight="semibold" style={styles.whiteText}>
          {t("calendar.complete")}
        </AgText>
      </View>
      <View
        style={styles.track}
        accessibilityRole="progressbar"
        accessibilityValue={{ now: summary.completed, min: 0, max: total }}
      >
        <View style={[styles.fill, { width: `${completedPercent}%` }]} />
      </View>
      <View style={styles.statsRow}>
        {stats.map(({ key, label, value, color, icon: Icon }) => (
          <View key={key} style={styles.stat}>
            <Icon size={25} color={color} />
            <View style={styles.statCopy}>
              <AgText variant="headingS" weight="bold" style={styles.whiteText}>
                {value}
              </AgText>
              <AgText
                variant="caption"
                style={styles.statLabel}
                numberOfLines={2}
              >
                {label}
              </AgText>
            </View>
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: GREEN, borderRadius: 14, padding: 16, gap: 9 },
  whiteText: { color: "#FFFFFF" },
  titleRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  totalBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    borderRadius: 12,
    backgroundColor: "#FFFFFF1A",
    paddingHorizontal: 9,
    paddingVertical: 4,
  },
  progressHeading: { flexDirection: "row", alignItems: "baseline", gap: 8 },
  track: {
    height: 10,
    borderRadius: 5,
    overflow: "hidden",
    backgroundColor: "#F8FBF4",
  },
  fill: { height: "100%", borderRadius: 5, backgroundColor: LIGHT_GREEN },
  statsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 8,
    marginTop: 4,
  },
  stat: {
    minWidth: 0,
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
  },
  statCopy: { minWidth: 0 },
  statLabel: { color: "#F1F5EF" },
});
