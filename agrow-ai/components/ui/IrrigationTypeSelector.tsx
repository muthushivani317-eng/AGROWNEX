import { Check, ChevronDown, Droplets, Search, X } from 'lucide-react-native';
import { useMemo, useState, type ReactNode } from 'react';
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
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useTranslation } from 'react-i18next';

import { useLanguage } from '@/hooks/useLanguage';

const BG = '#0B0E0C';
const SURFACE = '#151917';
const SELECTED_SURFACE = '#102016';
const BORDER = '#303633';
const TEXT = '#F4F7F4';
const MUTED = '#AEB5B0';
const GREEN = '#55C95A';

export interface IrrigationTypeOption {
  value: string;
  label: string;
  subtitle: string;
  alternateLabel: string;
}

export function normalizeIrrigationSearch(value: string): string {
  return value.trim().replace(/\s+/g, ' ').toLocaleLowerCase();
}

export function filterIrrigationTypes(
  options: IrrigationTypeOption[],
  query: string,
): IrrigationTypeOption[] {
  const normalized = normalizeIrrigationSearch(query);
  if (!normalized) return options;
  return options.filter((option) =>
    [option.label, option.alternateLabel, option.value]
      .some((candidate) => normalizeIrrigationSearch(candidate).includes(normalized)),
  );
}

export interface IrrigationTypeSelectorProps {
  visible: boolean;
  options: IrrigationTypeOption[];
  selectedValue?: string | null;
  onSelect: (value: string) => void;
  onClose: () => void;
}

export function IrrigationTypeSelector({
  visible,
  options,
  selectedValue,
  onSelect,
  onClose,
}: IrrigationTypeSelectorProps) {
  const { t } = useTranslation();
  const { isTamil } = useLanguage();
  const [query, setQuery] = useState('');
  const filtered = useMemo(() => filterIrrigationTypes(options, query), [options, query]);

  const close = () => {
    setQuery('');
    onClose();
  };

  return (
    <Modal
      visible={visible}
      transparent
      statusBarTranslucent
      animationType="slide"
      onRequestClose={close}
    >
      <View style={styles.backdrop}>
        <SafeAreaView style={styles.sheet} edges={['top', 'bottom']}>
          <View style={styles.dragHandle} />
          <View style={styles.header}>
            <Text style={[styles.title, isTamil && styles.tamilBold]}>
              {t('irrigationSelector.title')}
            </Text>
            <Pressable
              testID="irrigation-selector-close"
              onPress={close}
              accessibilityRole="button"
              accessibilityLabel={t('irrigationSelector.close')}
              style={styles.closeButton}
            >
              <X size={28} color={TEXT} />
            </Pressable>
          </View>

          <View style={styles.searchField}>
            <Search size={24} color={MUTED} />
            <TextInput
              testID="irrigation-search-input"
              value={query}
              onChangeText={setQuery}
              placeholder={t('irrigationSelector.searchPlaceholder')}
              placeholderTextColor={MUTED}
              accessibilityLabel={t('irrigationSelector.searchPlaceholder')}
              autoCorrect={false}
              autoCapitalize="none"
              returnKeyType="search"
              keyboardAppearance="dark"
              style={[styles.searchInput, isTamil && styles.tamilRegular]}
            />
          </View>

          <FlatList
            testID="irrigation-type-list"
            data={filtered}
            keyExtractor={(item) => item.value}
            keyboardShouldPersistTaps="handled"
            keyboardDismissMode="on-drag"
            initialNumToRender={7}
            contentContainerStyle={styles.listContent}
            ListEmptyComponent={
              <View style={styles.emptyState}>
                <Search size={34} color={MUTED} />
                <Text style={[styles.emptyText, isTamil && styles.tamilRegular]}>
                  {t('irrigationSelector.noResults')}
                </Text>
              </View>
            }
            renderItem={({ item }) => {
              const selected = item.value === selectedValue;
              return (
                <Pressable
                  testID={`irrigation-option-${item.value}`}
                  onPress={() => {
                    onSelect(item.value);
                    close();
                  }}
                  accessibilityRole="radio"
                  accessibilityState={{ selected }}
                  accessibilityLabel={item.label}
                  style={[styles.row, selected && styles.selectedRow]}
                >
                  <View style={[styles.iconTile, selected && styles.selectedIcon]}>
                    <Droplets size={27} color={GREEN} />
                  </View>
                  <View style={styles.rowCopy}>
                    <Text style={[styles.rowTitle, isTamil && styles.tamilBold]} numberOfLines={2}>
                      {item.label}
                    </Text>
                    <Text style={[styles.rowSubtitle, isTamil && styles.tamilRegular]} numberOfLines={2}>
                      {item.subtitle}
                    </Text>
                  </View>
                  <View style={[styles.radio, selected && styles.radioSelected]}>
                    {selected ? <Check size={18} strokeWidth={3} color={BG} /> : null}
                  </View>
                </Pressable>
              );
            }}
          />
        </SafeAreaView>
      </View>
    </Modal>
  );
}

interface AgIrrigationTypeDropdownProps {
  label?: string;
  placeholder: string;
  value?: string;
  options: IrrigationTypeOption[];
  onChange: (value: string) => void;
  leftAccessory?: ReactNode;
  fieldStyle?: ViewStyle;
  textStyle?: StyleProp<TextStyle>;
  labelStyle?: StyleProp<TextStyle>;
}

export function AgIrrigationTypeDropdown({
  label,
  placeholder,
  value,
  options,
  onChange,
  leftAccessory,
  fieldStyle,
  textStyle,
  labelStyle,
}: AgIrrigationTypeDropdownProps) {
  const { isTamil } = useLanguage();
  const [visible, setVisible] = useState(false);
  const selected = options.find((option) => option.value === value);

  return (
    <View style={styles.dropdownContainer}>
      {label ? <Text style={[styles.label, isTamil && styles.tamilRegular, labelStyle]}>{label}</Text> : null}
      <Pressable
        testID="irrigation-type-dropdown"
        onPress={() => setVisible(true)}
        accessibilityRole="button"
        accessibilityState={{ expanded: visible }}
        accessibilityLabel={selected?.label ?? placeholder}
        style={[styles.dropdownField, fieldStyle]}
      >
        <View style={styles.dropdownContent}>
          {leftAccessory ? <View pointerEvents="none" style={styles.accessory}>{leftAccessory}</View> : null}
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

      <IrrigationTypeSelector
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
  backdrop: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.72)' },
  sheet: { flex: 1, marginTop: 20, overflow: 'hidden', borderTopLeftRadius: 30, borderTopRightRadius: 30, backgroundColor: BG },
  dragHandle: { width: 68, height: 5, marginTop: 12, marginBottom: 16, borderRadius: 3, alignSelf: 'center', backgroundColor: '#D9DDDA' },
  header: { minHeight: 62, paddingHorizontal: 22, paddingBottom: 16, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  title: { color: TEXT, fontFamily: 'Inter_700Bold', fontSize: 30, lineHeight: 38 },
  closeButton: { width: 52, height: 52, borderRadius: 26, borderWidth: 1, borderColor: BORDER, backgroundColor: '#202321', alignItems: 'center', justifyContent: 'center' },
  searchField: { minHeight: 58, marginHorizontal: 22, marginBottom: 16, borderRadius: 17, borderWidth: 1.5, borderColor: BORDER, backgroundColor: SURFACE, paddingHorizontal: 16, flexDirection: 'row', alignItems: 'center', gap: 11 },
  searchInput: { flex: 1, minHeight: 54, paddingVertical: 0, color: TEXT, backgroundColor: SURFACE, fontFamily: 'Inter_400Regular', fontSize: 16 },
  listContent: { paddingHorizontal: 22, paddingBottom: 26, gap: 10 },
  row: { width: '100%', minHeight: 96, paddingHorizontal: 16, paddingVertical: 13, borderRadius: 20, borderWidth: 1.5, borderColor: BORDER, backgroundColor: SURFACE, flexDirection: 'row', alignItems: 'center', gap: 14 },
  selectedRow: { borderColor: GREEN, backgroundColor: SELECTED_SURFACE },
  iconTile: { width: 58, height: 58, borderRadius: 29, borderWidth: 1, borderColor: BORDER, backgroundColor: '#202522', alignItems: 'center', justifyContent: 'center' },
  selectedIcon: { borderColor: '#245B2C', backgroundColor: '#142719' },
  rowCopy: { flex: 1, minWidth: 0 },
  rowTitle: { color: TEXT, fontFamily: 'Inter_600SemiBold', fontSize: 20, lineHeight: 28 },
  rowSubtitle: { marginTop: 3, color: MUTED, fontFamily: 'Inter_400Regular', fontSize: 14, lineHeight: 21 },
  radio: { width: 36, height: 36, borderRadius: 18, borderWidth: 2, borderColor: MUTED, alignItems: 'center', justifyContent: 'center' },
  radioSelected: { borderColor: GREEN, backgroundColor: GREEN },
  emptyState: { minHeight: 200, alignItems: 'center', justifyContent: 'center', gap: 12 },
  emptyText: { color: MUTED, fontFamily: 'Inter_400Regular', fontSize: 16, lineHeight: 24, textAlign: 'center' },
  tamilRegular: { fontFamily: 'NotoSansTamil_400Regular' },
  tamilBold: { fontFamily: 'NotoSansTamil_600SemiBold' },
  dropdownContainer: { width: '100%' },
  label: { marginBottom: 8, color: MUTED, fontFamily: 'Inter_500Medium', fontSize: 14, lineHeight: 20 },
  dropdownField: { width: '100%', minHeight: 62, paddingHorizontal: 16, borderRadius: 17, borderWidth: 1.5, borderColor: BORDER, backgroundColor: SURFACE, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  dropdownContent: { flex: 1, minWidth: 0, flexDirection: 'row', alignItems: 'center' },
  accessory: { marginRight: 12 },
  dropdownText: { flexShrink: 1, color: TEXT, fontFamily: 'Inter_400Regular', fontSize: 16, lineHeight: 24 },
  placeholder: { color: MUTED },
});
