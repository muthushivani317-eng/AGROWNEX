import { useTranslation } from "react-i18next";
import { Pressable, ScrollView, StyleSheet } from "react-native";

import { AgText } from "@/components/ui";

import { PRODUCE_VIEWS, VIEW_LABEL_KEY } from "../constants";
import type { ProduceView } from "../types";
import { PRODUCE_COLORS as C } from "../produceTheme";

/** Segmented view switcher: All / Upcoming / History. */
export function ProduceViewTabs({
  active,
  onChange,
}: {
  active: ProduceView;
  onChange: (view: ProduceView) => void;
}) {
  const { t } = useTranslation();
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.content}
      accessibilityRole="tablist"
    >
      {PRODUCE_VIEWS.map((view) => (
        <Pressable
          key={view}
          onPress={() => onChange(view)}
          accessibilityRole="tab"
          accessibilityState={{ selected: active === view }}
          style={[
            styles.tab,
            active === view && styles.activeTab,
          ]}
        >
          <AgText
            weight="semibold"
            style={active === view ? styles.activeText : styles.text}
          >
            {t(VIEW_LABEL_KEY[view])}
          </AgText>
        </Pressable>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { gap: 8, paddingVertical: 4, paddingRight: 8 },
  tab: {
    minHeight: 48,
    paddingHorizontal: 20,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.paper,
    alignItems: "center",
    justifyContent: "center",
  },
  activeTab: { borderColor: C.green, backgroundColor: C.green },
  text: { color: C.ink },
  activeText: { color: C.paper },
});
