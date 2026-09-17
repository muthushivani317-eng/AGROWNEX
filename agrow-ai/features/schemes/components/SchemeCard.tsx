import { useRouter } from "expo-router";
import {
  Bookmark,
  Building2,
  ChevronRight,
  Landmark,
  ShieldCheck,
} from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { StyleSheet, TouchableOpacity, View } from "react-native";

import { AgText } from "@/components/ui";

import { CATEGORY_LABEL_KEY } from "../constants";
import type { SchemeSummary } from "../types";

const GREEN = "#176B36";
const TEXT = "#101713";
const MUTED = "#536158";

/** Truthful list presentation: engine matches are leads, not official eligibility decisions. */
export function SchemeCard({
  scheme,
  onToggleBookmark,
  busy,
}: {
  scheme: SchemeSummary;
  onToggleBookmark: (scheme: SchemeSummary) => void;
  busy?: boolean;
}) {
  const { t } = useTranslation();
  const router = useRouter();
  const category = t(CATEGORY_LABEL_KEY[scheme.category], {
    defaultValue: scheme.category,
  });
  const department = scheme.departments[0];

  return (
    <TouchableOpacity
      onPress={() => router.push(`/schemes/${scheme.id}`)}
      accessibilityRole="button"
      accessibilityLabel={scheme.title}
      activeOpacity={0.8}
      style={styles.card}
    >
      <View style={styles.badgeRow}>
        <View style={styles.categoryBadge}>
          <AgText variant="caption" weight="semibold" style={styles.greenText}>
            {category}
          </AgText>
        </View>
        {scheme.eligibility && scheme.eligibility.status !== "not_eligible" ? (
          <View style={styles.matchBadge}>
            <ShieldCheck size={15} color={GREEN} />
            <AgText
              variant="caption"
              weight="semibold"
              style={styles.greenText}
            >
              {t("schemes.potentialMatch")}
            </AgText>
          </View>
        ) : null}
      </View>

      <View style={styles.mainRow}>
        <View style={styles.iconTile}>
          <Landmark size={30} color={GREEN} />
        </View>
        <View style={styles.copy}>
          <AgText variant="bodyLarge" weight="bold" style={styles.primaryText}>
            {scheme.title}
          </AgText>
          <AgText
            variant="bodySmall"
            numberOfLines={3}
            style={styles.secondaryText}
          >
            {scheme.description}
          </AgText>
        </View>
        <TouchableOpacity
          onPress={(event) => {
            event.stopPropagation();
            onToggleBookmark(scheme);
          }}
          disabled={busy}
          hitSlop={10}
          accessibilityRole="button"
          accessibilityState={{ selected: scheme.bookmarked, busy }}
          accessibilityLabel={
            scheme.bookmarked
              ? t("schemes.removeBookmark")
              : t("schemes.addBookmark")
          }
          style={styles.bookmark}
          activeOpacity={0.65}
        >
          <Bookmark
            size={24}
            color={scheme.bookmarked ? GREEN : MUTED}
            fill={scheme.bookmarked ? GREEN : "transparent"}
          />
        </TouchableOpacity>
      </View>

      <View style={styles.footer}>
        <View style={styles.department}>
          <Building2 size={16} color={MUTED} />
          <AgText
            variant="caption"
            numberOfLines={2}
            style={styles.secondaryText}
          >
            {department ?? t("schemes.departmentNotProvided")}
          </AgText>
        </View>
        <View style={styles.verifyAction}>
          <AgText
            variant="caption"
            weight="semibold"
            style={styles.secondaryText}
          >
            {scheme.officialUrl
              ? t("schemes.verifyOfficialSource")
              : t("schemes.verifyAgainstOfficialSource")}
          </AgText>
          <ChevronRight size={18} color={GREEN} />
        </View>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: 18,
    padding: 18,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#D9D6C8",
    backgroundColor: "#FFFFFF",
  },
  badgeRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    gap: 10,
  },
  categoryBadge: {
    paddingHorizontal: 11,
    paddingVertical: 6,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#BDD2B8",
    backgroundColor: "#EAF3E5",
  },
  matchBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: 11,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: "#EAF3E5",
  },
  greenText: { color: GREEN },
  primaryText: { color: TEXT },
  secondaryText: { color: MUTED },
  mainRow: { flexDirection: "row", alignItems: "flex-start", gap: 14 },
  iconTile: {
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "#BDD2B8",
    backgroundColor: "#EAF3E5",
  },
  copy: { flex: 1, gap: 7 },
  bookmark: {
    width: 40,
    minHeight: 44,
    alignItems: "center",
    justifyContent: "center",
  },
  footer: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: "#E4E0D4",
  },
  department: {
    minWidth: 130,
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  verifyAction: {
    maxWidth: "55%",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "flex-end",
    gap: 5,
  },
});
