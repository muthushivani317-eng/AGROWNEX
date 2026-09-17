import { useTranslation } from "react-i18next";
import { ScrollView, StyleSheet, TouchableOpacity } from "react-native";

import { AgText } from "@/components/ui";

/** Crop filter chips, shown only when the real calendar spans multiple crops. */
export function CropFilter({
  crops,
  selected,
  onSelect,
}: {
  crops: string[];
  selected: string | null;
  onSelect: (crop: string | null) => void;
}) {
  const { t } = useTranslation();
  if (crops.length <= 1) return null;

  const options: (string | null)[] = [null, ...crops];
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.row}
    >
      {options.map((crop) => {
        const active = selected === crop;
        return (
          <TouchableOpacity
            key={crop ?? "all"}
            onPress={() => onSelect(crop)}
            accessibilityRole="button"
            accessibilityState={{ selected: active }}
            activeOpacity={0.72}
            style={[
              styles.chip,
              {
                backgroundColor: active ? "#DDEDD7" : "#FFFFFF",
                borderColor: active ? "#176B36" : "#D7DDCF",
              },
            ]}
          >
            <AgText
              variant="bodySmall"
              weight={active ? "semibold" : "medium"}
              style={{ color: active ? "#0F5A2D" : "#34443A" }}
            >
              {crop ?? t("calendar.allCrops")}
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
    borderRadius: 20,
    borderWidth: 1,
    justifyContent: "center",
    paddingHorizontal: 14,
  },
});
