import {
  CalendarDays,
  ChevronRight,
  CloudOff,
  Eye,
  Images,
  MapPin,
  Pencil,
  Ruler,
  Sprout,
  Trash2,
} from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { useLanguage } from "@/hooks/useLanguage";
import type { FarmStatus, FarmSummary } from "../types";
import { hectaresToAcres } from "../utils/geo";
import { cropLabel, districtLabel } from "../utils/labels";

const STATUS_KEY: Record<FarmStatus, string> = {
  draft: "farm.statusDraft",
  active: "farm.statusActive",
  harvested: "farm.statusHarvested",
  archived: "farm.statusArchived",
};
const STATUS_COLOR: Record<FarmStatus, string> = {
  draft: "#607068",
  active: "#176B3A",
  harvested: "#A56800",
  archived: "#315E75",
};

export function FarmCard({
  farm,
  onView,
  onEdit,
  onCalendar,
  onDelete,
}: {
  farm: FarmSummary;
  onView: () => void;
  onEdit: () => void;
  onCalendar: () => void;
  onDelete?: () => void;
}) {
  const { t } = useTranslation();
  const { isTamil } = useLanguage();
  const crop = cropLabel(farm.crop, isTamil);
  const district = districtLabel(farm.district, isTamil);
  const area =
    farm.areaHectares != null
      ? `${hectaresToAcres(farm.areaHectares).toFixed(2)} ${t("farm.acresShort")}`
      : t("farm.notSet");
  const statusColor = STATUS_COLOR[farm.status];

  return (
    <View testID={`farm-card-${farm.id}`} style={styles.card}>
      <Pressable
        onPress={onView}
        accessibilityRole="button"
        accessibilityLabel={farm.name}
        style={({ pressed }) => [styles.main, pressed && styles.pressed]}
      >
        <View style={styles.farmIcon}>
          <Sprout size={28} color="#176B3A" />
        </View>
        <View style={styles.identity}>
          <Text style={styles.name} numberOfLines={2}>
            {farm.name}
          </Text>
          <View style={styles.cropRow}>
            <Sprout size={16} color="#607068" />
            <Text style={styles.crop} numberOfLines={2}>
              {crop ?? t("farm.notSet")}
            </Text>
          </View>
        </View>
        <ChevronRight size={22} color="#607068" />
      </Pressable>
      <View
        style={[
          styles.status,
          {
            borderColor: `${statusColor}55`,
            backgroundColor: `${statusColor}12`,
          },
        ]}
      >
        <View style={[styles.statusDot, { backgroundColor: statusColor }]} />
        <Text style={[styles.statusText, { color: statusColor }]}>
          {t(STATUS_KEY[farm.status])}
        </Text>
      </View>

      <View style={styles.summary}>
        <SummaryItem icon={Ruler} label={t("farm.area")} value={area} />
        <View style={styles.divider} />
        <SummaryItem
          icon={MapPin}
          label={t("farm.location")}
          value={district ?? t("farm.notSet")}
        />
        <View style={styles.divider} />
        <SummaryItem
          icon={Images}
          label={t("farm.photos")}
          value={String(farm.imageCount)}
        />
      </View>
      {farm.syncStatus === "pending" ? (
        <View style={styles.syncRow}>
          <CloudOff size={16} color="#A56800" />
          <Text style={styles.syncText}>{t("farm.pendingSync")}</Text>
        </View>
      ) : null}
      <View style={styles.actions}>
        <FarmAction icon={Eye} label={t("farm.viewDetails")} onPress={onView} />
        <FarmAction
          icon={CalendarDays}
          label={t("farm.calendar")}
          onPress={onCalendar}
        />
        <FarmAction icon={Pencil} label={t("farm.editFarm")} onPress={onEdit} />
        {onDelete ? (
          <FarmAction
            icon={Trash2}
            label={t("farm.deleteFarm")}
            onPress={onDelete}
            danger
          />
        ) : null}
      </View>
    </View>
  );
}

function SummaryItem({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Ruler;
  label: string;
  value: string;
}) {
  return (
    <View style={styles.summaryItem}>
      <Icon size={19} color="#176B3A" />
      <View style={styles.summaryCopy}>
        <Text style={styles.summaryLabel} numberOfLines={1}>
          {label}
        </Text>
        <Text style={styles.summaryValue} numberOfLines={2}>
          {value}
        </Text>
      </View>
    </View>
  );
}

function FarmAction({
  icon: Icon,
  label,
  onPress,
  danger = false,
}: {
  icon: typeof Eye;
  label: string;
  onPress: () => void;
  danger?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={({ pressed }) => [
        styles.action,
        danger && styles.dangerAction,
        pressed && styles.pressed,
      ]}
    >
      <Icon size={19} color={danger ? "#B42318" : "#176B3A"} />
      <Text
        style={[styles.actionLabel, danger && styles.dangerText]}
        numberOfLines={2}
      >
        {label}
      </Text>
      <ChevronRight size={16} color={danger ? "#B42318" : "#607068"} style={styles.actionChevron} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderColor: "#D8D7C9",
    borderRadius: 24,
    padding: 17,
    gap: 14,
    backgroundColor: "#FFFDF8",
    shadowColor: "#173B2B",
    shadowOpacity: 0.08,
    shadowRadius: 9,
    shadowOffset: { width: 0, height: 3 },
    elevation: 2,
  },
  main: { minHeight: 68, flexDirection: "row", alignItems: "center", gap: 12 },
  pressed: { opacity: 0.68 },
  farmIcon: {
    width: 58,
    height: 58,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#C8DCCB",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#EEF6EC",
  },
  identity: { flex: 1, gap: 5 },
  name: { color: "#173B2B", fontSize: 23, lineHeight: 29, fontWeight: "800" },
  cropRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  crop: { flex: 1, color: "#58685F", fontSize: 15, lineHeight: 20 },
  status: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    borderWidth: 1,
    borderRadius: 18,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  statusText: { fontSize: 13, fontWeight: "700" },
  summary: {
    minHeight: 88,
    flexDirection: "row",
    alignItems: "stretch",
    borderWidth: 1,
    borderColor: "#E0E1D8",
    borderRadius: 18,
    backgroundColor: "#F7F7F0",
    paddingVertical: 13,
  },
  summaryItem: {
    flex: 1,
    minWidth: 0,
    alignItems: "center",
    justifyContent: "center",
    gap: 5,
    paddingHorizontal: 6,
  },
  summaryCopy: { alignItems: "center", minWidth: 0 },
  summaryLabel: { color: "#607068", fontSize: 12 },
  summaryValue: {
    color: "#173B2B",
    fontSize: 14,
    lineHeight: 19,
    fontWeight: "700",
    textAlign: "center",
  },
  divider: { width: StyleSheet.hairlineWidth, backgroundColor: "#D8D7C9" },
  syncRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  syncText: { color: "#805800", fontSize: 13 },
  actions: {
    borderTopWidth: 1,
    borderTopColor: "#E4E4DA",
    paddingTop: 12,
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    gap: 9,
  },
  action: {
    minHeight: 48,
    width: "48%",
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    paddingHorizontal: 12,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#D3DDD3",
    backgroundColor: "#F6FAF5",
  },
  actionLabel: {
    flex: 1,
    minWidth: 0,
    color: "#173B2B",
    fontSize: 13,
    lineHeight: 17,
    fontWeight: "700",
  },
  actionChevron: { flexShrink: 0 },
  dangerAction: { borderColor: "#F0C8C4", backgroundColor: "#FFF2F0" },
  dangerText: { color: "#B42318" },
});
