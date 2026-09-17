import { ChevronRight, CloudSun, Droplets, FlaskConical, Leaf, type LucideIcon } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { StyleSheet, TouchableOpacity, View } from 'react-native';

import { AgText } from '@/components/ui';

import { SUGGESTION_KEYS } from '../constants';

const ICONS: LucideIcon[] = [Leaf, Droplets, FlaskConical, CloudSun];

/** Localized starter prompts; each row sends through the real chat flow. */
export function SuggestionChips({ onSelect, compact = false }: { onSelect: (text: string) => void; compact?: boolean }) {
  const { t } = useTranslation();

  if (compact) {
    return (
      <View style={styles.compactWrap} accessibilityLabel={t('ai.tryAsking')}>
        {SUGGESTION_KEYS.slice(0, 2).map((key, index) => {
          const Icon = ICONS[index];
          const prompt = t(key);
          return (
            <TouchableOpacity
              key={key}
              testID={`ai-suggestion-compact-${index + 1}`}
              onPress={() => onSelect(prompt)}
              activeOpacity={0.78}
              accessibilityRole="button"
              accessibilityLabel={prompt}
              style={styles.compactChip}
            >
              <Icon size={19} color="#165B33" />
              <AgText variant="bodySmall" weight="medium" numberOfLines={3} style={styles.compactText}>{prompt}</AgText>
            </TouchableOpacity>
          );
        })}
      </View>
    );
  }

  return (
    <View style={styles.card}>
      <AgText variant="bodyLarge" weight="bold" style={styles.heading}>
        {t('ai.tryAsking')}
      </AgText>
      {SUGGESTION_KEYS.map((key, index) => {
        const Icon = ICONS[index];
        const prompt = t(key);
        return (
          <TouchableOpacity
            key={key}
            testID={`ai-suggestion-${index + 1}`}
            onPress={() => onSelect(prompt)}
            activeOpacity={0.78}
            accessibilityRole="button"
            accessibilityLabel={prompt}
            style={[
              styles.row,
              index < SUGGESTION_KEYS.length - 1 && styles.rowDivider,
            ]}
          >
            <View style={styles.iconSlot}><Icon size={21} color="#165B33" /></View>
            <AgText variant="body" numberOfLines={3} style={styles.prompt}>{prompt}</AgText>
            <ChevronRight size={21} color="#165B33" />
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { marginTop: 28, borderRadius: 22, borderWidth: 1, borderColor: '#B9CCBC', backgroundColor: '#FFFDF8', paddingHorizontal: 18, paddingTop: 18, paddingBottom: 6 },
  heading: { marginBottom: 6, color: '#165B33' },
  row: { minHeight: 66, flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 11 },
  iconSlot: { width: 28, alignItems: 'center' },
  rowDivider: { borderBottomColor: '#D9CDB5', borderBottomWidth: StyleSheet.hairlineWidth },
  prompt: { flex: 1, minWidth: 0, color: '#173B2B' },
  compactWrap: { paddingHorizontal: 16, paddingVertical: 9, flexDirection: 'row', flexWrap: 'wrap', gap: 8, backgroundColor: '#F8F5EC' },
  compactChip: { flexGrow: 1, flexBasis: '45%', minHeight: 48, paddingHorizontal: 12, paddingVertical: 8, borderRadius: 12, borderWidth: 1, borderColor: '#165B33', backgroundColor: '#FFFDF8', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 },
  compactText: { flexShrink: 1, color: '#173B2B', textAlign: 'center' },
});
