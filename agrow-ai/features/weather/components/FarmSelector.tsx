import { Check, ChevronDown, ChevronUp, MapPin } from 'lucide-react-native';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FlatList, Pressable, StyleSheet, View } from 'react-native';

import { AgText } from '@/components/ui';
import type { FarmSummary } from '@/features/farm';
import { useAppTheme } from '@/hooks/useAppTheme';

/** Existing farm switcher, presented as a compact selected-location control. */
export function FarmSelector({
  farms,
  selectedId,
  onSelect,
  light = false,
  compact = false,
}: {
  farms: FarmSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  light?: boolean;
  compact?: boolean;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const [expanded, setExpanded] = useState(false);
  const selected = farms.find((farm) => farm.id === selectedId) ?? farms[0] ?? null;
  const canSwitch = farms.length > 1;
  const Chevron = expanded ? ChevronUp : ChevronDown;

  if (!selected) return null;

  return (
    <View style={styles.wrapper}>
      <Pressable
        testID="weather-farm-selector"
        accessibilityRole="button"
        accessibilityLabel={t('weather.selectedFarm', { name: selected.name })}
        accessibilityState={{ expanded, disabled: !canSwitch }}
        disabled={!canSwitch}
        onPress={() => setExpanded((value) => !value)}
        style={[
          styles.selectedCard,
          compact && styles.compactSelectedCard,
          {
            backgroundColor: light ? '#FFFDF8' : colors.card,
            borderColor: light ? '#DED9CA' : colors.border,
          },
        ]}
      >
        <View style={[styles.locationIcon, light && styles.lightIcon]}>
          <MapPin size={20} color={colors.primary} />
        </View>
        <View style={[styles.selectedCopy, compact && styles.compactSelectedCopy]}>
          {compact ? (
            <AgText variant="bodySmall" weight="medium" numberOfLines={1} style={styles.lightMutedText}>
              {t('farm.location')}
            </AgText>
          ) : null}
          {compact ? <View style={styles.compactDivider} /> : null}
          <AgText variant={compact ? 'body' : 'bodyLarge'} weight="semibold" style={light ? styles.lightText : undefined} numberOfLines={1}>
            {selected.name}
          </AgText>
        </View>
        <View style={[styles.trailingIcon, light && styles.lightIcon]}>
          {canSwitch ? <Chevron size={20} color={colors.primary} /> : <Check size={18} color={colors.primary} />}
        </View>
      </Pressable>

      {expanded ? (
        <FlatList
          testID="weather-farm-options"
          horizontal
          data={farms}
          keyExtractor={(farm) => farm.id}
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.options}
          renderItem={({ item }) => {
            const active = item.id === selected.id;
            return (
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ selected: active }}
                onPress={() => {
                  onSelect(item.id);
                  setExpanded(false);
                }}
                style={[
                  styles.option,
                  {
                    backgroundColor: active ? `${colors.primary}20` : light ? '#FFFDF8' : colors.surface,
                    borderColor: active ? colors.primary : colors.border,
                  },
                ]}
              >
                <AgText
                  variant="bodySmall"
                  weight={active ? 'semibold' : 'regular'}
                  style={light ? (active ? styles.lightActiveText : styles.lightText) : undefined}
                >
                  {item.name}
                </AgText>
              </Pressable>
            );
          }}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { width: '100%' },
  selectedCard: {
    minHeight: 52,
    borderWidth: 1,
    borderRadius: 18,
    paddingHorizontal: 14,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  compactSelectedCard: { alignSelf: 'flex-start', maxWidth: '100%', minHeight: 54, paddingHorizontal: 10 },
  locationIcon: { width: 38, height: 38, borderRadius: 12, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  lightIcon: { backgroundColor: '#EDF6E9' },
  selectedCopy: { flex: 1, minWidth: 0, justifyContent: 'center' },
  compactSelectedCopy: { flexDirection: 'row', alignItems: 'center', gap: 9 },
  compactDivider: { width: 1, height: 20, backgroundColor: '#D8D5C9' },
  trailingIcon: { width: 34, height: 34, borderRadius: 17, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  lightText: { color: '#173B2B' },
  lightMutedText: { color: '#58685F' },
  lightActiveText: { color: '#176B3A' },
  pressed: { opacity: 0.76 },
  options: { gap: 8, paddingTop: 10, paddingBottom: 2 },
  option: { minHeight: 42, justifyContent: 'center', borderWidth: 1, borderRadius: 18, paddingHorizontal: 14 },
});
