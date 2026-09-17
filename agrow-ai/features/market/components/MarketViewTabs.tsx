import { useTranslation } from "react-i18next";
import { ScrollView, StyleSheet, Text, TouchableOpacity } from "react-native";

import { MARKET_VIEWS, VIEW_LABEL_KEY } from "../constants";
import type { MarketView } from "../types";

/** Segmented view switcher: All / Today / Nearby / Favourites. */
export function MarketViewTabs({
  active,
  onChange,
}: {
  active: MarketView;
  onChange: (view: MarketView) => void;
}) {
  const { t } = useTranslation();
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.content}
      accessibilityRole="tablist"
    >
      {MARKET_VIEWS.map((view) => {
        const selected = active === view;
        return (
          <TouchableOpacity
            key={view}
            onPress={() => onChange(view)}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            style={[styles.tab, selected && styles.tabSelected]}
          >
            <Text style={[styles.label, selected && styles.labelSelected]}>
              {t(VIEW_LABEL_KEY[view])}
            </Text>
          </TouchableOpacity>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { paddingVertical: 4, paddingRight: 12, gap: 8 },
  tab: {
    minHeight: 44,
    justifyContent: "center",
    paddingHorizontal: 18,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: "#CBD5CB",
    backgroundColor: "#FFFDF8",
  },
  tabSelected: { backgroundColor: "#176B3A", borderColor: "#176B3A" },
  label: { color: "#27483A", fontSize: 15, fontWeight: "600" },
  labelSelected: { color: "#FFFFFF" },
});
