import { Check, ChevronDown, ChevronRight, Leaf, Search, X } from 'lucide-react-native';
import { type ReactNode, useMemo, useState } from 'react';
import {
  FlatList, KeyboardAvoidingView, Modal, Platform, StyleSheet, TextInput, View,
  type StyleProp, type TextStyle, type ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useTranslation } from 'react-i18next';

import { COMMON_CROPS, type Crop } from '@/constants/crops';
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

export function normalizeCropSearch(value: string): string {
  return value.trim().replace(/\s+/g, ' ').toLocaleLowerCase();
}

export function filterCrops(crops: Crop[], query: string): Crop[] {
  const normalized = normalizeCropSearch(query);
  if (!normalized) return crops;
  return crops.filter((crop) =>
    [crop.en, crop.ta, crop.id].some((label) =>
      normalizeCropSearch(label).includes(normalized),
    ),
  );
}

export interface CropSelectorProps {
  visible: boolean;
  selectedCrop?: string | null;
  onSelect: (cropId: string) => void;
  onClose: () => void;
}

/** Shared crop picker backed exclusively by the app's canonical crop configuration. */
export function CropSelector({ visible, selectedCrop, onSelect, onClose }: CropSelectorProps) {
  const { t } = useTranslation();
  const { language, isTamil } = useLanguage();
  const [query, setQuery] = useState('');
  const crops = useMemo(() => filterCrops(COMMON_CROPS, query), [query]);

  const close = () => {
    setQuery('');
    onClose();
  };

  return (
    <Modal visible={visible} transparent statusBarTranslucent animationType="slide" onRequestClose={close}>
      <KeyboardAvoidingView
        style={styles.backdrop}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <SafeAreaView style={styles.sheet} edges={['bottom']}>
          <View style={styles.dragHandle} />
          <View style={styles.header}>
            <View style={styles.titleRow}>
              <Leaf size={30} color={GREEN} />
              <AgText variant="headingL" weight="bold" style={styles.primaryText}>
                {t('cropSelector.title')}
              </AgText>
            </View>
            <AgPressable
              haptic={false}
              onPress={close}
              accessibilityRole="button"
              accessibilityLabel={t('cropSelector.close')}
              style={styles.closeButton}
            >
              <X size={27} color={TEXT} />
            </AgPressable>
          </View>

          <View style={styles.searchField}>
            <Search size={23} color={MUTED} />
            <TextInput
              testID="crop-search-input"
              value={query}
              onChangeText={setQuery}
              placeholder={t('cropSelector.searchPlaceholder')}
              placeholderTextColor={MUTED}
              accessibilityLabel={t('cropSelector.searchPlaceholder')}
              autoCorrect={false}
              autoCapitalize="none"
              returnKeyType="search"
              keyboardAppearance="dark"
              style={[styles.searchInput, isTamil && styles.tamilInput]}
            />
          </View>

          <FlatList
            testID="crop-list"
            data={crops}
            keyExtractor={(crop) => crop.id}
            keyboardShouldPersistTaps="handled"
            keyboardDismissMode="on-drag"
            initialNumToRender={12}
            windowSize={7}
            contentContainerStyle={styles.listContent}
            ListEmptyComponent={
              <View style={styles.emptyState}>
                <Search size={34} color={MUTED} />
                <AgText variant="body" style={styles.secondaryText}>{t('cropSelector.noResults')}</AgText>
              </View>
            }
            renderItem={({ item }) => {
              const selected = item.id === selectedCrop;
              const label = language === 'ta' ? item.ta : item.en;
              const secondaryLabel = language === 'ta' ? item.en : item.ta;
              return (
                <AgPressable
                  haptic={false}
                  onPress={() => { onSelect(item.id); close(); }}
                  accessibilityRole="radio"
                  accessibilityState={{ selected }}
                  accessibilityLabel={`${label}, ${secondaryLabel}`}
                  style={({ pressed }) => [styles.row, selected && styles.selectedRow, pressed && styles.pressed]}
                >
                  <View style={[styles.cropTile, selected && styles.selectedTile]}>
                    <Leaf size={23} color={selected ? GREEN : MUTED} />
                  </View>
                  <View style={styles.rowCopy}>
                    <AgText variant="bodyLarge" weight={selected ? 'semibold' : 'medium'} style={styles.primaryText}>
                      {label}
                    </AgText>
                    <AgText variant="caption" style={styles.secondaryText}>{secondaryLabel}</AgText>
                  </View>
                  {selected
                    ? <View style={styles.checkTile}><Check size={19} color={SHEET_BG} /></View>
                    : <ChevronRight size={22} color={MUTED} />}
                </AgPressable>
              );
            }}
            ItemSeparatorComponent={() => <View style={styles.separator} />}
          />
        </SafeAreaView>
      </KeyboardAvoidingView>
    </Modal>
  );
}

interface AgCropDropdownProps {
  label?: string;
  required?: boolean;
  placeholder: string;
  value?: string;
  onChange: (cropId: string) => void;
  error?: string;
  leftAccessory?: ReactNode;
  fieldStyle?: StyleProp<ViewStyle>;
  textStyle?: StyleProp<TextStyle>;
  labelStyle?: StyleProp<TextStyle>;
}

/** Form-field wrapper around the shared CropSelector. */
export function AgCropDropdown({
  label, required, placeholder, value, onChange, error, leftAccessory, fieldStyle, textStyle, labelStyle,
}: AgCropDropdownProps) {
  const { colors } = useAppTheme();
  const { language } = useLanguage();
  const [visible, setVisible] = useState(false);
  const selected = COMMON_CROPS.find((crop) => crop.id === value);
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
        className={cn('flex-row items-center justify-between border', error ? 'border-danger' : 'border-border')}
        style={({ pressed }) => [
          styles.dropdownField,
          { borderColor: error ? colors.danger : colors.border, backgroundColor: colors.surface },
          fieldStyle,
          pressed && styles.pressed,
        ]}
      >
        <View style={styles.dropdownContent}>
          {leftAccessory ? <View pointerEvents="none" style={styles.dropdownAccessory}>{leftAccessory}</View> : null}
          <AgText color={selectedLabel ? 'default' : 'disabled'} numberOfLines={1} style={[styles.dropdownText, textStyle]}>
            {selectedLabel ?? placeholder}
          </AgText>
        </View>
        <ChevronDown size={20} color={colors.textMuted} />
      </AgPressable>
      {error ? <AgText variant="caption" color="danger" style={styles.error}>{error}</AgText> : null}
      <CropSelector visible={visible} selectedCrop={value} onSelect={onChange} onClose={() => setVisible(false)} />
    </View>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.72)' },
  sheet: { height: '82%', overflow: 'hidden', borderTopLeftRadius: 30, borderTopRightRadius: 30, borderWidth: 1, borderBottomWidth: 0, borderColor: BORDER, backgroundColor: SHEET_BG },
  dragHandle: { width: 58, height: 5, marginTop: 12, marginBottom: 14, borderRadius: 3, alignSelf: 'center', backgroundColor: '#6D726F' },
  header: { paddingHorizontal: 22, paddingBottom: 18, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 },
  titleRow: { flex: 1, minWidth: 0, flexDirection: 'row', alignItems: 'center', gap: 12 },
  primaryText: { color: TEXT },
  secondaryText: { color: MUTED },
  closeButton: { width: 46, height: 46, borderRadius: 23, backgroundColor: '#202321', alignItems: 'center', justifyContent: 'center' },
  searchField: { minHeight: 60, marginHorizontal: 22, marginBottom: 14, borderRadius: 17, borderWidth: 1, borderColor: BORDER, backgroundColor: SURFACE, paddingHorizontal: 16, flexDirection: 'row', alignItems: 'center', gap: 12 },
  searchInput: { flex: 1, minHeight: 58, paddingVertical: 0, color: TEXT, backgroundColor: SURFACE, fontSize: 17 },
  tamilInput: { fontFamily: 'NotoSansTamil_400Regular' },
  listContent: { marginHorizontal: 22, paddingBottom: 28, borderWidth: 1, borderColor: BORDER, borderRadius: 20, overflow: 'hidden' },
  row: { minHeight: 76, paddingVertical: 10, paddingHorizontal: 16, flexDirection: 'row', alignItems: 'center', gap: 14, backgroundColor: SURFACE },
  selectedRow: { backgroundColor: '#102016' },
  cropTile: { width: 48, height: 48, borderRadius: 24, borderWidth: 1, borderColor: BORDER, alignItems: 'center', justifyContent: 'center' },
  selectedTile: { borderColor: GREEN, backgroundColor: '#132719' },
  checkTile: { width: 28, height: 28, borderRadius: 14, backgroundColor: GREEN, alignItems: 'center', justifyContent: 'center' },
  rowCopy: { flex: 1, minWidth: 0, gap: 2 },
  separator: { height: StyleSheet.hairlineWidth, backgroundColor: BORDER },
  emptyState: { minHeight: 180, alignItems: 'center', justifyContent: 'center', gap: 12, backgroundColor: SURFACE },
  pressed: { opacity: 0.8 },
  dropdownContainer: { width: '100%' },
  dropdownLabel: { marginBottom: 8 },
  dropdownField: { minHeight: 58, paddingHorizontal: 16, borderRadius: 14, borderWidth: 1.5, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  dropdownContent: { flex: 1, minWidth: 0, flexDirection: 'row', alignItems: 'center' },
  dropdownAccessory: { marginRight: 12 },
  dropdownText: { flexShrink: 1 },
  error: { marginTop: 6 },
});
