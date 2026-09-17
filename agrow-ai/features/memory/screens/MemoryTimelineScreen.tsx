import { History } from 'lucide-react-native';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { RefreshControl, ScrollView, View } from 'react-native';

import {
  AgEmptyState,
  AgErrorState,
  AgScreen,
  AgSkeleton,
} from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import { MemoryBackHeader } from '../components/MemoryBackHeader';
import { MemoryFilters } from '../components/MemoryFilters';
import { MemoryTimeline } from '../components/MemoryTimeline';
import { useMemoryHistory } from '../hooks/useMemory';
import { useMemorySync } from '../hooks/useMemorySync';
import type { MemoryHistoryFilter } from '../types';

/**
 * The full memory timeline for a farm (newest first), filterable by source module and
 * importance and searchable. Every entry links back to the module that produced it.
 */
export function MemoryTimelineScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const [filter, setFilter] = useState<MemoryHistoryFilter>({});
  useMemorySync();

  const query = useMemoryHistory(farmId, filter);
  const items = query.data?.items ?? [];

  return (
    <AgScreen padded={false}>
      <ScrollView
        className="flex-1 px-5"
        contentContainerClassName="pb-24 gap-3"
        keyboardShouldPersistTaps="handled"
        refreshControl={
          <RefreshControl
            refreshing={query.isRefetching}
            onRefresh={() => void query.refetch()}
            tintColor={colors.primary}
          />
        }
      >
        <MemoryBackHeader title={t('memory.timelineTitle')} />
        <MemoryFilters filter={filter} onChange={setFilter} />

        {query.isLoading ? (
          <View className="gap-3">
            {[0, 1, 2, 3].map((i) => (
              <AgSkeleton key={i} className="h-24 w-full rounded-card" />
            ))}
          </View>
        ) : query.isError ? (
          <AgErrorState onRetry={() => void query.refetch()} />
        ) : items.length === 0 ? (
          <AgEmptyState
            icon={History}
            title={t('memory.timelineEmptyTitle')}
            message={t('memory.timelineEmptyMessage')}
          />
        ) : (
          <MemoryTimeline memories={items} />
        )}
      </ScrollView>
    </AgScreen>
  );
}
