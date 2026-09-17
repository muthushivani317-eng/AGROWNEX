import type { LucideIcon } from "lucide-react-native";
import type { ReactElement } from "react";
import {
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  View,
} from "react-native";

import { AgErrorState, AgSkeleton, AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import type { ProduceOffer } from "../types";
import { PRODUCE_COLORS as C } from "../produceTheme";
import { ProduceCard } from "./ProduceCard";

/** Shared list rendering for the produce screens (list / upcoming / history). */
export function ProduceListView({
  items,
  isLoading,
  isError,
  isRefetching,
  onRefresh,
  onRetry,
  header,
  emptyIcon,
  emptyTitle,
  emptyMessage,
  emptyActionLabel,
  onEmptyAction,
}: {
  items: ProduceOffer[];
  isLoading: boolean;
  isError: boolean;
  isRefetching: boolean;
  onRefresh: () => void;
  onRetry: () => void;
  header?: ReactElement;
  emptyIcon: LucideIcon;
  emptyTitle: string;
  emptyMessage: string;
  emptyActionLabel?: string;
  onEmptyAction?: () => void;
}) {
  const { colors } = useAppTheme();
  const EmptyIcon = emptyIcon;
  return (
    <FlatList
      data={items}
      keyExtractor={(item) => item.id}
      ListHeaderComponent={header}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={isRefetching}
          onRefresh={onRefresh}
          tintColor={colors.primary}
        />
      }
      renderItem={({ item }) => <ProduceCard offer={item} />}
      ListEmptyComponent={
        isLoading ? (
          <ProduceSkeleton />
        ) : isError ? (
          <AgErrorState onRetry={onRetry} />
        ) : (
          <View style={styles.emptyCard}>
            <View style={styles.emptyIcon}>
              <EmptyIcon size={42} color={C.green} />
            </View>
            <AgText variant="headingS" weight="bold" center style={styles.ink}>
              {emptyTitle}
            </AgText>
            <AgText center style={styles.muted}>
              {emptyMessage}
            </AgText>
            {emptyActionLabel && onEmptyAction ? (
              <Pressable
                onPress={onEmptyAction}
                accessibilityRole="button"
                testID="produce-empty-add-listing-button"
                style={styles.emptyAction}
              >
                <AgText weight="bold" style={styles.actionText}>
                  {emptyActionLabel}
                </AgText>
              </Pressable>
            ) : null}
          </View>
        )
      }
    />
  );
}

const styles = StyleSheet.create({
  content: { paddingBottom: 112, gap: 14 },
  emptyCard: {
    marginTop: 20,
    alignItems: "center",
    gap: 12,
    padding: 28,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.paper,
  },
  emptyIcon: {
    width: 104,
    height: 104,
    borderRadius: 52,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: C.greenSoft,
  },
  ink: { color: C.ink },
  muted: { color: C.muted },
  emptyAction: {
    minHeight: 52,
    minWidth: 190,
    marginTop: 8,
    paddingHorizontal: 20,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: C.green,
  },
  actionText: { color: C.paper },
});

function ProduceSkeleton() {
  return (
    <View className="mt-2 gap-3">
      {[0, 1, 2, 3].map((i) => (
        <AgSkeleton key={i} className="h-28 w-full rounded-card" />
      ))}
    </View>
  );
}
