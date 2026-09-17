import { useTranslation } from "react-i18next";
import { StyleSheet, TouchableOpacity, View } from "react-native";

import { AgText } from "@/components/ui";

import { SCHEME_TABS, TAB_LABEL_KEY } from "../constants";
import type { SchemeTab } from "../types";

const GREEN = "#176B36";
const TEXT = "#101713";

/** Retains the four real query-backed scheme views in a compact tab strip. */
export function SchemeViewTabs({
  active,
  onChange,
}: {
  active: SchemeTab;
  onChange: (tab: SchemeTab) => void;
}) {
  const { t } = useTranslation();
  return (
    <View style={styles.content} accessibilityRole="tablist">
      {SCHEME_TABS.map((tab) => {
        const selected = active === tab;
        return (
          <TouchableOpacity
            key={tab}
            onPress={() => onChange(tab)}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            activeOpacity={0.72}
            style={[styles.tab, selected && styles.tabSelected]}
          >
            <AgText
              variant="bodySmall"
              weight={selected ? "semibold" : "medium"}
              style={styles.tabText}
            >
              {t(TAB_LABEL_KEY[tab])}
            </AgText>
            <View
              style={[styles.indicator, selected && styles.indicatorActive]}
            />
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  content: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  tab: {
    minHeight: 52,
    width: "48%",
    flexGrow: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#D9D6C8",
    backgroundColor: "#FFFFFF",
    gap: 5,
  },
  tabSelected: { borderColor: GREEN, backgroundColor: "#EAF3E5" },
  indicator: {
    width: 28,
    height: 3,
    borderRadius: 3,
    backgroundColor: "transparent",
  },
  indicatorActive: { backgroundColor: GREEN },
  tabText: { color: TEXT, textAlign: "center" },
});
