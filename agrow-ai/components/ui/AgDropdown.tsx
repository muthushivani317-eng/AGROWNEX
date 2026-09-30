import { Check, ChevronDown, Leaf, Search, Sprout, X } from 'lucide-react-native';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FlatList, Modal, StyleSheet, TextInput, TouchableOpacity, View, type StyleProp, type TextStyle, type ViewStyle } from 'react-native';
import type { ReactNode } from 'react';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useAppTheme } from '@/hooks/useAppTheme';
import { useLanguage } from '@/hooks/useLanguage';
import { cn } from '@/utils/cn';

import { AgText } from './AgText';

export interface AgDropdownOption {
  value: string;
  label: string;
  sublabel?: string;
  /** Expanded, illustrated selector row for curated organic product choices. */
  description?: string;
}

export interface AgDropdownProps {
  /** Force the high-contrast light picker used by fixed-light flows. */
  light?: boolean;
  label?: string;
  required?: boolean;
  placeholder: string;
  value?: string;
  options: AgDropdownOption[];
  onChange: (value: string) => void;
  searchable?: boolean;
  error?: string;
  title?: string;
  openRequest?: number;
  leftAccessory?: ReactNode;
  fieldStyle?: ViewStyle;
  textStyle?: StyleProp<TextStyle>;
  labelStyle?: StyleProp<TextStyle>;
  optionVariant?: 'default' | 'organicProduct';
}

/**
 * Themed single-select picker that opens a full-screen searchable list —
 * preferred over native pickers for consistency and large, farmer-friendly tap
 * targets.
 */
export function AgDropdown({
  light = false,
  label,
  required,
  placeholder,
  value,
  options,
  onChange,
  searchable = true,
  error,
  title,
  openRequest,
  leftAccessory,
  fieldStyle,
  textStyle,
  labelStyle,
  optionVariant = 'default',
}: AgDropdownProps) {
  const { t } = useTranslation();
  const { colors, isDark } = useAppTheme();
  const palette = light
    ? {
        bg: '#F8F5E9', surface: '#FFFDF8', text: '#173B2B', muted: '#5F6F67',
        border: '#D8D1BD', primary: '#176B36', onPrimary: '#FFFFFF', soft: '#EAF3E5',
        danger: '#B43A32',
      }
    : {
        bg: colors.bg, surface: colors.surface, text: colors.text, muted: colors.textMuted,
        border: colors.border, primary: colors.primary, onPrimary: colors.onPrimary,
        soft: colors.primaryLight, danger: colors.danger,
      };
  const { isTamil } = useLanguage();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');

  useEffect(() => {
    if (openRequest) setOpen(true);
  }, [openRequest]);

  const selected = options.find((o) => o.value === value);

  const filtered = useMemo(() => {
    if (!query.trim()) return options;
    const q = query.toLowerCase();
    return options.filter((o) => o.label.toLowerCase().includes(q));
  }, [options, query]);

  return (
    <View className="w-full" style={styles.container}>
      {label ? (
        <AgText variant="label" weight="semibold" color="muted" className="mb-2" style={[light && { color: palette.text }, labelStyle]}>
          {label}{required ? <AgText color="danger"> *</AgText> : null}
        </AgText>
      ) : null}

      <TouchableOpacity
        activeOpacity={0.78}
        onPress={() => setOpen(true)}
        accessibilityRole="button"
        className={cn(
          'h-14 flex-row items-center justify-between rounded-md border bg-surface-card px-4',
          error ? 'border-danger' : 'border-border',
        )}
        style={[
          styles.field,
          {
            borderColor: error ? palette.danger : palette.border,
            backgroundColor: palette.surface,
          },
          fieldStyle,
        ]}
      >
        <View style={styles.fieldContent}>
          {leftAccessory ? <View pointerEvents="none" style={styles.leftAccessory}>{leftAccessory}</View> : null}
          <AgText color={selected ? 'default' : 'disabled'} numberOfLines={1} style={[styles.fieldText, { color: selected ? palette.text : palette.muted }, textStyle]}>
            {selected?.label ?? placeholder}
          </AgText>
        </View>
        <ChevronDown size={20} color={palette.primary} />
      </TouchableOpacity>

      {error ? (
        <AgText variant="caption" color="danger" className="mt-1.5">
          {error}
        </AgText>
      ) : null}

      <Modal
        visible={open}
        animationType="slide"
        presentationStyle="fullScreen"
        onRequestClose={() => setOpen(false)}
      >
        <SafeAreaView style={[styles.modal, { backgroundColor: palette.bg }]} edges={['top', 'bottom']}>
          <View style={[styles.modalHeader, optionVariant === 'organicProduct' && styles.productModalHeader, { borderBottomColor: palette.border }]}>
            <View accessible={false} style={[styles.modalMark, { backgroundColor: palette.soft }]}>
              <Check size={22} color={palette.primary} />
            </View>
            <AgText variant="headingS" weight="bold" numberOfLines={2} style={[styles.modalTitle, { color: palette.text }]}>
              {title ?? placeholder}
            </AgText>
            <TouchableOpacity
              activeOpacity={0.72}
              onPress={() => setOpen(false)}
              accessibilityRole="button"
              accessibilityLabel={t('common.close')}
              style={[styles.closeButton, { backgroundColor: palette.surface, borderColor: palette.border }]}
            >
              <X size={24} color={palette.text} />
            </TouchableOpacity>
          </View>

          {searchable ? (
            <View style={[styles.search, { borderColor: palette.border, backgroundColor: palette.surface }]}>
              <Search size={20} color={palette.primary} />
              <TextInput
                value={query}
                onChangeText={setQuery}
                placeholder={placeholder}
                placeholderTextColor={palette.muted}
                accessibilityLabel={placeholder}
                returnKeyType="search"
                className={cn(
                  'ml-2 h-full flex-1 text-[16px] text-content',
                  isTamil ? 'font-tamil' : 'font-sans',
                )}
                style={[styles.searchInput, { color: palette.text, backgroundColor: palette.surface }]}
              />
            </View>
          ) : null}

          <FlatList
            data={filtered}
            keyExtractor={(o) => o.value}
            keyboardShouldPersistTaps="handled"
            contentContainerStyle={styles.listContent}
            renderItem={({ item }) => {
              const isSel = item.value === value;
              if (optionVariant === 'organicProduct') {
                const Icon = item.value.toLowerCase().includes('seed') ? Sprout : Leaf;
                return <TouchableOpacity activeOpacity={0.76} onPress={() => { onChange(item.value); setQuery(''); setOpen(false); }} accessibilityRole="radio" accessibilityState={{ checked: isSel }} style={[styles.productOption, { backgroundColor: isSel ? palette.soft : palette.surface, borderColor: isSel ? palette.primary : palette.border }]}><View style={[styles.productArt, { backgroundColor: isDark ? '#25462D' : '#EAF6E6' }]}><View style={[styles.productGlow, { backgroundColor: palette.primary }]} /><Icon size={40} color={palette.primary} /></View><View style={styles.optionCopy}><AgText variant="headingS" weight="bold" style={{ color: palette.text }}>{item.label}</AgText>{item.description || item.sublabel ? <AgText variant="bodySmall" numberOfLines={3} style={[styles.productDescription, { color: palette.muted }]}>{item.description ?? item.sublabel}</AgText> : null}</View><View style={[styles.productRadio, { borderColor: isSel ? palette.primary : palette.muted, backgroundColor: isSel ? palette.primary : palette.surface }]}>{isSel ? <Check size={22} color={palette.onPrimary} /> : null}</View></TouchableOpacity>;
              }
              return (
                <TouchableOpacity
                  activeOpacity={0.76}
                  onPress={() => {
                    onChange(item.value);
                    setQuery('');
                    setOpen(false);
                  }}
                  accessibilityRole="radio"
                  accessibilityState={{ checked: isSel }}
                  style={[
                    styles.option,
                    { backgroundColor: isSel ? palette.soft : palette.surface, borderColor: isSel ? palette.primary : palette.border },
                  ]}
                >
                  <View style={styles.optionCopy}>
                    <AgText weight={isSel ? 'bold' : 'semibold'} style={{ color: palette.text }}>{item.label}</AgText>
                    {item.sublabel ? (
                      <AgText variant="caption" color="disabled" style={{ color: palette.muted }}>
                        {item.sublabel}
                      </AgText>
                    ) : null}
                  </View>
                  <View style={[styles.radio, { borderColor: isSel ? palette.primary : palette.muted, backgroundColor: isSel ? palette.primary : palette.surface }]}>
                    {isSel ? <Check size={16} color={palette.onPrimary} /> : null}
                  </View>
                </TouchableOpacity>
              );
            }}
          />
        </SafeAreaView>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { width: '100%' },
  field: { minHeight: 58, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderRadius: 14, borderWidth: 1.5, paddingHorizontal: 16 },
  fieldContent: { flex: 1, minWidth: 0, flexDirection: 'row', alignItems: 'center' },
  leftAccessory: { marginRight: 12 },
  fieldText: { flexShrink: 1 },
  modal: { flex: 1 },
  modalHeader: { minHeight: 80, flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 12, gap: 12, borderBottomWidth: StyleSheet.hairlineWidth },
  productModalHeader: { minHeight: 102, paddingTop: 20, paddingBottom: 16 },
  modalMark: { width: 44, height: 44, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  modalTitle: { flex: 1 },
  closeButton: { width: 48, height: 48, borderRadius: 16, borderWidth: 1, alignItems: 'center', justifyContent: 'center' },
  search: { height: 56, marginHorizontal: 20, marginTop: 16, marginBottom: 12, flexDirection: 'row', alignItems: 'center', borderRadius: 16, borderWidth: 1.5, paddingHorizontal: 16 },
  searchInput: { flex: 1, height: '100%', marginLeft: 8, fontSize: 16 },
  listContent: { paddingHorizontal: 20, paddingBottom: 32, gap: 10 },
  option: { minHeight: 64, flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 12, borderRadius: 18, borderWidth: 1 },
  productOption: { minHeight: 132, flexDirection: 'row', alignItems: 'center', padding: 14, borderRadius: 22, borderWidth: 1.5, gap: 13 },
  productArt: { width: 86, height: 96, borderRadius: 18, overflow: 'hidden', alignItems: 'center', justifyContent: 'center' },
  productGlow: { position: 'absolute', width: 78, height: 78, borderRadius: 39, opacity: 0.16, transform: [{ translateX: 19 }, { translateY: -20 }] },
  productDescription: { marginTop: 5, lineHeight: 20 },
  productRadio: { width: 48, height: 48, borderRadius: 24, borderWidth: 2, alignItems: 'center', justifyContent: 'center' },
  optionCopy: { flex: 1, minWidth: 0, paddingRight: 12 },
  radio: { width: 28, height: 28, borderRadius: 14, borderWidth: 2, alignItems: 'center', justifyContent: 'center' },
});
