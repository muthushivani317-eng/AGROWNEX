import dayjs from "dayjs";
import {
  CalendarDays,
  Check,
  ChevronDown,
  CloudRain,
  Droplets,
  Leaf,
  RotateCcw,
  Sprout,
} from "lucide-react-native";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { StyleSheet, TouchableOpacity, View } from "react-native";

import { AgText } from "@/components/ui";

import {
  ADVISORY_LABEL_KEY,
  PRIORITY_LABEL_KEY,
  STATUS_LABEL_KEY,
  activityDescKey,
  activityTitleKey,
} from "../constants";
import type { CalendarEvent } from "../types";

const PALETTE = {
  card: "#FFFFFF",
  ink: "#173B25",
  body: "#34443A",
  muted: "#667168",
  green: "#176B36",
  border: "#DDD7C8",
  icon: "#EDF4E8",
  gold: "#B86B16",
  goldPale: "#FFF1CE",
  red: "#C44132",
  blue: "#2367A8",
} as const;

function activityIcon(event: CalendarEvent) {
  const value = `${event.code} ${event.activityType}`.toLowerCase();
  if (value.includes("irrig")) return Droplets;
  if (value.includes("weed") || value.includes("harvest")) return Leaf;
  if (value.includes("sow") || value.includes("seed")) return Sprout;
  return CalendarDays;
}

/** Compact expandable activity card backed only by the real event model. */
export function TaskCard({
  event,
  onToggle,
  busy,
}: {
  event: CalendarEvent;
  onToggle: (event: CalendarEvent) => void;
  busy?: boolean;
}) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const Icon = activityIcon(event);

  const titleKey = event.title.startsWith("calendar.verified.")
    ? event.title
    : activityTitleKey(event.code);
  const descriptionKey = event.description.startsWith("calendar.verified.")
    ? event.description
    : activityDescKey(event.code);
  const title = t(titleKey, { defaultValue: event.title });
  const description = t(descriptionKey, { defaultValue: event.description });
  const isDone = event.status === "done";
  const advisoryKey = ADVISORY_LABEL_KEY[event.weatherAdvisory];
  const priorityColor =
    event.priority === "high"
      ? PALETTE.red
      : event.priority === "medium"
        ? PALETTE.gold
        : PALETTE.green;
  const statusColor = isDone
    ? PALETTE.green
    : event.status === "skipped"
      ? PALETTE.muted
      : PALETTE.blue;

  return (
    <View
      testID={`calendar-task-${event.id}`}
      style={[
        styles.card,
        {
          backgroundColor: PALETTE.card,
          borderColor: PALETTE.border,
          opacity: isDone ? 0.82 : 1,
        },
      ]}
    >
      <TouchableOpacity
        onPress={() => setExpanded((value) => !value)}
        accessibilityRole="button"
        accessibilityLabel={title}
        accessibilityHint={t("calendar.detailsHint")}
        accessibilityState={{ expanded }}
        activeOpacity={0.76}
        style={styles.summary}
      >
        <View
          style={[
            styles.iconTile,
            {
              backgroundColor: PALETTE.icon,
              borderColor: "#D9E7D3",
            },
          ]}
        >
          <Icon size={25} color={PALETTE.green} />
        </View>

        <View style={styles.copy}>
          <View style={styles.titleLine}>
            <AgText
              variant="bodyLarge"
              weight="semibold"
              numberOfLines={expanded ? undefined : 2}
              style={[styles.titleText, isDone ? styles.doneTitle : undefined]}
            >
              {title}
            </AgText>
            <View
              style={[
                styles.statusBadge,
                {
                  backgroundColor: `${statusColor}12`,
                  borderColor: `${statusColor}35`,
                },
              ]}
            >
              <AgText
                variant="caption"
                weight="semibold"
                style={{ color: statusColor }}
              >
                {t(STATUS_LABEL_KEY[event.status])}
              </AgText>
            </View>
          </View>
          <View style={styles.metaRow}>
            <CalendarDays size={15} color={PALETTE.muted} />
            <AgText variant="bodySmall" style={styles.bodyText}>
              {dayjs(event.scheduledDate).format("ddd, DD MMM YYYY")}
            </AgText>
          </View>
          <View style={styles.metaRow}>
            <View
              style={[styles.priorityDot, { backgroundColor: priorityColor }]}
            />
            <AgText variant="bodySmall" style={{ color: priorityColor }}>
              {t(PRIORITY_LABEL_KEY[event.priority])}{" "}
              {t("calendar.prioritySuffix")}
            </AgText>
          </View>
          {advisoryKey ? (
            <View style={styles.metaRow}>
              <CloudRain size={15} color={PALETTE.gold} />
              <AgText variant="bodySmall" style={{ color: PALETTE.gold }}>
                {t(advisoryKey)}
              </AgText>
            </View>
          ) : null}
        </View>

        <ChevronDown
          size={21}
          color={PALETTE.muted}
          style={{ transform: [{ rotate: expanded ? "180deg" : "0deg" }] }}
        />
      </TouchableOpacity>

      {expanded ? (
        <View style={[styles.details, { borderTopColor: PALETTE.border }]}>
          {description ? (
            <AgText variant="bodySmall" style={styles.bodyText}>
              {description}
            </AgText>
          ) : null}
          {event.registryVerificationStatus === "SOURCED_PUBLIC_REFERENCE" ? (
            <AgText
              variant="caption"
              style={[styles.provenanceNotice, { color: PALETTE.gold }]}
            >
              {t("calendar.sourcedNotReviewedNotice")}
            </AgText>
          ) : null}
          <AgText
            variant="caption"
            style={[styles.safetyCopy, styles.mutedText]}
          >
            {t("calendar.officialGuidance")}
          </AgText>
          <TouchableOpacity
            onPress={() => onToggle(event)}
            disabled={busy}
            accessibilityRole="button"
            accessibilityState={{ checked: isDone, busy, disabled: busy }}
            accessibilityLabel={
              isDone ? t("calendar.markPending") : t("calendar.markDone")
            }
            activeOpacity={0.72}
            style={[
              styles.action,
              {
                backgroundColor: isDone ? "#F1F2EE" : "#F6FBF5",
                borderColor: isDone ? PALETTE.muted : PALETTE.green,
                opacity: busy ? 0.55 : 1,
              },
            ]}
          >
            {isDone ? (
              <RotateCcw size={17} color={PALETTE.ink} />
            ) : (
              <Check size={17} color={PALETTE.green} />
            )}
            <AgText
              variant="bodySmall"
              weight="semibold"
              style={styles.titleText}
            >
              {isDone ? t("calendar.markPending") : t("calendar.markDone")}
            </AgText>
          </TouchableOpacity>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, borderRadius: 12, padding: 12 },
  summary: {
    minHeight: 80,
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
  },
  iconTile: {
    width: 48,
    height: 48,
    borderRadius: 24,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  copy: { flex: 1, gap: 5 },
  titleLine: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    gap: 8,
  },
  statusBadge: {
    borderWidth: 1,
    borderRadius: 14,
    paddingHorizontal: 9,
    paddingVertical: 3,
  },
  metaRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  priorityDot: { width: 7, height: 7, borderRadius: 4 },
  doneTitle: { textDecorationLine: "line-through" },
  titleText: { color: PALETTE.ink },
  bodyText: { color: PALETTE.body },
  mutedText: { color: PALETTE.muted },
  details: {
    marginTop: 14,
    paddingTop: 14,
    borderTopWidth: StyleSheet.hairlineWidth,
    gap: 10,
  },
  safetyCopy: { fontStyle: "italic" },
  provenanceNotice: { fontStyle: "italic" },
  action: {
    minHeight: 44,
    alignSelf: "stretch",
    justifyContent: "center",
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    borderRadius: 8,
    borderWidth: 1,
    paddingHorizontal: 16,
    paddingVertical: 9,
  },
});
