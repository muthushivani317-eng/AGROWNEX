import { Search, X } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { Pressable, ScrollView, View } from "react-native";

import { AgText, AgInput, AgPressable } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import { CATEGORY_LABEL_KEY, FILTER_CATEGORIES } from "../constants";
import type { SchemeCategory } from "../types";

/**
 * Search box + category filter chips for the "All schemes" view
 * (docs: Government Schemes → Search, Filters).
 */
export function SchemeFilterBar({
  search,
  onSearchChange,
  category,
  onCategoryChange,
}: {
  search: string;
  onSearchChange: (value: string) => void;
  category: SchemeCategory | null;
  onCategoryChange: (category: SchemeCategory | null) => void;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();

  return (
    <View style={{ gap: 8 }}>
      <AgInput
        value={search}
        onChangeText={onSearchChange}
        placeholder={t("schemes.searchPlaceholder")}
        accessibilityLabel={t("schemes.searchPlaceholder")}
        autoCapitalize="none"
        fieldStyle={{ backgroundColor: '#FFFFFF', borderColor: '#D9D6C8' }}
        fieldBackgroundColor="#FFFFFF"
        fieldBorderColor="#D9D6C8"
        focusBorderColor="#176B36"
        style={{ color: '#101713', backgroundColor: '#FFFFFF' }}
        placeholderTextColor="#536158"
        leftAccessory={<Search size={18} color={colors.textMuted} />}
        rightAccessory={
          search.length > 0 ? (
            <AgPressable
              onPress={() => onSearchChange("")}
              accessibilityRole="button"
              accessibilityLabel={t("common.clear")}
            >
              <X size={18} color={colors.textMuted} />
            </AgPressable>
          ) : undefined
        }
      />
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{ gap: 8, paddingVertical: 4 }}
      >
        <AgChip
          label={t("schemes.filterAll")}
          selected={category === null}
          onPress={() => onCategoryChange(null)}
          light
        />
        {FILTER_CATEGORIES.map((cat) => (
          <AgChip
            key={cat}
            label={t(CATEGORY_LABEL_KEY[cat])}
            selected={category === cat}
            onPress={() => onCategoryChange(category === cat ? null : cat)}
            light
          />
        ))}
      </ScrollView>
    </View>
  );
}

function AgChip({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void; light?: boolean }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityState={{ selected }}
      style={{ minHeight: 44, justifyContent: 'center', paddingHorizontal: 14, borderWidth: 1, borderRadius: 12,
        borderColor: selected ? '#176B36' : '#D9D6C8', backgroundColor: selected ? '#EAF3E5' : '#FFFFFF' }}>
      <AgText style={{ color: '#173B2B' }}>{label}</AgText>
    </Pressable>
  );
}
