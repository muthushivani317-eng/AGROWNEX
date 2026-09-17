import { ScrollView, StyleSheet, TouchableOpacity } from "react-native";

import { AgText } from "@/components/ui";
import type { FarmSummary } from "@/features/farm";

/** Horizontal farm switcher backed by the existing selected-farm state. */
export function FarmSwitcher({
  farms,
  selectedId,
  onSelect,
  light: _light = false,
}: {
  farms: FarmSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  light?: boolean;
}) {
  if (farms.length <= 1) return null;

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.row}
    >
      {farms.map((farm) => {
        const selected = selectedId === farm.id;
        return (
          <TouchableOpacity
            key={farm.id}
            onPress={() => onSelect(farm.id)}
            accessibilityRole="button"
            accessibilityState={{ selected }}
            activeOpacity={0.72}
            style={[
              styles.chip,
              {
                backgroundColor: selected ? "#DDEDD7" : "#FFFFFF",
                borderColor: selected ? "#176B36" : "#D7DDCF",
              },
            ]}
          >
            <AgText
              variant="bodySmall"
              weight={selected ? "semibold" : "medium"}
              style={{
                color: selected ? "#0F5A2D" : "#34443A",
              }}
            >
              {farm.name}
            </AgText>
          </TouchableOpacity>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  row: { gap: 9, paddingRight: 20 },
  chip: {
    minHeight: 48,
    borderRadius: 21,
    borderWidth: 1,
    justifyContent: "center",
    paddingHorizontal: 15,
  },
});
