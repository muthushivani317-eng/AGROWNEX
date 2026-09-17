import { CalendarRange } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { RefreshControl, ScrollView, View } from 'react-native';

import {
  AgEmptyState,
  AgErrorState,
  AgScreen,
  AgSkeleton,
  AgText,
} from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import { MemoryBackHeader } from '../components/MemoryBackHeader';
import { MemorySummaryCard } from '../components/MemorySummaryCard';
import { useMemorySummary } from '../hooks/useMemory';

/**
 * Generated season and year summaries for a farm — deterministic recaps derived from the
 * real memory timeline (counts, dominant activity, top importance). Never fabricated.
 */
export function MemorySummaryScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const query = useMemorySummary(farmId);
  const bundle = query.data;
  const isEmpty = bundle && bundle.seasons.length === 0 && bundle.years.length === 0;

  return (
    <AgScreen padded={false}>
      <ScrollView
        className="flex-1 px-5"
        contentContainerClassName="pb-24 gap-3"
        refreshControl={
          <RefreshControl
            refreshing={query.isRefetching}
            onRefresh={() => void query.refetch()}
            tintColor={colors.primary}
          />
        }
      >
        <MemoryBackHeader title={t('memory.summaryTitle')} />

        {query.isLoading ? (
          <View className="gap-3">
            {[0, 1, 2].map((i) => (
              <AgSkeleton key={i} className="h-24 w-full rounded-card" />
            ))}
          </View>
        ) : query.isError ? (
          <AgErrorState onRetry={() => void query.refetch()} />
        ) : isEmpty ? (
          <AgEmptyState
            icon={CalendarRange}
            title={t('memory.summaryEmptyTitle')}
            message={t('memory.summaryEmptyMessage')}
          />
        ) : (
          <>
            {bundle!.seasons.length > 0 ? (
              <View className="gap-2">
                <AgText variant="label" weight="semibold" color="muted">
                  {t('memory.bySeason')}
                </AgText>
                {bundle!.seasons.map((s) => (
                  <MemorySummaryCard key={s.periodKey} summary={s} />
                ))}
              </View>
            ) : null}

            {bundle!.years.length > 0 ? (
              <View className="mt-2 gap-2">
                <AgText variant="label" weight="semibold" color="muted">
                  {t('memory.byYear')}
                </AgText>
                {bundle!.years.map((y) => (
                  <MemorySummaryCard key={y.periodKey} summary={y} />
                ))}
              </View>
            ) : null}
          </>
        )}
      </ScrollView>
    </AgScreen>
  );
}
