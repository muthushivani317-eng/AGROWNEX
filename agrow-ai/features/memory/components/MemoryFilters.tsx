import { Search } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { ScrollView, View } from 'react-native';

import { AgChip, AgInput, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import { FILTERABLE_SOURCES, IMPORTANCE_LABEL_KEY, SOURCE_LABEL_KEY } from '../constants';
import type { MemoryHistoryFilter, MemoryImportance } from '../types';

const IMPORTANCES: MemoryImportance[] = ['critical', 'high', 'medium', 'low'];

/**
 * Timeline filters — by source module and importance — plus a text search. Filters only
 * narrow real memories; they never generate data.
 */
export function MemoryFilters({
  filter,
  onChange,
}: {
  filter: MemoryHistoryFilter;
  onChange: (next: MemoryHistoryFilter) => void;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();

  const setSource = (source?: string) =>
    onChange({ ...filter, sourceModule: filter.sourceModule === source ? undefined : source });
  const setImportance = (importance?: MemoryImportance) =>
    onChange({ ...filter, importance: filter.importance === importance ? undefined : importance });

  return (
    <View className="gap-2">
      <AgInput
        placeholder={t('memory.searchPlaceholder')}
        value={filter.q ?? ''}
        onChangeText={(q) => onChange({ ...filter, q: q || undefined })}
        leftAccessory={<Search size={18} color={colors.textMuted} />}
        autoCorrect={false}
      />

      <AgText variant="caption" color="muted">
        {t('memory.filterBySource')}
      </AgText>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerClassName="gap-2 pr-4">
        <AgChip
          label={t('memory.filterAll')}
          selected={!filter.sourceModule}
          onPress={() => setSource(undefined)}
        />
        {FILTERABLE_SOURCES.map((source) => (
          <AgChip
            key={source}
            label={t(SOURCE_LABEL_KEY[source] ?? source)}
            selected={filter.sourceModule === source}
            onPress={() => setSource(source)}
          />
        ))}
      </ScrollView>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerClassName="gap-2 pr-4">
        <AgChip
          label={t('memory.filterAll')}
          selected={!filter.importance}
          onPress={() => setImportance(undefined)}
        />
        {IMPORTANCES.map((importance) => (
          <AgChip
            key={importance}
            label={t(IMPORTANCE_LABEL_KEY[importance])}
            selected={filter.importance === importance}
            onPress={() => setImportance(importance)}
          />
        ))}
      </ScrollView>
    </View>
  );
}
