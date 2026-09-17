import { ArrowLeft, History } from "lucide-react-native";
import { useRouter } from "expo-router";
import { useTranslation } from "react-i18next";
import { FlatList, RefreshControl, StyleSheet, View } from "react-native";

import {
  AgBadge,
  AgCard,
  AgEmptyState,
  AgErrorState,
  AgPressable,
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import { RiskTimeline } from "../components/RiskTimeline";
import { RISK_LABEL_KEY, RISK_TONE } from "../constants";
import { useIntelligenceHistory } from "../hooks/useIntelligence";
import type { IntelligenceHistoryEntry } from "../types";
import { INTELLIGENCE_COLORS as C } from "../design";

/** The farm's health / risk / confidence trend over time (one row per report). */
export function IntelligenceHistoryScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const router = useRouter();
  const query = useIntelligenceHistory(farmId);
  // A failed refresh must remain actionable even when React Query still owns
  // older rows. Do not let stale history hide the error state.
  const items = query.isError ? [] : (query.data?.items ?? []);

  return (
    <AgScreen padded={false} backgroundColor={C.background}>
      <View style={styles.container}>
        <FlatList
          data={items}
          keyExtractor={(item) => item.id}
          ListHeaderComponent={
            <View style={styles.headerArea}>
              <View style={styles.header}>
                <AgPressable
                  onPress={() => router.back()}
                  accessibilityRole="button"
                  accessibilityLabel={t("common.back")}
                  style={styles.back}
                >
                  <ArrowLeft size={23} color={C.ink} />
                </AgPressable>
                <View style={styles.historyIcon}>
                  <History size={22} color={C.primary} />
                </View>
                <View style={styles.headerCopy}>
                  <AgText variant="headingL" weight="bold" style={styles.ink}>
                    {t("intelligence.historyTitle")}
                  </AgText>
                </View>
              </View>
              {items.length >= 2 ? <RiskTimeline entries={items} /> : null}
            </View>
          }
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={query.isRefetching}
              onRefresh={() => void query.refetch()}
              tintColor={colors.primary}
            />
          }
          renderItem={({ item }) => <HistoryRow entry={item} />}
          ListEmptyComponent={
            query.isLoading ? (
              <View className="mt-2 gap-3">
                {[0, 1, 2].map((i) => (
                  <AgSkeleton key={i} className="h-20 w-full rounded-card" />
                ))}
              </View>
            ) : query.isError ? (
              <AgErrorState onRetry={() => void query.refetch()} />
            ) : (
              <AgEmptyState
                icon={History}
                title={t("intelligence.historyEmptyTitle")}
                message={t("intelligence.historyEmptyMessage")}
                light
              />
            )
          }
        />
      </View>
    </AgScreen>
  );
}

function HistoryRow({ entry }: { entry: IntelligenceHistoryEntry }) {
  const { t } = useTranslation();
  return (
    <AgCard style={styles.rowCard}>
      <View className="flex-row items-center justify-between">
        <AgText variant="bodySmall" weight="semibold" style={styles.ink}>
          {entry.recordedAt.slice(0, 10)}
        </AgText>
        <AgBadge
          label={t(RISK_LABEL_KEY[entry.overallRisk])}
          tone={RISK_TONE[entry.overallRisk]}
          light
        />
      </View>
      <View className="flex-row justify-between">
        <View className="items-center">
          <AgText variant="caption" color="muted">
            {t("intelligence.overallHealth")}
          </AgText>
          <AgText variant="bodySmall" weight="semibold">
            {entry.overallHealthScore ?? "—"}
          </AgText>
        </View>
        <View className="items-center">
          <AgText variant="caption" color="muted">
            {t("intelligence.confidence")}
          </AgText>
          <AgText variant="bodySmall" weight="semibold">
            {entry.confidence}%
          </AgText>
        </View>
      </View>
    </AgCard>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, paddingHorizontal: 20 },
  listContent: { paddingBottom: 96, gap: 12 },
  headerArea: { gap: 14, paddingTop: 14, paddingBottom: 4 },
  header: { flexDirection: "row", alignItems: "center", gap: 11 },
  back: {
    width: 44,
    height: 44,
    borderRadius: 15,
    backgroundColor: C.surface,
    borderWidth: 1,
    borderColor: C.border,
    alignItems: "center",
    justifyContent: "center",
  },
  historyIcon: {
    width: 46,
    height: 46,
    borderRadius: 16,
    backgroundColor: C.surfaceSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  headerCopy: { flex: 1 },
  ink: { color: C.ink },
  rowCard: { gap: 10, backgroundColor: C.surface, borderColor: C.border },
});
