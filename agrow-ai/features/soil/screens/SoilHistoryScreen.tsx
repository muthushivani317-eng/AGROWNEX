import { History } from "lucide-react-native";
import { useRouter } from "expo-router";
import { useTranslation } from "react-i18next";
import { FlatList, RefreshControl, StyleSheet, View } from "react-native";

import {
  AgBadge,
  AgEmptyState,
  AgErrorState,
  AgOfflineBanner,
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import { SoilFeatureHeader } from "../components/SoilFeatureHeader";
import { SOURCE_LABEL_KEY } from "../constants";
import { SOIL_SHADOW, SOIL_UI } from "../design";
import { useSoilHistory } from "../hooks/useSoil";
import type { SoilHistoryEntry, SoilSource } from "../types";

/** The farm's soil value trend over time (one row per report). */
export function SoilHistoryScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const query = useSoilHistory(farmId);
  const items = query.data?.items ?? [];

  return (
    <AgScreen padded={false} backgroundColor={SOIL_UI.canvas}>
      <AgOfflineBanner />
      <View style={styles.screen}>
        <FlatList
          data={items}
          keyExtractor={(item) => item.id}
          ListHeaderComponent={
            <View style={styles.headerSpace}>
              <SoilFeatureHeader
                title={t("soil.historyTitle")}
                onBack={() => router.back()}
              />
            </View>
          }
          contentContainerStyle={styles.content}
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
              <View style={styles.loadingList}>
                {[0, 1, 2].map((i) => (
                  <AgSkeleton key={i} className="h-20 w-full rounded-card" />
                ))}
              </View>
            ) : query.isError ? (
              <AgErrorState light onRetry={() => void query.refetch()} />
            ) : (
              <AgEmptyState
                light
                icon={History}
                title={t("soil.historyEmptyTitle")}
                message={t("soil.historyEmptyMessage")}
              />
            )
          }
        />
      </View>
    </AgScreen>
  );
}

function HistoryRow({ entry }: { entry: SoilHistoryEntry }) {
  const { t } = useTranslation();
  const metric = (label: string, value: number | null) =>
    value === null ? null : (
      <View style={styles.metric}>
        <AgText variant="caption" style={styles.mutedText}>
          {t(label)}
        </AgText>
        <AgText variant="bodySmall" weight="semibold" style={styles.primaryText}>
          {value}
        </AgText>
      </View>
    );

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <AgText variant="bodySmall" weight="semibold" style={styles.primaryText}>
          {entry.testDate ?? entry.recordedAt.slice(0, 10)}
        </AgText>
        <AgBadge
          label={t(
            SOURCE_LABEL_KEY[entry.source as SoilSource] ?? "soil.sourceSelf",
          )}
          tone="info"
        />
      </View>
      <View style={styles.metrics}>
        {metric("soil.paramPh", entry.ph)}
        {metric("soil.paramOrganicCarbon", entry.organicCarbon)}
        {metric("soil.paramNitrogen", entry.nitrogen)}
        {metric("soil.paramPhosphorus", entry.phosphorus)}
        {metric("soil.paramPotassium", entry.potassium)}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, paddingHorizontal: 20 },
  content: { gap: 12, paddingBottom: 112 },
  headerSpace: { paddingBottom: 4 },
  loadingList: { marginTop: 8, gap: 12 },
  primaryText: { color: SOIL_UI.text },
  mutedText: { color: SOIL_UI.muted },
  card: {
    padding: 16,
    gap: 14,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: SOIL_UI.border,
    backgroundColor: SOIL_UI.surface,
    ...SOIL_SHADOW,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  metrics: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  metric: {
    minWidth: 88,
    flexGrow: 1,
    padding: 10,
    borderRadius: 14,
    backgroundColor: SOIL_UI.surfaceSoft,
    alignItems: "flex-start",
    gap: 3,
  },
});
