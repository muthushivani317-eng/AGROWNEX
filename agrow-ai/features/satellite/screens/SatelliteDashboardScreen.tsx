import { useRouter } from "expo-router";
import {
  Bell,
  ChevronRight,
  FlaskConical,
  MapPinOff,
  RefreshCw,
  Satellite,
} from "lucide-react-native";
import { useEffect, useRef, useState } from "react";
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
  AgOfflineBanner,
  AgPressable,
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";
import { useSelectedFarm } from "@/features/weather";
import { FarmSelector } from "@/features/weather/components/FarmSelector";
import { useAppTheme } from "@/hooks/useAppTheme";
import { useAuthStore } from "@/features/auth/store/authStore";
import { logger } from "@/lib/logger";
import { ApiError } from "@/types";

import { ComparisonView } from "../components/ComparisonView";
import { IndexGauges } from "../components/IndexGauges";
import { LatestImageCard } from "../components/LatestImageCard";
import { SatelliteAnalysisCard } from "../components/SatelliteAnalysisCard";
import { SatelliteAlertCard } from "../components/SatelliteAlertCard";
import { SatelliteBackHeader } from "../components/SatelliteBackHeader";
import { SatelliteImageViewer } from "../components/SatelliteImageViewer";
import { VegetationHealthCard } from "../components/VegetationHealthCard";
import {
  useRefreshSatellite,
  useRepairSatelliteImages,
  useSatelliteDashboard,
  useSatelliteHistory,
  useSatelliteReadiness,
  useWaterloggingAssessment,
} from "../hooks/useSatellite";
import { useSatelliteSync } from "../hooks/useSatelliteSync";
import type { SatelliteImage } from "../types";
import { SATELLITE_UI } from "../design";

/** Satellite dashboard: latest scene, vegetation health, indices, alerts — or an
 * honest 'Not Available' / 'add a farm polygon' state. */
export function SatelliteDashboardScreen() {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const router = useRouter();
  const tokenPresent = useAuthStore((state) => Boolean(state.tokens?.idToken));
  useSatelliteSync();

  const {
    farms,
    selected,
    select,
    isLoading: farmsLoading,
    isError: farmsError,
    refetch: refetchFarms,
  } = useSelectedFarm();
  const farmId = selected?.id;
  const hasPolygon = selected?.hasBoundary ?? true;
  const query = useSatelliteDashboard(farmId, hasPolygon);
  const historyQuery = useSatelliteHistory(farmId);
  const waterloggingQuery = useWaterloggingAssessment(farmId);
  const readinessQuery = useSatelliteReadiness();
  const refresh = useRefreshSatellite();
  const repairImages = useRepairSatelliteImages();
  const [viewer, setViewer] = useState<SatelliteImage | null>(null);
  const autoRefreshFarm = useRef<string | null>(null);

  const data = query.data;
  const session = data?.session ?? null;

  useEffect(() => {
    if (!farmId || !hasPolygon || query.isLoading || query.isError || refresh.isPending) return;
    if (autoRefreshFarm.current === farmId) return;
    const ageMs = session?.captureDate ? Date.now() - new Date(session.captureDate).getTime() : Infinity;
    if (!session || ageMs > 7 * 24 * 60 * 60 * 1000) {
      autoRefreshFarm.current = farmId;
      refresh.mutate({ farmId, hasPolygon });
    }
  }, [farmId, hasPolygon, query.isError, query.isLoading, refresh, session]);

  useEffect(() => {
    logger.info("satellite.screen", "satellite_screen_mounted");
  }, []);

  useEffect(() => {
    logger.info("satellite.screen", "farm_selected", {
      farm_selected: Boolean(selected),
    });
    logger.info("satellite.screen", "coordinates_present", {
      coordinates_present: Boolean(
        selected?.latitude != null && selected?.longitude != null,
      ),
    });
    logger.info("satellite.screen", "polygon_present", {
      polygon_present: hasPolygon,
    });
    logger.info("satellite.screen", "authentication_state", {
      token_present: tokenPresent,
    });
  }, [hasPolygon, selected, tokenPresent]);

  useEffect(() => {
    if (!data) return;
    logger.info("satellite.render", "response_data_present", {
      response_data_present: true,
    });
    logger.info("satellite.render", "map_render_started");
    if (data.hasData && (data.session?.images.length ?? 0) > 0) {
      logger.info("satellite.render", "map_render_completed");
    } else {
      logger.info("satellite.render", "map_render_failed", {
        category: data.messageCode ?? "no_imagery",
      });
    }
  }, [data]);

  const onRefresh = () => {
    if (!farmId || refresh.isPending) return;
    refresh.mutate(
      { farmId, hasPolygon },
      {
        onSuccess: (res) => {
          if (res.offline) Alert.alert(t("satellite.queuedOffline"));
        },
        onError: () => Alert.alert(t("satellite.refreshFailed")),
      },
    );
  };

  if (farmsError) {
    return <AgScreen backgroundColor={SATELLITE_UI.canvas}>
      <SatelliteBackHeader title={t("satellite.title")} />
      <AgErrorState light onRetry={() => void refetchFarms()} />
    </AgScreen>;
  }

  if (!farmsLoading && farms.length === 0) {
    return (
      <AgScreen backgroundColor={SATELLITE_UI.canvas}>
        <SatelliteBackHeader title={t("satellite.title")} />
        <View className="mt-8">
          <AgCard
            style={styles.surfaceCard}
            className="items-center gap-2 py-8"
          >
            <Satellite size={30} color={SATELLITE_UI.spectral} />
            <AgText variant="body" weight="semibold" style={styles.primaryText}>
              {t("satellite.noFarmTitle")}
            </AgText>
            <AgButton
              light
              className="mt-2"
              title={t("home.actionAddFarm")}
              onPress={() => router.push("/farm/new")}
            />
          </AgCard>
        </View>
      </AgScreen>
    );
  }

  const alerts = session?.alerts ?? data?.alerts ?? [];

  return (
    <AgScreen padded={false} backgroundColor={SATELLITE_UI.canvas}>
      <AgOfflineBanner />
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={query.isRefetching || historyQuery.isRefetching || waterloggingQuery.isRefetching || refresh.isPending}
            enabled={!refresh.isPending}
            onRefresh={() => {
              if (refresh.isPending) return;
              void refetchFarms();
              void readinessQuery.refetch();
              if (!farmId) return;
              void query.refetch();
              void historyQuery.refetch();
              void waterloggingQuery.refetch();
            }}
            tintColor={colors.primary}
          />
        }
      >
        <SatelliteBackHeader title={t("satellite.title")} />
        <AgText variant="bodySmall" style={styles.mutedText}>
          {t("satellite.subtitle")}
        </AgText>

        <FarmSelector
          farms={farms}
          selectedId={selected?.id ?? null}
          onSelect={select}
          light
        />

        {readinessQuery.data && !readinessQuery.data.ready_for_image_generation ? (
          <AgCard style={styles.surfaceCard} className="gap-2 border border-warning/30">
            <AgText variant="label" weight="semibold" style={styles.primaryText}>
              {t("satellite.readinessTitle")}
            </AgText>
            <AgText variant="bodySmall" style={styles.mutedText}>
              {t("satellite.readinessBody")}
            </AgText>
            <AgText variant="caption" style={styles.mutedText}>
              {t("satellite.readinessMissing")}: {readinessQuery.data.missing_components.join(", ")}
            </AgText>
          </AgCard>
        ) : null}

        {farmsLoading || query.isLoading ? (
          <View className="gap-3">
            {[0, 1, 2].map((i) => (
              <AgSkeleton key={i} style={{ height: 112, width: "100%", borderRadius: 18 }} />
            ))}
          </View>
        ) : query.isError ? (
          <AgCard
            style={styles.surfaceCard}
            className="items-center gap-2 border border-danger/30 py-6"
          >
            <AgText variant="body" weight="semibold" style={styles.primaryText}>
              {t("satellite.unavailableTitle")}
            </AgText>
            <AgText variant="bodySmall" style={styles.mutedText} center>
              {query.error instanceof ApiError && query.error.isNetwork
                ? t("errors.network")
                : query.error instanceof ApiError &&
                    query.error.errorCode.toLowerCase().includes("timeout")
                  ? t("errors.timeout")
                  : t("satellite.status.provider_error")}
            </AgText>
            <AgButton
              light
              title={t("common.retry")}
              onPress={() => void query.refetch()}
            />
          </AgCard>
        ) : (
          <>
            {/* Sample-data notice — sample indices are clearly flagged, never presented as real. */}
            {session?.isSample ? (
              <AgCard
                style={styles.surfaceCard}
                className="flex-row items-center gap-2 border border-info/30"
              >
                <FlaskConical size={16} color={colors.info} />
                <AgText variant="caption" style={styles.mutedText} className="flex-1">
                  {t("satellite.sampleNotice")}
                </AgText>
              </AgCard>
            ) : null}
            {data?.dataSource === "cached" || data?.dataSource === "stale" ? (
              <AgCard
                style={styles.surfaceCard}
                className="border border-warning/30"
              >
                <AgText variant="caption" style={styles.mutedText}>
                  {t(
                    data.dataSource === "stale"
                      ? "satellite.staleNotice"
                      : "satellite.cachedNotice",
                  )}
                </AgText>
              </AgCard>
            ) : null}
            {refresh.isError ? <AgErrorState light onRetry={onRefresh} /> : null}
            {waterloggingQuery.isError ? (
              <AgCard style={styles.surfaceCard}>
                <AgText style={styles.primaryText}>{t("satellite.waterlogging.title")}</AgText>
                <AgErrorState light onRetry={() => void waterloggingQuery.refetch()} />
              </AgCard>
            ) : waterloggingQuery.data ? (
              <AgCard
                style={styles.surfaceCard}
                className="gap-2 border border-info/30"
              >
                <AgText variant="label" weight="semibold" style={styles.primaryText}>
                  {t("satellite.waterlogging.title")}
                </AgText>
                <AgText variant="bodySmall" weight="semibold" style={styles.primaryText}>
                  {t(
                    `satellite.waterlogging.${waterloggingQuery.data.decision}`,
                  )}
                </AgText>
                <AgText variant="caption" style={styles.mutedText}>
                  {t("satellite.waterlogging.caution")}
                </AgText>
                {waterloggingQuery.data.freshness === "stale" ? (
                  <AgText variant="caption" style={styles.mutedText}>
                    {t("satellite.waterlogging.stale")}
                  </AgText>
                ) : null}
                {waterloggingQuery.data.isSample ? (
                  <AgText variant="caption" style={styles.mutedText}>
                    {t("satellite.waterlogging.sample")}
                  </AgText>
                ) : null}
                <AgButton
                  light
                  variant="outline"
                  title={t("satellite.waterlogging.open")}
                  onPress={() =>
                    router.push({
                      pathname: "/satellite/waterlogging" as never,
                      params: { farmId },
                    })
                  }
                />
              </AgCard>
            ) : farmId ? (
              <AgCard
                style={styles.surfaceCard}
                className="gap-2 border border-info/30"
              >
                <AgText variant="label" weight="semibold" style={styles.primaryText}>
                  {t("satellite.waterlogging.title")}
                </AgText>
                <AgText variant="caption" style={styles.mutedText}>
                  {t("satellite.waterlogging.noAssessmentBody")}
                </AgText>
                <AgButton
                  light
                  variant="outline"
                  title={t("satellite.waterlogging.open")}
                  onPress={() =>
                    router.push({
                      pathname: "/satellite/waterlogging" as never,
                      params: { farmId },
                    })
                  }
                />
              </AgCard>
            ) : null}

            {/* No polygon → prompt to draw the field boundary. */}
            {data && !data.hasPolygon ? (
              <AgCard
                style={styles.surfaceCard}
                className="items-center gap-2 border border-warning/30 py-6"
              >
                <MapPinOff size={26} color={colors.warning} />
                <AgText variant="body" weight="semibold" style={styles.primaryText}>
                  {t("satellite.noPolygonTitle")}
                </AgText>
                <AgText
                  variant="bodySmall"
                  style={styles.mutedText}
                  className="px-4 text-center"
                >
                  {t("satellite.noPolygonMessage")}
                </AgText>
                <AgButton
                  light
                  className="mt-2"
                  variant="outline"
                  title={t("satellite.drawBoundary")}
                  onPress={() =>
                    selected && router.push(`/farm/${selected.id}/boundary`)
                  }
                />
              </AgCard>
            ) : data && !data.hasData ? (
              <AgCard
                style={styles.surfaceCard}
                className="items-center gap-2 border border-warning/30 py-6"
              >
                <Satellite size={26} color={colors.warning} />
                <AgText variant="body" weight="semibold" style={styles.primaryText}>
                  {t("satellite.unavailableTitle")}
                </AgText>
                <AgText
                  variant="bodySmall"
                  style={styles.mutedText}
                  className="px-4 text-center"
                >
                  {t(data.messageCode ?? "satellite.status.never_refreshed")}
                </AgText>
              </AgCard>
            ) : null}

            {session && data?.hasData ? (
              <>
                <LatestImageCard
                  session={session}
                  onOpen={setViewer}
                  repairing={repairImages.isPending}
                  onRepair={() => {
                    if (!farmId) return;
                    repairImages.mutate(farmId, {
                      onError: () => Alert.alert(t("satellite.refreshFailed")),
                    });
                  }}
                />
                <SatelliteAnalysisCard session={session} />
                <VegetationHealthCard session={session} />
                <IndexGauges indices={session.indices} />
                {(historyQuery.data?.items?.length ?? 0) >= 2 ? (
                  <ComparisonView entries={historyQuery.data!.items} />
                ) : null}
              </>
            ) : null}

            {/* Alerts preview */}
            {alerts.length > 0 ? (
              <View className="gap-2">
                <View className="flex-row items-center justify-between">
                  <View className="flex-row items-center gap-1">
                    <Bell size={15} color={SATELLITE_UI.muted} />
                    <AgText variant="label" weight="semibold" style={styles.mutedText}>
                      {t("satellite.alerts")}
                    </AgText>
                  </View>
                  <AgPressable
                    onPress={() =>
                      router.push({
                        pathname: "/satellite/alerts",
                        params: { farmId },
                      })
                    }
                    accessibilityRole="button"
                    accessibilityLabel={t("satellite.viewAll")}
                    className="flex-row items-center"
                  >
                    <AgText variant="caption" weight="semibold" style={styles.greenText}>
                      {t("satellite.viewAll")}
                    </AgText>
                    <ChevronRight size={14} color={SATELLITE_UI.spectral} />
                  </AgPressable>
                </View>
                {alerts.slice(0, 3).map((a) => (
                  <SatelliteAlertCard key={a.code} alert={a} />
                ))}
              </View>
            ) : null}

            <View className="mt-1 flex-row gap-2">
              <AgButton
                light
                className="flex-1"
                variant="primary"
                title={t("satellite.refresh")}
                leftIcon={<RefreshCw size={18} color={SATELLITE_UI.text} />}
                onPress={onRefresh}
                loading={refresh.isPending}
              />
              <AgButton
                light
                className="flex-1"
                variant="outline"
                title={t("satellite.timeline")}
                onPress={() =>
                  router.push({
                    pathname: "/satellite/timeline",
                    params: { farmId },
                  })
                }
              />
            </View>
          </>
        )}
      </ScrollView>

      <SatelliteImageViewer image={viewer} onClose={() => setViewer(null)} />
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1, paddingHorizontal: 20 },
  content: { gap: 12, paddingBottom: 112 },
  surfaceCard: {
    backgroundColor: SATELLITE_UI.surface,
    borderColor: SATELLITE_UI.border,
  },
  primaryText: { color: SATELLITE_UI.text },
  mutedText: { color: SATELLITE_UI.muted },
  greenText: { color: SATELLITE_UI.spectral },
});
