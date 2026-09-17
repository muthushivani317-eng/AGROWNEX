import { useRouter } from "expo-router";
import {
  ChevronRight,
  ClipboardList,
  FileUp,
  History,
  Lightbulb,
  Sprout,
} from "lucide-react-native";
import { useTranslation } from "react-i18next";
import {
  RefreshControl,
  ScrollView,
  StyleSheet,
  useWindowDimensions,
  View,
} from "react-native";

import {
  AgButton,
  AgEmptyState,
  AgErrorState,
  AgOfflineBanner,
  AgPressable,
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";
import { useSelectedFarm } from "@/features/weather";
import { FarmSelector } from "@/features/weather/components/FarmSelector";
import { useAppTheme } from "@/hooks/useAppTheme";

import { SoilHealthCard } from "../components/SoilHealthCard";
import { SoilFeatureHeader } from "../components/SoilFeatureHeader";
import { SoilRecommendationCard } from "../components/SoilRecommendationCard";
import { SOIL_SHADOW, SOIL_UI } from "../design";
import { useSoilDashboard } from "../hooks/useSoil";
import { useSoilSync } from "../hooks/useSoilSync";

/** Soil dashboard: health card, generic advice and clear 'no data' guidance. */
export function SoilDashboardScreen() {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const router = useRouter();
  const { width } = useWindowDimensions();
  useSoilSync();

  const {
    farms,
    selected,
    select,
    isLoading: farmsLoading,
    isError: farmsError,
    refetch: refetchFarms,
  } = useSelectedFarm();
  const farmId = selected?.id;
  const query = useSoilDashboard(farmId);
  const data = query.data;
  const compact = width < 390;

  if (farmsError) {
    return (
      <AgScreen backgroundColor={SOIL_UI.canvas}>
        <SoilFeatureHeader title={t("soil.title")} subtitle={t("soil.subtitle")} onBack={() => router.back()} />
        <AgErrorState light onRetry={() => void refetchFarms()} />
      </AgScreen>
    );
  }

  if (!farmsLoading && farms.length === 0) {
    return (
      <AgScreen backgroundColor={SOIL_UI.canvas}>
        <SoilFeatureHeader
          title={t("soil.title")}
          subtitle={t("soil.subtitle")}
          onBack={() => router.back()}
        />
        <View style={styles.noFarmState}>
          <AgEmptyState
            light
            icon={Sprout}
            title={t("soil.noFarmTitle")}
            message={t("soil.noFarmMessage")}
          />
          <AgButton
            title={t("home.actionAddFarm")}
            onPress={() => router.push("/farm/new")}
          />
        </View>
      </AgScreen>
    );
  }

  const topRecs = (data?.recommendations ?? []).slice(0, 3);
  const openUpload = () =>
    router.push({ pathname: "/soil/upload", params: { farmId } });
  const openHistory = () =>
    router.push({ pathname: "/soil/history", params: { farmId } });
  const openRecommendations = () =>
    router.push({ pathname: "/soil/recommendations", params: { farmId } });
  const openScan = () => router.push(`/soil/scan?farmId=${farmId}` as never);

  return (
    <AgScreen padded={false} backgroundColor={SOIL_UI.canvas}>
      <AgOfflineBanner />
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={query.isRefetching}
            onRefresh={() => {
              void refetchFarms();
              if (farmId) void query.refetch();
            }}
            tintColor={colors.primary}
          />
        }
      >
        <SoilFeatureHeader
          title={t("soil.title")}
          subtitle={t("soil.subtitle")}
          onBack={() => router.back()}
        />

        <FarmSelector
          farms={farms}
          selectedId={selected?.id ?? null}
          onSelect={select}
          light
        />

        {farmsLoading || query.isLoading ? (
          <View style={styles.skeletons}>
            {[0, 1, 2].map((i) => (
              <AgSkeleton key={i} style={{ height: 112, width: "100%", borderRadius: 18 }} />
            ))}
          </View>
        ) : query.isError ? (
          <AgErrorState light onRetry={() => void query.refetch()} />
        ) : (
          <>
            {data && !data.hasData ? (
              <AgPressable
                onPress={openUpload}
                accessibilityRole="button"
                accessibilityLabel={t("soil.upload")}
                style={[
                  styles.noDataCard,
                  {
                    backgroundColor: SOIL_UI.surface,
                    borderColor: SOIL_UI.border,
                  },
                ]}
              >
                <View
                  style={[
                    styles.noDataLayout,
                    compact && styles.noDataLayoutCompact,
                  ]}
                >
                  <View style={[styles.illustration, { backgroundColor: SOIL_UI.surfaceSoft }]}>
                    <ClipboardList size={72} color={SOIL_UI.muted} />
                    <View style={[styles.illustrationSprout, { backgroundColor: SOIL_UI.greenSoft }]}>
                      <Sprout size={38} color={SOIL_UI.green} />
                    </View>
                  </View>
                  <View style={styles.noDataCopy}>
                    <AgText variant="headingM" weight="bold" style={styles.fixedText}>
                      {t("soil.noDataTitle")}
                    </AgText>
                    <AgText variant="body" style={styles.fixedMuted}>
                      {t("soil.noDataMessage")}
                    </AgText>
                    <View
                      style={[
                        styles.primaryAction,
                        { backgroundColor: SOIL_UI.green },
                      ]}
                    >
                      <FileUp size={22} color={SOIL_UI.white} />
                      <AgText
                        variant="bodyLarge"
                        weight="bold"
                        style={styles.onGreenText}
                      >
                        {t("soil.uploadSoilTest")}
                      </AgText>
                    </View>
                  </View>
                </View>
              </AgPressable>
            ) : null}

            <SoilHealthCard
              profile={data?.profile ?? null}
              assessment={data?.assessment ?? null}
              evidence={data?.indicatorEvidence ?? []}
            />
            <AgButton
              light
              title={t("soil.scanTitle")}
              onPress={openScan}
              disabled={!farmId}
            />

            {data?.profile?.lastTestDate ? (
              <AgText variant="caption" style={styles.fixedMuted}>
                {t("soil.lastTested", { date: data.profile.lastTestDate })} ·{" "}
                {t("soil.confidence", { value: data.profile.confidence })}
              </AgText>
            ) : null}

            <View
              style={[
                styles.recommendationsCard,
                {
                  backgroundColor: SOIL_UI.surface,
                  borderColor: SOIL_UI.border,
                },
              ]}
            >
              <View style={styles.sectionHeader}>
                <View style={styles.sectionTitle}>
                  <Lightbulb size={24} color={SOIL_UI.green} />
                  <AgText variant="headingS" weight="bold" style={styles.fixedText}>
                    {t("soil.recommendations")}
                  </AgText>
                </View>
                {topRecs.length > 0 ? (
                  <AgPressable
                    onPress={openRecommendations}
                    accessibilityRole="button"
                    accessibilityLabel={t("soil.viewAll")}
                    style={styles.viewAll}
                  >
                    <AgText
                      variant="bodySmall"
                      weight="semibold"
                      style={styles.greenText}
                    >
                      {t("soil.viewAll")}
                    </AgText>
                    <ChevronRight size={18} color={SOIL_UI.green} />
                  </AgPressable>
                ) : null}
              </View>

              {topRecs.length > 0 ? (
                <View style={styles.recommendationList}>
                  {topRecs.map((rec) => (
                    <SoilRecommendationCard key={rec.code} rec={rec} />
                  ))}
                </View>
              ) : (
                <AgPressable
                  onPress={openUpload}
                  accessibilityRole="button"
                  style={[
                    styles.getTestCard,
                    {
                      backgroundColor: SOIL_UI.surfaceSoft,
                      borderColor: SOIL_UI.border,
                    },
                  ]}
                >
                  <View
                    style={[
                      styles.getTestIcon,
                      { backgroundColor: SOIL_UI.greenSoft },
                    ]}
                  >
                    <Sprout size={30} color={SOIL_UI.green} />
                  </View>
                  <View style={styles.getTestCopy}>
                    <AgText variant="bodyLarge" weight="semibold" style={styles.fixedText}>
                      {t("soil.getSoilTestTitle")}
                    </AgText>
                    <AgText variant="bodySmall" style={styles.fixedMuted}>
                      {t("soil.getSoilTestMessage")}
                    </AgText>
                  </View>
                  <ChevronRight size={24} color={SOIL_UI.muted} />
                </AgPressable>
              )}

              <AgPressable
                onPress={openUpload}
                accessibilityRole="button"
                style={[
                  styles.uploadButton,
                  { backgroundColor: SOIL_UI.green },
                ]}
              >
                <View style={styles.buttonContent}>
                  <FileUp size={22} color={SOIL_UI.white} />
                  <AgText variant="bodyLarge" weight="bold" style={styles.onGreenText}>
                    {t("soil.upload")}
                  </AgText>
                </View>
              </AgPressable>
              <AgPressable
                onPress={openHistory}
                accessibilityRole="button"
                style={[styles.historyButton, { borderColor: SOIL_UI.green }]}
              >
                <View style={styles.buttonContent}>
                  <History size={22} color={SOIL_UI.green} />
                  <AgText variant="bodyLarge" weight="semibold" style={styles.greenText}>
                    {t("soil.history")}
                  </AgText>
                </View>
              </AgPressable>
            </View>
          </>
        )}
      </ScrollView>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1, paddingHorizontal: 20 },
  content: { gap: 18, paddingBottom: 112 },
  noFarmState: { marginTop: 36, gap: 18 },
  skeletons: { gap: 12 },
  noDataCard: { borderWidth: 1, borderRadius: 24, padding: 22 },
  noDataLayout: { flexDirection: "row", alignItems: "center", gap: 22 },
  noDataLayoutCompact: { flexDirection: "column" },
  illustration: {
    width: 140,
    height: 166,
    borderRadius: 70,
    alignItems: "center",
    justifyContent: "center",
  },
  illustrationSprout: {
    position: "absolute",
    right: 8,
    bottom: 12,
    width: 54,
    height: 54,
    borderRadius: 27,
    alignItems: "center",
    justifyContent: "center",
  },
  noDataCopy: { flex: 1, gap: 10 },
  primaryAction: {
    minHeight: 58,
    borderRadius: 18,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    marginTop: 6,
    paddingHorizontal: 14,
  },
  recommendationsCard: {
    borderWidth: 1,
    borderRadius: 24,
    padding: 18,
    gap: 12,
    ...SOIL_SHADOW,
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  sectionTitle: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    flex: 1,
  },
  viewAll: { minHeight: 44, flexDirection: "row", alignItems: "center" },
  recommendationList: { gap: 10 },
  getTestCard: {
    minHeight: 112,
    borderWidth: 1,
    borderRadius: 18,
    padding: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
  },
  getTestIcon: {
    width: 60,
    height: 60,
    borderRadius: 30,
    alignItems: "center",
    justifyContent: "center",
  },
  getTestCopy: { flex: 1, gap: 4 },
  uploadButton: { minHeight: 58, borderRadius: 16, justifyContent: "center" },
  historyButton: {
    minHeight: 58,
    borderRadius: 16,
    borderWidth: 1,
    justifyContent: "center",
  },
  buttonContent: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },
  fixedText: { color: SOIL_UI.text },
  fixedMuted: { color: SOIL_UI.muted },
  greenText: { color: SOIL_UI.green },
  onGreenText: { color: SOIL_UI.white },
});
