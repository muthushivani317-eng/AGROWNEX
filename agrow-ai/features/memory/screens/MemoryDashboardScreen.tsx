import { useRouter } from "expo-router";
import {
  ArrowLeft,
  Brain,
  CalendarRange,
  FlaskConical,
  History,
  Plus,
  RefreshCw,
} from "lucide-react-native";
import { useTranslation } from "react-i18next";
import {
  Alert,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";

import {
  AgButton,
  AgErrorState,
  AgPressable,
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";
import { useSelectedFarm } from "@/features/weather";
import { FarmSelector } from "@/features/weather/components/FarmSelector";

import { MemorySummaryCard } from "../components/MemorySummaryCard";
import { MemoryTimeline } from "../components/MemoryTimeline";
import { useMemoryDashboard, useRebuildMemory } from "../hooks/useMemory";
import { useMemorySync } from "../hooks/useMemorySync";

const C = {
  background: "#FBF7EA",
  surface: "#FFFDF7",
  text: "#173F30",
  muted: "#5F6D65",
  green: "#17633B",
  greenStrong: "#124B30",
  soft: "#E8F3E5",
  border: "#D8D2C2",
  amber: "#A96705",
  amberSoft: "#FFF4D8",
} as const;

export function MemoryDashboardScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  useMemorySync();
  const {
    farms,
    selected,
    select,
    isLoading: farmsLoading,
  } = useSelectedFarm();
  const farmId = selected?.id;
  const query = useMemoryDashboard(farmId);
  const rebuild = useRebuildMemory();
  const data = query.data;
  const memories = data?.recent ?? [];
  const sample = memories.some((memory) => memory.isSample);

  const onRebuild = () => {
    if (!farmId) return;
    rebuild.mutate(
      { farmId },
      {
        onSuccess: (result) =>
          result.offline
            ? Alert.alert(t("memory.queuedOffline"))
            : void query.refetch(),
        onError: () => Alert.alert(t("memory.rebuildFailed")),
      },
    );
  };

  const backButton = (
    <AgPressable
      onPress={() => router.back()}
      accessibilityRole="button"
      accessibilityLabel={t("common.back")}
      hitSlop={8}
      style={styles.backButton}
    >
      <ArrowLeft size={26} color={C.greenStrong} />
    </AgPressable>
  );

  if (!farmsLoading && farms.length === 0) {
    return (
      <AgScreen
        backgroundColor={C.background}
        contentContainerStyle={styles.emptyScreen}
      >
        {backButton}
        <View style={styles.emptyCard}>
          <View style={styles.largeIcon}>
            <Brain size={32} color={C.green} />
          </View>
          <AgText variant="headingL" weight="bold" style={styles.title}>
            {t("memory.title")}
          </AgText>
          <AgText style={styles.emptyText}>{t("memory.noFarmTitle")}</AgText>
          <AgButton
            title={t("home.actionAddFarm")}
            leftIcon={<Plus size={19} color="#FFFFFF" />}
            onPress={() => router.push("/farm/new")}
          />
        </View>
      </AgScreen>
    );
  }

  return (
    <AgScreen padded={false} backgroundColor={C.background}>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={query.isRefetching}
            onRefresh={() => void query.refetch()}
            tintColor={C.green}
          />
        }
      >
        <View style={styles.topBar}>
          {backButton}
          <View style={styles.brandIcon}>
            <Brain size={25} color={C.green} />
          </View>
        </View>

        <View style={styles.hero}>
          <AgText variant="headingL" weight="bold" style={styles.title}>
            {t("memory.title")}
          </AgText>
          <AgText style={styles.subtitle}>{t("memory.subtitle")}</AgText>
        </View>

        {farmsLoading ? (
          <AgSkeleton
            testID="farm-memory-farm-loading"
            style={styles.farmSkeleton}
          />
        ) : (
          <FarmSelector
            farms={farms}
            selectedId={selected?.id ?? null}
            onSelect={select}
            light
          />
        )}

        {farmsLoading || query.isLoading ? (
          <View style={styles.loadingList}>
            {[0, 1, 2].map((item) => (
              <AgSkeleton key={item} style={styles.skeleton} />
            ))}
          </View>
        ) : query.isError ? (
          <AgErrorState onRetry={() => void query.refetch()} />
        ) : (
          <>
            {sample ? (
              <View style={styles.sampleCard}>
                <FlaskConical size={20} color={C.amber} />
                <AgText style={styles.sampleText}>
                  {t("memory.sampleNotice")}
                </AgText>
              </View>
            ) : null}

            {data?.hasData ? (
              <>
                {data.latestSummary ? (
                  <MemorySummaryCard summary={data.latestSummary} />
                ) : null}
                <View style={styles.sectionHeader}>
                  <View>
                    <AgText
                      variant="headingS"
                      weight="bold"
                      style={styles.sectionTitle}
                    >
                      {t("memory.recent")}
                    </AgText>
                    <AgText style={styles.sectionHint}>
                      {t("memory.totalCount", { n: data.total })}
                    </AgText>
                  </View>
                  <View style={styles.countBadge}>
                    <AgText style={styles.countText} weight="bold">
                      {data.total}
                    </AgText>
                  </View>
                </View>
                <MemoryTimeline memories={memories} />
              </>
            ) : (
              <View style={styles.emptyCard}>
                <View style={styles.largeIcon}>
                  <Brain size={30} color={C.green} />
                </View>
                <AgText variant="headingS" weight="bold" style={styles.title}>
                  {t("memory.emptyTitle")}
                </AgText>
                <AgText style={styles.emptyText}>
                  {t(data?.messageCode ?? "memory.status.no_memory")}
                </AgText>
              </View>
            )}

            <View style={styles.actions}>
              <AgButton
                variant="primary"
                title={t("memory.rebuild")}
                leftIcon={<RefreshCw size={18} color="#FFFFFF" />}
                onPress={onRebuild}
                loading={rebuild.isPending}
              />
              <View style={styles.secondaryActions}>
                <View style={styles.secondaryButton}>
                  <AgButton
                    variant="outline"
                    title={t("memory.timeline")}
                    leftIcon={<History size={18} color={C.green} />}
                    onPress={() =>
                      router.push({
                        pathname: "/memory/history",
                        params: { farmId },
                      })
                    }
                  />
                </View>
                <View style={styles.secondaryButton}>
                  <AgButton
                    variant="outline"
                    title={t("memory.summaries")}
                    leftIcon={<CalendarRange size={18} color={C.green} />}
                    onPress={() =>
                      router.push({
                        pathname: "/memory/summary",
                        params: { farmId },
                      })
                    }
                  />
                </View>
              </View>
            </View>
          </>
        )}
      </ScrollView>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: C.background },
  content: {
    gap: 18,
    paddingHorizontal: 20,
    paddingTop: 14,
    paddingBottom: 110,
  },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  backButton: {
    width: 48,
    height: 48,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: C.surface,
    borderWidth: 1,
    borderColor: C.border,
  },
  brandIcon: {
    width: 48,
    height: 48,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: C.soft,
  },
  hero: { gap: 7 },
  title: { color: C.greenStrong },
  subtitle: { color: C.muted, fontSize: 17, lineHeight: 25 },
  loadingList: { gap: 12 },
  skeleton: { width: "100%", height: 140, borderRadius: 22 },
  farmSkeleton: { width: "100%", height: 64, borderRadius: 18 },
  sampleCard: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
    padding: 15,
    borderRadius: 18,
    backgroundColor: C.amberSoft,
    borderWidth: 1,
    borderColor: "#E5C77A",
  },
  sampleText: { flex: 1, color: "#654B20", lineHeight: 21 },
  sectionHeader: {
    marginTop: 4,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  sectionTitle: { color: C.text },
  sectionHint: { color: C.muted, marginTop: 2 },
  countBadge: {
    minWidth: 42,
    height: 42,
    borderRadius: 21,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: C.soft,
  },
  countText: { color: C.green },
  emptyScreen: { gap: 18, backgroundColor: C.background },
  emptyCard: {
    alignItems: "center",
    gap: 12,
    padding: 24,
    borderRadius: 22,
    backgroundColor: C.surface,
    borderWidth: 1,
    borderColor: C.border,
  },
  largeIcon: {
    width: 64,
    height: 64,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: C.soft,
  },
  emptyText: { color: C.muted, textAlign: "center", lineHeight: 23 },
  actions: { gap: 10, marginTop: 4 },
  secondaryActions: { flexDirection: "row", gap: 10 },
  secondaryButton: { flex: 1 },
});
