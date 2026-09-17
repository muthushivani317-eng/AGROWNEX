import { BellOff } from 'lucide-react-native';
import type { ReactElement } from 'react';
import { ActivityIndicator, FlatList, RefreshControl, View } from 'react-native';

import { AgEmptyState, AgErrorState, AgSkeleton } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import type { NotificationItem } from '../types';
import { NotificationCard } from './NotificationCard';

/** Shared list rendering for the Notification Center (loading/empty/error). */
export function NotificationListView({
  items,
  isLoading,
  isError,
  isRefetching,
  isFetchingNextPage,
  onRefresh,
  onRetry,
  onEndReached,
  onPressItem,
  header,
  footer,
  emptyTitle,
  emptyMessage,
}: {
  items: NotificationItem[];
  isLoading: boolean;
  isError: boolean;
  isRefetching: boolean;
  isFetchingNextPage: boolean;
  onRefresh: () => void;
  onRetry: () => void;
  onEndReached: () => void;
  onPressItem: (item: NotificationItem) => void;
  header?: ReactElement;
  footer?: ReactElement;
  emptyTitle: string;
  emptyMessage: string;
}) {
  const { colors } = useAppTheme();
  return (
    <FlatList
      data={items}
      keyExtractor={(item) => item.id}
      ListHeaderComponent={header}
      contentContainerStyle={{ gap: 14, paddingBottom: 112 }}
      onEndReached={onEndReached}
      onEndReachedThreshold={0.5}
      refreshControl={
        <RefreshControl
          refreshing={isRefetching}
          onRefresh={onRefresh}
          tintColor={colors.primary}
        />
      }
      renderItem={({ item }) => <NotificationCard item={item} onPress={onPressItem} />}
      ListFooterComponent={
        <View>
        {isFetchingNextPage ? (
          <View className="items-center py-4">
            <ActivityIndicator color={colors.primary} />
          </View>
        ) : null}
        {footer}
        </View>
      }
      ListEmptyComponent={
        isLoading ? (
          <NotificationSkeleton />
        ) : isError ? (
          <AgErrorState onRetry={onRetry} />
        ) : (
          <AgEmptyState icon={BellOff} title={emptyTitle} message={emptyMessage} />
        )
      }
    />
  );
}

function NotificationSkeleton() {
  return (
    <View className="mt-2 gap-3">
      {[0, 1, 2, 3, 4].map((i) => (
        <AgSkeleton key={i} className="h-24 w-full rounded-card" />
      ))}
    </View>
  );
}
