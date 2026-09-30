import { Check, ChevronDown, Search, X } from 'lucide-react-native';
import { useMemo, useState } from 'react';
import {
  FlatList,
  KeyboardAvoidingView,
  Modal,
  Platform,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AgPressable, AgText } from '@/components/ui';

import type { LocalizedCatalogLabel, OnboardingProductOption } from './onboardingData';

const GREEN = '#165B33';
const CREAM = '#FFFDF6';
const BORDER = '#D8D5C9';
const TEXT = '#173B2B';
const MUTED = '#66736B';

interface Props {
  language: 'ta' | 'en';
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  label: string;
  placeholder: string;
  products: OnboardingProductOption[];
  categories: LocalizedCatalogLabel[];
}

export function ProductMultiSelect({ language, selectedIds, onChange, label, placeholder, products, categories }: Props) {
  const [visible, setVisible] = useState(false);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<string | 'all'>('all');
  const rows = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    return products.filter((product) => {
      const inCategory = category === 'all' || product.category === category;
      const matches = !needle || `${product.ta} ${product.en}`.toLocaleLowerCase().includes(needle);
      return inCategory && matches;
    });
  }, [category, products, query]);

  const toggle = (id: string) => {
    onChange(selectedIds.includes(id) ? selectedIds.filter((item) => item !== id) : [...selectedIds, id]);
  };

  return (
    <>
      <AgPressable
        onPress={() => setVisible(true)}
        accessibilityRole="button"
        accessibilityState={{ expanded: visible }}
        style={({ pressed }) => [styles.trigger, pressed && styles.pressed]}
      >
        <View style={styles.triggerCopy}>
          <AgText variant="body" weight="semibold" style={styles.text}>{label}</AgText>
          <AgText variant="bodySmall" style={styles.muted}>
            {selectedIds.length ? `${selectedIds.length} ${language === 'ta' ? 'தேர்வு' : 'selected'}` : placeholder}
          </AgText>
        </View>
        <ChevronDown size={24} color={GREEN} />
      </AgPressable>

      <Modal visible={visible} transparent animationType="slide" statusBarTranslucent onRequestClose={() => setVisible(false)}>
        <KeyboardAvoidingView style={styles.backdrop} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
          <SafeAreaView style={styles.sheet} edges={['bottom']}>
            <View style={styles.handle} />
            <View style={styles.header}>
              <View style={styles.triggerCopy}>
                <AgText variant="headingS" weight="bold" style={styles.text}>
                  {language === 'ta' ? 'விளைபொருட்களைத் தேர்வு செய்க' : 'Select farm products'}
                </AgText>
                <AgText variant="bodySmall" style={styles.muted}>
                  {language === 'ta' ? 'பலவற்றைத் தேர்வு செய்யலாம்' : 'You can select more than one'}
                </AgText>
              </View>
              <AgPressable onPress={() => setVisible(false)} accessibilityRole="button" style={styles.close}>
                <X size={24} color={TEXT} />
              </AgPressable>
            </View>
            <View style={styles.search}>
              <Search size={22} color={MUTED} />
              <TextInput
                value={query}
                onChangeText={setQuery}
                placeholder={language === 'ta' ? 'தேடுங்கள்…' : 'Search…'}
                placeholderTextColor={MUTED}
                style={styles.searchInput}
                autoCorrect={false}
                accessibilityLabel={language === 'ta' ? 'விளைபொருள் தேடல்' : 'Search farm products'}
              />
            </View>
            <FlatList
              horizontal
              data={[{ code: 'all', en: 'All', ta: 'அனைத்தும்' }, ...categories]}
              keyExtractor={(item) => item.code}
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.categories}
              renderItem={({ item }) => {
                const active = category === item.code;
                const categoryLabel = item[language];
                return (
                  <AgPressable onPress={() => setCategory(item.code)} style={[styles.category, active && styles.categoryActive]}>
                    <AgText variant="bodySmall" weight="semibold" style={active ? styles.categoryActiveText : styles.text}>
                      {categoryLabel}
                    </AgText>
                  </AgPressable>
                );
              }}
            />
            <FlatList
              data={rows}
              keyExtractor={(item) => item.code}
              keyboardShouldPersistTaps="handled"
              contentContainerStyle={styles.list}
              ListEmptyComponent={<AgText variant="body" style={styles.empty}>{language === 'ta' ? 'பொருள் கிடைக்கவில்லை' : 'No products found'}</AgText>}
              renderItem={({ item }) => {
                const selected = selectedIds.includes(item.code);
                return (
                  <AgPressable
                    onPress={() => toggle(item.code)}
                    accessibilityRole="checkbox"
                    accessibilityState={{ checked: selected }}
                    style={[styles.row, selected && styles.rowSelected]}
                  >
                    <View style={[styles.check, selected && styles.checkSelected]}>
                      {selected ? <Check size={17} color="#FFFFFF" strokeWidth={3} /> : null}
                    </View>
                    <View style={styles.triggerCopy}>
                      <AgText variant="body" weight="semibold" style={styles.text}>{item[language]}</AgText>
                      <AgText variant="caption" style={styles.muted}>{item[language === 'ta' ? 'en' : 'ta']}</AgText>
                    </View>
                  </AgPressable>
                );
              }}
            />
            <AgPressable onPress={() => setVisible(false)} style={styles.done}>
              <AgText variant="body" weight="bold" style={styles.doneText}>
                {language === 'ta' ? `முடிந்தது (${selectedIds.length})` : `Done (${selectedIds.length})`}
              </AgText>
            </AgPressable>
          </SafeAreaView>
        </KeyboardAvoidingView>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  trigger: { minHeight: 68, borderWidth: 1.3, borderColor: BORDER, borderRadius: 16, backgroundColor: '#FFFFFF', paddingHorizontal: 16, flexDirection: 'row', alignItems: 'center', gap: 12 },
  triggerCopy: { flex: 1, minWidth: 0, gap: 3 },
  text: { color: TEXT },
  muted: { color: MUTED },
  pressed: { opacity: 0.76 },
  backdrop: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(15,35,25,0.45)' },
  sheet: { height: '88%', borderTopLeftRadius: 28, borderTopRightRadius: 28, backgroundColor: CREAM, paddingTop: 10 },
  handle: { width: 52, height: 5, borderRadius: 3, backgroundColor: '#B8B9AE', alignSelf: 'center', marginBottom: 12 },
  header: { minHeight: 62, paddingHorizontal: 20, flexDirection: 'row', alignItems: 'center', gap: 12 },
  close: { width: 48, height: 48, borderRadius: 24, alignItems: 'center', justifyContent: 'center', backgroundColor: '#F0EEE5' },
  search: { minHeight: 58, marginHorizontal: 20, marginTop: 10, borderWidth: 1.3, borderColor: BORDER, borderRadius: 16, backgroundColor: '#FFFFFF', paddingHorizontal: 15, flexDirection: 'row', alignItems: 'center', gap: 10 },
  searchInput: { flex: 1, minHeight: 56, color: TEXT, fontSize: 17 },
  categories: { paddingHorizontal: 20, paddingVertical: 14, gap: 8 },
  category: { minHeight: 44, borderWidth: 1, borderColor: BORDER, borderRadius: 22, paddingHorizontal: 15, alignItems: 'center', justifyContent: 'center', backgroundColor: '#FFFFFF' },
  categoryActive: { borderColor: GREEN, backgroundColor: GREEN },
  categoryActiveText: { color: '#FFFFFF' },
  list: { paddingHorizontal: 20, paddingBottom: 18, gap: 8 },
  row: { minHeight: 68, borderWidth: 1, borderColor: BORDER, borderRadius: 15, backgroundColor: '#FFFFFF', paddingHorizontal: 14, flexDirection: 'row', alignItems: 'center', gap: 13 },
  rowSelected: { borderColor: '#76A974', backgroundColor: '#EFF7EA' },
  check: { width: 28, height: 28, borderRadius: 8, borderWidth: 1.5, borderColor: '#AEB2A9', alignItems: 'center', justifyContent: 'center' },
  checkSelected: { borderColor: GREEN, backgroundColor: GREEN },
  empty: { color: MUTED, textAlign: 'center', paddingVertical: 44 },
  done: { minHeight: 58, marginHorizontal: 20, marginBottom: 10, borderRadius: 16, alignItems: 'center', justifyContent: 'center', backgroundColor: '#F5B51B' },
  doneText: { color: TEXT },
});
