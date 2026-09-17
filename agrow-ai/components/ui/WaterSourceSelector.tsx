import {
  Check,
  ChevronDown,
  CloudRain,
  Droplets,
  Search,
  Waves,
  X,
} from "lucide-react-native";
import { useMemo, useState, type ReactNode } from "react";
import {
  FlatList,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type StyleProp,
  type TextStyle,
  type ViewStyle,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTranslation } from "react-i18next";

import { useLanguage } from "@/hooks/useLanguage";

const BG = "#F7F3E8";
const PAPER = "#FFFDF8";
const SELECTED = "#EAF3E5";
const BORDER = "#D9D6C8";
const TEXT = "#173B2B";
const MUTED = "#5F6F67";
const GREEN = "#176B36";

export interface WaterSourceOption {
  value: string;
  label: string;
  alternateLabel: string;
}

function SourceIcon({
  value,
  color = GREEN,
}: {
  value: string;
  color?: string;
}) {
  if (value === "rain") return <CloudRain size={25} color={color} />;
  if (value === "river" || value === "canal")
    return <Waves size={25} color={color} />;
  return <Droplets size={25} color={color} />;
}

export function filterWaterSources(
  options: WaterSourceOption[],
  query: string,
) {
  const normalized = query.trim().toLocaleLowerCase();
  if (!normalized) return options;
  return options.filter((option) =>
    [option.label, option.alternateLabel, option.value].some((candidate) =>
      candidate.toLocaleLowerCase().includes(normalized),
    ),
  );
}

interface WaterSourceSelectorProps {
  visible: boolean;
  options: WaterSourceOption[];
  selectedValue?: string | null;
  onSelect: (value: string) => void;
  onClose: () => void;
}

export function WaterSourceSelector({
  visible,
  options,
  selectedValue,
  onSelect,
  onClose,
}: WaterSourceSelectorProps) {
  const { t } = useTranslation();
  const { isTamil } = useLanguage();
  const [query, setQuery] = useState("");
  const filtered = useMemo(
    () => filterWaterSources(options, query),
    [options, query],
  );
  const close = () => {
    setQuery("");
    onClose();
  };

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={close}>
      <SafeAreaView style={styles.screen} edges={["top", "bottom"]}>
        <View style={styles.header}>
          <View style={styles.headerCopy}>
            <View style={styles.headerIcon}>
              <Waves size={27} color={GREEN} />
            </View>
            <View style={styles.headerText}>
              <Text style={[styles.title, isTamil && styles.tamilBold]}>
                {t("waterSourceSelector.title")}
              </Text>
              <Text style={[styles.subtitle, isTamil && styles.tamilRegular]}>
                {t("waterSourceSelector.subtitle")}
              </Text>
            </View>
          </View>
          <Pressable
            onPress={close}
            accessibilityRole="button"
            accessibilityLabel={t("waterSourceSelector.close")}
            style={({ pressed }) => [
              styles.closeButton,
              pressed && styles.pressed,
            ]}
          >
            <X size={25} color={TEXT} />
          </Pressable>
        </View>

        <View style={styles.searchField}>
          <Search size={22} color={MUTED} />
          <TextInput
            value={query}
            onChangeText={setQuery}
            placeholder={t("waterSourceSelector.searchPlaceholder")}
            placeholderTextColor={MUTED}
            accessibilityLabel={t("waterSourceSelector.searchPlaceholder")}
            autoCorrect={false}
            autoCapitalize="none"
            returnKeyType="search"
            style={[styles.searchInput, isTamil && styles.tamilRegular]}
          />
        </View>

        <FlatList
          data={filtered}
          keyExtractor={(item) => item.value}
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Search size={34} color={MUTED} />
              <Text style={[styles.emptyText, isTamil && styles.tamilRegular]}>
                {t("waterSourceSelector.noResults")}
              </Text>
            </View>
          }
          renderItem={({ item }) => {
            const selected = item.value === selectedValue;
            return (
              <Pressable
                onPress={() => {
                  onSelect(item.value);
                  close();
                }}
                accessibilityRole="radio"
                accessibilityState={{ selected }}
                accessibilityLabel={item.label}
                style={({ pressed }) => [
                  styles.option,
                  selected && styles.selectedOption,
                  pressed && styles.pressed,
                ]}
              >
                <View
                  style={[styles.optionIcon, selected && styles.selectedIcon]}
                >
                  <SourceIcon value={item.value} />
                </View>
                <View style={styles.optionCopy}>
                  <Text
                    style={[styles.optionTitle, isTamil && styles.tamilBold]}
                  >
                    {item.label}
                  </Text>
                  <Text
                    style={[
                      styles.optionSubtitle,
                      isTamil && styles.tamilRegular,
                    ]}
                    numberOfLines={1}
                  >
                    {item.alternateLabel}
                  </Text>
                </View>
                <View style={[styles.radio, selected && styles.selectedRadio]}>
                  {selected ? (
                    <Check size={18} color="#FFFFFF" strokeWidth={3} />
                  ) : null}
                </View>
              </Pressable>
            );
          }}
        />
      </SafeAreaView>
    </Modal>
  );
}

interface AgWaterSourceDropdownProps {
  label?: string;
  placeholder: string;
  value?: string;
  options: WaterSourceOption[];
  onChange: (value: string) => void;
  leftAccessory?: ReactNode;
  fieldStyle?: ViewStyle;
  textStyle?: StyleProp<TextStyle>;
  labelStyle?: StyleProp<TextStyle>;
}

export function AgWaterSourceDropdown({
  label,
  placeholder,
  value,
  options,
  onChange,
  leftAccessory,
  fieldStyle,
  textStyle,
  labelStyle,
}: AgWaterSourceDropdownProps) {
  const { isTamil } = useLanguage();
  const [visible, setVisible] = useState(false);
  const selected = options.find((option) => option.value === value);

  return (
    <View style={styles.dropdownContainer}>
      {label ? (
        <Text
          style={[styles.label, isTamil && styles.tamilRegular, labelStyle]}
        >
          {label}
        </Text>
      ) : null}
      <Pressable
        onPress={() => setVisible(true)}
        accessibilityRole="button"
        accessibilityState={{ expanded: visible }}
        accessibilityLabel={selected?.label ?? placeholder}
        style={({ pressed }) => [
          styles.dropdown,
          fieldStyle,
          pressed && styles.pressed,
        ]}
      >
        <View style={styles.dropdownContent}>
          {leftAccessory ? (
            <View style={styles.accessory}>{leftAccessory}</View>
          ) : null}
          <Text
            numberOfLines={1}
            style={[
              styles.dropdownText,
              !selected && styles.placeholder,
              isTamil && styles.tamilRegular,
              textStyle,
            ]}
          >
            {selected?.label ?? placeholder}
          </Text>
        </View>
        <ChevronDown size={21} color={MUTED} />
      </Pressable>
      <WaterSourceSelector
        visible={visible}
        options={options}
        selectedValue={value}
        onSelect={onChange}
        onClose={() => setVisible(false)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: BG },
  header: {
    paddingHorizontal: 20,
    paddingTop: 14,
    paddingBottom: 16,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  headerCopy: {
    flex: 1,
    minWidth: 0,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  headerIcon: {
    width: 52,
    height: 52,
    borderRadius: 17,
    backgroundColor: SELECTED,
    alignItems: "center",
    justifyContent: "center",
  },
  headerText: { flex: 1, minWidth: 0 },
  title: {
    color: TEXT,
    fontFamily: "Inter_700Bold",
    fontSize: 27,
    lineHeight: 34,
  },
  subtitle: {
    marginTop: 2,
    color: MUTED,
    fontFamily: "Inter_400Regular",
    fontSize: 14,
    lineHeight: 20,
  },
  closeButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: BORDER,
    backgroundColor: PAPER,
    alignItems: "center",
    justifyContent: "center",
  },
  searchField: {
    minHeight: 60,
    marginHorizontal: 20,
    marginBottom: 16,
    paddingHorizontal: 16,
    borderRadius: 18,
    borderWidth: 1.5,
    borderColor: BORDER,
    backgroundColor: PAPER,
    flexDirection: "row",
    alignItems: "center",
    gap: 11,
  },
  searchInput: {
    flex: 1,
    minHeight: 58,
    paddingVertical: 0,
    color: TEXT,
    fontFamily: "Inter_400Regular",
    fontSize: 16,
  },
  list: { paddingHorizontal: 20, paddingBottom: 28, gap: 10 },
  option: {
    width: "100%",
    alignSelf: "stretch",
    minHeight: 88,
    padding: 14,
    borderRadius: 20,
    borderWidth: 1.5,
    borderColor: BORDER,
    backgroundColor: PAPER,
    flexDirection: "row",
    alignItems: "center",
    gap: 13,
  },
  selectedOption: { borderColor: GREEN, backgroundColor: SELECTED },
  optionIcon: {
    width: 54,
    height: 54,
    borderRadius: 17,
    backgroundColor: SELECTED,
    alignItems: "center",
    justifyContent: "center",
  },
  selectedIcon: { backgroundColor: "#DCECD7" },
  optionCopy: { flex: 1, minWidth: 0 },
  optionTitle: {
    color: TEXT,
    fontFamily: "Inter_600SemiBold",
    fontSize: 19,
    lineHeight: 27,
  },
  optionSubtitle: {
    marginTop: 2,
    color: MUTED,
    fontFamily: "Inter_400Regular",
    fontSize: 14,
    lineHeight: 20,
  },
  radio: {
    flexShrink: 0,
    marginLeft: "auto",
    width: 34,
    height: 34,
    borderRadius: 17,
    borderWidth: 2,
    borderColor: "#9AA59F",
    alignItems: "center",
    justifyContent: "center",
  },
  selectedRadio: { borderColor: GREEN, backgroundColor: GREEN },
  empty: {
    minHeight: 220,
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
  },
  emptyText: { color: MUTED, fontFamily: "Inter_400Regular", fontSize: 16 },
  pressed: { opacity: 0.76 },
  tamilRegular: { fontFamily: "NotoSansTamil_400Regular" },
  tamilBold: { fontFamily: "NotoSansTamil_600SemiBold" },
  dropdownContainer: { width: "100%" },
  label: {
    marginBottom: 8,
    color: MUTED,
    fontFamily: "Inter_500Medium",
    fontSize: 14,
    lineHeight: 20,
  },
  dropdown: {
    width: "100%",
    minHeight: 62,
    paddingHorizontal: 16,
    borderRadius: 17,
    borderWidth: 1.5,
    borderColor: BORDER,
    backgroundColor: PAPER,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  dropdownContent: {
    flex: 1,
    minWidth: 0,
    flexDirection: "row",
    alignItems: "center",
  },
  accessory: { marginRight: 12 },
  dropdownText: {
    flexShrink: 1,
    color: TEXT,
    fontFamily: "Inter_400Regular",
    fontSize: 16,
    lineHeight: 24,
  },
  placeholder: { color: MUTED },
});
