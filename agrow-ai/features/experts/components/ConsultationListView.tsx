import { MessageSquareText } from 'lucide-react-native';
import type { ReactElement } from 'react';
import { FlatList, RefreshControl, View } from 'react-native';

import { AgEmptyState, AgErrorState, AgSkeleton } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import type { Consultation } from '../types';
import { ConsultationCard } from './ConsultationCard';

/** Shared list rendering for the consultation screens (loading/empty/error). */
export function ConsultationListView({
  items,
  isLoading,
  isError,
  isRefetching,
  onRefresh,
  onRetry,
  onPressItem,
  header,
  emptyTitle,
  emptyMessage,
}: {
  items: Consultation[];
  isLoading: boolean;
  isError: boolean;
  isRefetching: boolean;
  onRefresh: () => void;
  onRetry: () => void;
  onPressItem: (consultation: Consultation) => void;
  header?: ReactElement;
  emptyTitle: string;
  emptyMessage: string;
}) {
  const { colors } = useAppTheme();
  return (
    <FlatList
      data={items}
      keyExtractor={(item) => item.id}
      ListHeaderComponent={header}
      contentContainerClassName="pb-28 gap-3"
      refreshControl={
        <RefreshControl
          refreshing={isRefetching}
          onRefresh={onRefresh}
          tintColor={colors.primary}
        />
      }
      renderItem={({ item }) => (
        <ConsultationCard consultation={item} onPress={onPressItem} />
      )}
      ListEmptyComponent={
        isLoading ? (
          <ConsultationSkeleton />
        ) : isError ? (
          <AgErrorState onRetry={onRetry} />
        ) : (
          <AgEmptyState icon={MessageSquareText} title={emptyTitle} message={emptyMessage} />
        )
      }
    />
  );
}

function ConsultationSkeleton() {
  return (
    <View className="mt-2 gap-3">
      {[0, 1, 2, 3].map((i) => (
        <AgSkeleton key={i} className="h-28 w-full rounded-card" />
      ))}
    </View>
  );
}
