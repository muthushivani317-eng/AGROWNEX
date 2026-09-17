import { useTranslation } from "react-i18next";
import { ScrollView, StyleSheet, TouchableOpacity } from "react-native";

import { AgText } from "@/components/ui";

import { CALENDAR_VIEWS, VIEW_LABEL_KEY } from "../constants";
import type { CalendarView } from "../types";

/** Device-safe horizontal segmented control for every implemented calendar view. */
export function ViewTabs({
  active,
  onChange,
}: {
  active: CalendarView;
  onChange: (view: CalendarView) => void;
}) {
  const { t } = useTranslation();

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.row}
    >
      {CALENDAR_VIEWS.map((item) => {
        const selected = active === item;
        return (
          <TouchableOpacity
            key={item}
            testID={`calendar-view-${item}`}
            onPress={() => onChange(item)}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            activeOpacity={0.72}
            style={[
              styles.tab,
              {
                backgroundColor: selected ? "#DDEDD7" : "#FFFFFF",
                borderColor: selected ? "#176B36" : "#CBD4C4",
              },
            ]}
          >
            <AgText
              variant="bodySmall"
              weight={selected ? "semibold" : "medium"}
              style={{
                color: selected ? "#0F5A2D" : "#24412E",
              }}
            >
              {t(VIEW_LABEL_KEY[item])}
            </AgText>
          </TouchableOpacity>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  row: { gap: 8, paddingVertical: 2, paddingRight: 20 },
  tab: {
    minHeight: 48,
    minWidth: 76,
    paddingHorizontal: 16,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
});
