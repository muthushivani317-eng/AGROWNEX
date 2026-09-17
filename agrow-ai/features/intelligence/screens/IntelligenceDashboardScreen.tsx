import { useRouter } from "expo-router";
import {
  ArrowLeft,
  Brain,
  FlaskConical,
  History,
  RefreshCw,
  ShieldCheck,
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
  AgCard,
  AgErrorState,
  AgPressable,
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";
import { useSelectedFarm } from "@/features/weather";
import { FarmSelector } from "@/features/weather/components/FarmSelector";
import { useAppTheme } from "@/hooks/useAppTheme";

import { HealthScoreCard } from "../components/HealthScoreCard";
import { PriorityIssueList } from "../components/PriorityIssueList";
import { RecommendationTimeline } from "../components/RecommendationTimeline";
import { RiskTimeline } from "../components/RiskTimeline";
import {
  useIntelligenceDashboard,
  useIntelligenceHistory,
  useRefreshIntelligence,
} from "../hooks/useIntelligence";
import { useIntelligenceSync } from "../hooks/useIntelligenceSync";
import { INTELLIGENCE_COLORS as C } from "../design";
import type { HealthModule, Recommendation } from "../types";

const MODULE_ROUTES: Record<HealthModule, string> = {
  disease: "/disease",
  nutrient: "/nutrient",
  soil: "/soil",
  satellite: "/satellite",
  weather: "/weather",
  growth: "/growth",
};

/**
 * Crop Intelligence dashboard: the aggregated farm-health score, overall risk,
 * confidence, priority issues, prioritized recommendations and the health trend — or an
 * honest "refresh to generate" state. The engine only aggregates existing modules; it
 * never fabricates missing data (docs/PRODUCT_RULES.md).
 */
export function IntelligenceDashboardScreen() {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const router = useRouter();
  useIntelligenceSync();

  const {
    farms,
    selected,
    select,
    isLoading: farmsLoading,
  } = useSelectedFarm();
  const farmId = selected?.id;
  const query = useIntelligenceDashboard(farmId);
  const historyQuery = useIntelligenceHistory(farmId);
  const refresh = useRefreshIntelligence();

  const data = query.data;
  const report = data?.report ?? null;

  const openModule = (module: HealthModule) =>
    router.push(MODULE_ROUTES[module] as never);
  const openRecommendation = (recommendation: Recommendation) => {
    const module = recommendation.modules.find(
      (item): item is HealthModule => item in MODULE_ROUTES,
    );
    if (module) return openModule(module);
    if (recommendation.category === "expert") return router.push("/experts" as never);
    if (recommendation.category === "task") return router.push("/calendar" as never);
    router.push("/farm" as never);
  };

  const onRefresh = () => {
    if (!farmId) return;
    refresh.mutate(
      { farmId },
      {
        onSuccess: (res) => {
          if (res.offline) Alert.alert(t("intelligence.queuedOffline"));
          else void query.refetch();
        },
        onError: () => Alert.alert(t("intelligence.refreshFailed")),
      },
    );
  };

  // Reached from Home's "Crop Intelligence" quick action with no back
  // affordance on either render path (2026-08 pre-release UI pass).
  const backButton = (
    <AgPressable
      onPress={() => router.back()}
      accessibilityRole="button"
      accessibilityLabel={t("common.back")}
      hitSlop={8}
      style={styles.backButton}
    >
      <ArrowLeft size={24} color={C.ink} />
    </AgPressable>
  );

  if (!farmsLoading && farms.length === 0) {
    return (
      <AgScreen backgroundColor={C.background}>
        <View style={styles.headerRow}>
          {backButton}
          <View style={styles.headerIcon}>
            <Brain size={24} color={C.primary} />
          </View>
          <AgText variant="headingL" weight="bold" style={styles.headerTitle}>
            {t("intelligence.title")}
          </AgText>
        </View>
        <View className="mt-8">
          <AgCard style={styles.emptyCard}>
            <Brain size={32} color={C.primary} />
            <AgText variant="body" weight="semibold" style={styles.inkText}>
              {t("intelligence.noFarmTitle")}
            </AgText>
            <AgButton
              className="mt-2"
              title={t("home.actionAddFarm")}
              onPress={() => router.push("/farm/new")}
            />
          </AgCard>
        </View>
      </AgScreen>
    );
  }

  return (
    <AgScreen padded={false} backgroundColor={C.background}>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={query.isRefetching}
            onRefresh={() => void query.refetch()}
            tintColor={colors.primary}
          />
        }
      >
        <View style={styles.headerRow}>
          {backButton}
          <View style={styles.headerIcon}>
            <Brain size={24} color={C.primary} />
          </View>
          <View style={styles.headerCopy}>
            <AgText variant="headingL" weight="bold" style={styles.headerTitle}>
              {t("intelligence.title")}
            </AgText>
          </View>
        </View>
        <AgText variant="bodySmall" style={styles.subtitle}>
          {t("intelligence.subtitle")}
        </AgText>

        {farmsLoading ? (
          <AgSkeleton
            testID="farm-health-farm-loading"
            className="h-16 w-full rounded-card"
          />
        ) : (
          <FarmSelector
            farms={farms}
            selectedId={selected?.id ?? null}
            onSelect={select}
            light
            compact
          />
        )}

        {farmsLoading || query.isLoading ? (
          <View className="gap-3">
            {[0, 1, 2].map((i) => (
              <AgSkeleton key={i} className="h-32 w-full rounded-card" />
            ))}
          </View>
        ) : query.isError ? (
          <AgErrorState onRetry={() => void query.refetch()} />
        ) : (
          <>
            {report?.isSample ? (
              <AgCard style={styles.noticeCard}>
                <FlaskConical size={18} color={C.info} />
                <AgText variant="caption" style={styles.noticeText}>
                  {t("intelligence.sampleNotice")}
                </AgText>
              </AgCard>
            ) : null}

            {report ? (
              <>
                <HealthScoreCard
                  health={report.health}
                  overall={report.overallHealthScore}
                  risk={report.overallRisk}
                  confidence={report.confidence}
                  onModulePress={openModule}
                />
                <PriorityIssueList issues={report.priorityIssues} />
                <RecommendationTimeline
                  recommendations={report.recommendations}
                  onRecommendationPress={openRecommendation}
                />
                {(historyQuery.data?.items?.length ?? 0) >= 2 ? (
                  <RiskTimeline entries={historyQuery.data!.items} />
                ) : null}
              </>
            ) : (
              <AgCard style={styles.emptyCard}>
                <Brain size={28} color={C.warning} />
                <AgText variant="body" weight="semibold" style={styles.inkText}>
                  {t("intelligence.emptyTitle")}
                </AgText>
                <AgText variant="bodySmall" style={styles.emptyText}>
                  {t(data?.messageCode ?? "intelligence.status.no_report")}
                </AgText>
              </AgCard>
            )}

            <View style={styles.buttonRow}>
              <AgButton
                className="flex-1"
                variant="primary"
                title={t("intelligence.refresh")}
                leftIcon={<RefreshCw size={18} color={colors.onPrimary} />}
                onPress={onRefresh}
                loading={refresh.isPending}
              />
              <AgButton
                className="flex-1"
                variant="outline"
                title={t("intelligence.history")}
                leftIcon={<History size={18} color={colors.primary} />}
                onPress={() =>
                  router.push({
                    pathname: "/intelligence/history",
                    params: { farmId },
                  })
                }
              />
            </View>
            <View style={styles.disclaimerCard}>
              <View style={styles.disclaimerIcon}>
                <ShieldCheck size={20} color={C.primary} />
              </View>
              <AgText variant="caption" style={styles.disclaimerText}>
                {t("intelligence.disclaimer")}
              </AgText>
            </View>
          </>
        )}
      </ScrollView>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1 },
  content: {
    paddingHorizontal: 20,
    paddingTop: 14,
    paddingBottom: 112,
    gap: 14,
  },
  headerRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  backButton: {
    width: 46,
    height: 46,
    borderRadius: 16,
    backgroundColor: C.surface,
    borderWidth: 1,
    borderColor: C.border,
    alignItems: "center",
    justifyContent: "center",
  },
  headerIcon: {
    width: 48,
    height: 48,
    borderRadius: 17,
    backgroundColor: C.surfaceSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  headerCopy: { flex: 1 },
  headerTitle: { color: C.ink, flexShrink: 1 },
  subtitle: { color: C.muted, lineHeight: 22, marginLeft: 58 },
  noticeCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: C.infoSoft,
    borderColor: "#B9D7DA",
  },
  noticeText: { color: C.muted, flex: 1 },
  emptyCard: {
    alignItems: "center",
    gap: 10,
    paddingVertical: 28,
    backgroundColor: C.surface,
    borderColor: C.border,
  },
  emptyText: { color: C.muted, textAlign: "center", paddingHorizontal: 16 },
  buttonRow: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginTop: 2 },
  disclaimerCard: {
    flexDirection: "row",
    gap: 11,
    alignItems: "center",
    backgroundColor: C.surfaceSoft,
    borderColor: C.border,
    borderWidth: 1,
    borderRadius: 18,
    padding: 14,
  },
  disclaimerIcon: {
    width: 38,
    height: 38,
    borderRadius: 13,
    backgroundColor: C.white,
    alignItems: "center",
    justifyContent: "center",
  },
  disclaimerText: { color: C.muted, flex: 1, lineHeight: 18 },
  inkText: { color: C.ink },
});
