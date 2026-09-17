import { Check, ChevronDown, ChevronRight, ListFilter, MapPin, Search, X } from 'lucide-react-native';
import { type ReactNode, useEffect, useMemo, useState } from 'react';
import {
  FlatList,
  Modal,
  StyleSheet,
  TextInput,
  View,
  type StyleProp,
  type TextStyle,
  type ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useTranslation } from 'react-i18next';

import { TAMIL_NADU_DISTRICTS, type District } from '@/constants/locations';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useLanguage } from '@/hooks/useLanguage';
import { cn } from '@/utils/cn';

import { AgPressable } from './AgPressable';
import { AgText } from './AgText';

const SHEET_BG = '#0B0E0C';
const SURFACE = '#151917';
const BORDER = '#2B312D';
const TEXT = '#F5F7F5';
const MUTED = '#AEB4B0';
const GREEN = '#4CAF50';

export function normalizeDistrictSearch(value: string): string {
  return value.trim().replace(/\s+/g, ' ').toLocaleLowerCase();
}

export function filterAndSortDistricts(
  districts: District[],
  query: string,
  language: 'ta' | 'en',
): District[] {
  const normalized = normalizeDistrictSearch(query);
  return districts
    .filter((district) => {
      if (!normalized) return true;
      return [district.en, district.ta, district.id]
        .some((label) => normalizeDistrictSearch(label).includes(normalized));
    })
    .sort((a, b) => {
      const aLabel = language === 'ta' ? a.ta : a.en;
      const bLabel = language === 'ta' ? b.ta : b.en;
      return aLabel.localeCompare(bLabel, language === 'ta' ? 'ta' : 'en');
    });
}

export interface DistrictSelectorProps {
  visible: boolean;
  selectedDistrict?: string | null;
  onSelect: (districtId: string) => void;
  onClose: () => void;
}

/** The single app-wide Tamil Nadu district-selection experience. */
export function DistrictSelector({
  visible,
  selectedDistrict,
  onSelect,
  onClose,
}: DistrictSelectorProps) {
  const { t } = useTranslation();
  const { language, isTamil } = useLanguage();
  const [query, setQuery] = useState('');
  const districts = useMemo(
    () => filterAndSortDistricts(TAMIL_NADU_DISTRICTS, query, language),
    [language, query],
  );

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
            <View style={styles.headerCopy}>
              <AgText variant="headingL" weight="bold" style={styles.primaryText}>
                {t('districtSelector.title')}
              </AgText>
              <AgText variant="body" style={styles.secondaryText}>
                {t('districtSelector.subtitle')}
              </AgText>
            </View>
            <AgPressable
              haptic={false}
              onPress={close}
              accessibilityRole="button"
              accessibilityLabel={t('districtSelector.close')}
              style={styles.closeButton}
            >
              <X size={27} color={TEXT} />
            </AgPressable>
          </View>

          <View style={styles.searchField}>
            <Search size={24} color={MUTED} />
            <TextInput
              testID="district-search-input"
              value={query}
              onChangeText={setQuery}
              placeholder={t('districtSelector.searchPlaceholder')}
              placeholderTextColor={MUTED}
              accessibilityLabel={t('districtSelector.searchPlaceholder')}
              autoCorrect={false}
              autoCapitalize="none"
              returnKeyType="search"
              keyboardAppearance="dark"
              style={[styles.searchInput, isTamil && styles.tamilInput]}
            />
          </View>

          <View style={styles.listHeader}>
            <AgText variant="bodyLarge" weight="medium" style={styles.primaryText}>
              {t('districtSelector.allDistricts')}
            </AgText>
            <View style={styles.sortLabel} accessibilityLabel={t('districtSelector.sortAZ')}>
              <ListFilter size={19} color={GREEN} />
              <AgText variant="bodySmall" style={styles.secondaryText}>{t('districtSelector.sortAZ')}</AgText>
            </View>
          </View>

          <FlatList
            testID="district-list"
            data={districts}
            keyExtractor={(district) => district.id}
            keyboardShouldPersistTaps="handled"
            keyboardDismissMode="on-drag"
            initialNumToRender={12}
            windowSize={7}
            contentContainerStyle={styles.listContent}
            ListEmptyComponent={
              <View style={styles.emptyState}>
                <Search size={34} color={MUTED} />
                <AgText variant="body" color="inherit" style={styles.secondaryText}>
                  {t('districtSelector.noResults')}
                </AgText>
              </View>
            }
            renderItem={({ item }) => {
              const selected = item.id === selectedDistrict;
              const label = language === 'ta' ? item.ta : item.en;
              return (
                <AgPressable
                  haptic={false}
                  onPress={() => {
                    onSelect(item.id);
                    close();
                  }}
                  accessibilityRole="button"
                  accessibilityState={{ selected }}
                  accessibilityLabel={label}
                  style={({ pressed }) => [
                    styles.row,
                    selected && styles.selectedRow,
                    pressed && styles.pressed,
                  ]}
                >
                  <View style={styles.pinTile}><MapPin size={22} color={GREEN} /></View>
                  <View style={styles.rowCopy}>
                    <AgText variant="bodyLarge" weight={selected ? 'semibold' : 'regular'} style={styles.primaryText}>
                      {label}
                    </AgText>
                    {isTamil ? <AgText variant="caption" style={styles.secondaryText}>{item.en}</AgText> : null}
                  </View>
                  {selected ? <Check size={22} color={GREEN} /> : <ChevronRight size={22} color={MUTED} />}
                </AgPressable>
              );
            }}
            ItemSeparatorComponent={() => <View style={styles.separator} />}
          />
        </SafeAreaView>
      </View>
    </Modal>
  );
}

interface AgDistrictDropdownProps {
  label?: string;
  required?: boolean;
  placeholder: string;
  value?: string;
  onChange: (districtId: string) => void;
  error?: string;
  openRequest?: number;
  leftAccessory?: ReactNode;
  fieldStyle?: ViewStyle;
  textStyle?: StyleProp<TextStyle>;
  labelStyle?: StyleProp<TextStyle>;
}

/** Form-field wrapper around the global DistrictSelector. */
export function AgDistrictDropdown({
  label,
  required,
  placeholder,
  value,
  onChange,
  error,
  openRequest,
  leftAccessory,
  fieldStyle,
  textStyle,
  labelStyle,
}: AgDistrictDropdownProps) {
  const { colors } = useAppTheme();
  const { language } = useLanguage();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (openRequest) setVisible(true);
  }, [openRequest]);

  const selected = TAMIL_NADU_DISTRICTS.find((district) => district.id === value);
  const selectedLabel = selected ? (language === 'ta' ? selected.ta : selected.en) : null;

  return (
    <View style={styles.dropdownContainer}>
      {label ? (
        <AgText variant="label" weight="medium" color="muted" style={[styles.dropdownLabel, labelStyle]}>
          {label}{required ? <AgText color="danger"> *</AgText> : null}
        </AgText>
      ) : null}
      <AgPressable
        haptic={false}
        onPress={() => setVisible(true)}
        accessibilityRole="button"
        accessibilityState={{ expanded: visible }}
        accessibilityLabel={selectedLabel ?? placeholder}
        className={cn('flex-row items-center justify-between border bg-surface-card', error ? 'border-danger' : 'border-border')}
        style={({ pressed }) => [
          styles.dropdownField,
          { borderColor: error ? colors.danger : colors.border, backgroundColor: colors.surface },
          fieldStyle,
          pressed && styles.pressed,
        ]}
      >
        <View style={styles.dropdownContent}>
          {leftAccessory ? <View pointerEvents="none" style={styles.dropdownAccessory}>{leftAccessory}</View> : null}
          <AgText
            color={selectedLabel ? 'default' : 'disabled'}
            numberOfLines={1}
            style={[styles.dropdownText, textStyle]}
          >
            {selectedLabel ?? placeholder}
          </AgText>
        </View>
        <ChevronDown size={20} color={colors.textMuted} />
      </AgPressable>
      {error ? <AgText variant="caption" color="danger" style={styles.error}>{error}</AgText> : null}

      <DistrictSelector
        visible={visible}
        selectedDistrict={value}
        onSelect={onChange}
        onClose={() => setVisible(false)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.72)' },
  sheet: {
    flex: 1, marginTop: 20, overflow: 'hidden', borderTopLeftRadius: 30, borderTopRightRadius: 30,
    backgroundColor: SHEET_BG,
  },
  dragHandle: { width: 68, height: 5, marginTop: 12, marginBottom: 12, borderRadius: 3, alignSelf: 'center', backgroundColor: '#E8EBE9' },
  header: { paddingHorizontal: 22, paddingBottom: 20, flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  headerCopy: { flex: 1, gap: 4 },
  primaryText: { color: TEXT },
  secondaryText: { color: MUTED },
  closeButton: { width: 50, height: 50, borderRadius: 25, backgroundColor: '#202321', alignItems: 'center', justifyContent: 'center' },
  searchField: {
    minHeight: 62, marginHorizontal: 22, borderRadius: 18, borderWidth: 1.5, borderColor: GREEN,
    backgroundColor: SURFACE, paddingHorizontal: 17, flexDirection: 'row', alignItems: 'center', gap: 12,
  },
  searchInput: { flex: 1, minHeight: 58, paddingVertical: 0, color: TEXT, backgroundColor: SURFACE, fontSize: 17 },
  tamilInput: { fontFamily: 'NotoSansTamil_400Regular' },
  listHeader: { paddingHorizontal: 22, paddingTop: 24, paddingBottom: 10, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  sortLabel: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  listContent: { paddingHorizontal: 22, paddingBottom: 24 },
  row: { minHeight: 72, paddingVertical: 10, paddingHorizontal: 3, flexDirection: 'row', alignItems: 'center', gap: 14 },
  selectedRow: { backgroundColor: 'rgba(76,175,80,0.06)' },
  pinTile: { width: 48, height: 48, borderRadius: 24, backgroundColor: '#132719', alignItems: 'center', justifyContent: 'center' },
  rowCopy: { flex: 1, minWidth: 0 },
  separator: { height: StyleSheet.hairlineWidth, backgroundColor: BORDER },
  emptyState: { minHeight: 180, alignItems: 'center', justifyContent: 'center', gap: 12 },
  pressed: { opacity: 0.8 },
  dropdownContainer: { width: '100%' },
  dropdownLabel: { marginBottom: 8 },
  dropdownField: { minHeight: 58, paddingHorizontal: 16, borderRadius: 14, borderWidth: 1.5, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  dropdownContent: { flex: 1, minWidth: 0, flexDirection: 'row', alignItems: 'center' },
  dropdownAccessory: { marginRight: 12 },
  dropdownText: { flexShrink: 1 },
  error: { marginTop: 6 },
});
