import { RefreshCw, Waves } from "lucide-react-native";
import { useState } from "react";
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
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";
import { useSelectedFarm } from "@/features/weather";
import { FarmSelector } from "@/features/weather/components/FarmSelector";
import { ApiError } from "@/types";

import { SatelliteBackHeader } from "../components/SatelliteBackHeader";
import { LatestImageCard } from "../components/LatestImageCard";
import { SatelliteImageViewer } from "../components/SatelliteImageViewer";
import {
  useRefreshWaterlogging,
  useSatelliteDashboard,
  useWaterloggingAssessment,
  useWaterloggingHistory,
} from "../hooks/useSatellite";
import type { SatelliteImage, WaterloggingAssessment } from "../types";
import { SATELLITE_SHADOW, SATELLITE_UI } from "../design";

function ResultCard({ result }: { result: WaterloggingAssessment }) {
  const { t } = useTranslation();
  const sourceState = result.dataSource ?? "live";
  return (
    <View style={styles.resultCard}>
      <AgText variant="body" weight="semibold" style={styles.resultTitle}>
        {t(`satellite.waterlogging.${result.decision}`)}
      </AgText>
      <AgText variant="bodySmall" style={styles.resultGuidance}>
        {t("satellite.waterlogging.guidance")}
      </AgText>
      {result.decision === "review_required" ? (
        <View style={styles.reviewNote}>
          <AgText variant="bodySmall" style={styles.reviewText}>
            {t("satellite.waterlogging.reviewReason")}
          </AgText>
        </View>
      ) : null}
      <AgText variant="caption" style={styles.resultMeta}>
        {t(
          `satellite.waterlogging.evidence_${String(result.provenance.evidence_type ?? "insufficient")}`,
        )}
      </AgText>
      <AgText variant="caption" style={styles.resultMeta}>
        {t(`satellite.waterlogging.source_${sourceState}`)}
      </AgText>
      {result.freshness === "stale" ? (
        <AgText variant="caption" style={styles.missingText}>{t("satellite.waterlogging.stale")}</AgText>
      ) : null}
      {result.aoiCoveragePct != null ? (
        <AgText variant="caption" style={styles.resultMetaStrong}>
          {t("satellite.waterlogging.coverage", {
            value: Math.round(result.aoiCoveragePct),
          })}
        </AgText>
      ) : null}
      {result.evidencePresent.length > 0 ? (
        <AgText variant="caption" style={styles.resultMetaStrong}>
          {t("satellite.waterlogging.availableEvidence", {
            count: result.evidencePresent.length,
          })}
        </AgText>
      ) : null}
      <AgText variant="caption" style={styles.resultMeta}>
        {t("satellite.waterlogging.lastChecked", {
          time: new Date(
            result.observedAt ?? result.processedAt,
          ).toLocaleString(),
        })}
      </AgText>
      {result.evidenceMissing.length > 0 ? (
        <AgText variant="caption" style={styles.missingText}>
          {t("satellite.waterlogging.missingEvidenceCount", {
            count: result.evidenceMissing.length,
          })}
        </AgText>
      ) : null}
      {result.isSample ? (
        <AgText variant="caption" style={styles.resultMeta}>
          {t("satellite.waterlogging.sample")}
        </AgText>
      ) : null}
      <AgText variant="caption" style={styles.resultMeta}>
        {t("satellite.waterlogging.caution")}
      </AgText>
      <AgText variant="caption" style={styles.resultMeta}>
        {t("satellite.waterlogging.verifyOfficial")}
      </AgText>
    </View>
  );
}

/** Farmer-facing water evidence screen. It presents backend evidence only and
 * never derives a flood conclusion on-device. */
export function WaterloggingScreen() {
  const { t } = useTranslation();
  const {
    farms,
    selected,
    select,
    isLoading: farmsLoading,
    isError: farmsError,
    refetch: refetchFarms,
  } = useSelectedFarm();
  const farmId = selected?.id;
  const hasBoundary = selected?.hasBoundary ?? false;
  const latest = useWaterloggingAssessment(farmId);
  const history = useWaterloggingHistory(farmId);
  const dashboard = useSatelliteDashboard(farmId, hasBoundary);
  const refresh = useRefreshWaterlogging();
  const [viewer, setViewer] = useState<SatelliteImage | null>(null);
  const satelliteSession = dashboard.data?.session ?? null;

  const onRefresh = () => {
    if (!farmId || !hasBoundary || refresh.isPending) return;
    refresh.mutate(farmId, {
      onError: (error) =>
        Alert.alert(
          error instanceof ApiError && error.isNetwork
            ? t("satellite.waterlogging.offlineRefresh")
            : t("satellite.waterlogging.refreshFailed"),
        ),
    });
  };

  if (farmsError) {
    return <AgScreen backgroundColor={SATELLITE_UI.canvas}>
      <SatelliteBackHeader title={t("satellite.waterlogging.title")} />
      <AgErrorState light onRetry={() => void refetchFarms()} />
    </AgScreen>;
  }

  return (
    <AgScreen padded={false} backgroundColor={SATELLITE_UI.canvas}>
      <AgOfflineBanner />
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={latest.isRefetching || history.isRefetching || dashboard.isRefetching || refresh.isPending}
            enabled={!refresh.isPending}
            onRefresh={() => {
              if (refresh.isPending) return;
              void refetchFarms();
              if (!farmId) return;
              void latest.refetch();
              void history.refetch();
              void dashboard.refetch();
            }}
            tintColor={SATELLITE_UI.spectral}
          />
        }
      >
        <SatelliteBackHeader title={t("satellite.waterlogging.title")} />
        <AgText variant="bodySmall" style={styles.mutedText}>
          {t("satellite.waterlogging.subtitle")}
        </AgText>
        <FarmSelector
          farms={farms}
          selectedId={selected?.id ?? null}
          onSelect={select}
          light
        />

        {farmsLoading || latest.isLoading ? (
          <View className="gap-3">
            <AgSkeleton style={{ height: 160, width: "100%", borderRadius: 18 }} />
            <AgSkeleton style={{ height: 96, width: "100%", borderRadius: 18 }} />
          </View>
        ) : !selected ? (
          <AgCard
            style={styles.surfaceCard}
            className="items-center gap-2 py-8"
          >
            <Waves size={26} color={SATELLITE_UI.muted} />
            <AgText style={styles.primaryText}>
              {t("satellite.waterlogging.selectFarm")}
            </AgText>
          </AgCard>
        ) : !hasBoundary ? (
          <AgCard
            style={styles.surfaceCard}
            className="gap-2 border border-warning/30"
          >
            <AgText weight="semibold" style={styles.primaryText}>
              {t("satellite.noPolygonTitle")}
            </AgText>
            <AgText variant="bodySmall" style={styles.mutedText}>
              {t("satellite.waterlogging.boundaryRequired")}
            </AgText>
          </AgCard>
        ) : latest.isError ? (
          <AgCard
            style={styles.surfaceCard}
            className="gap-3 border border-danger/30"
          >
            <AgText weight="semibold" style={styles.primaryText}>
              {t("satellite.unavailableTitle")}
            </AgText>
            <AgText variant="bodySmall" style={styles.mutedText}>
              {t("satellite.waterlogging.error")}
            </AgText>
            <AgButton
              light
              title={t("common.retry")}
              onPress={() => void latest.refetch()}
            />
          </AgCard>
        ) : latest.data ? (
          <ResultCard result={latest.data} />
        ) : (
          <AgCard style={styles.surfaceCard} className="gap-2">
            <AgText weight="semibold" style={styles.primaryText}>
              {t("satellite.waterlogging.noAssessment")}
            </AgText>
            <AgText variant="bodySmall" style={styles.mutedText}>
              {t("satellite.waterlogging.noAssessmentBody")}
            </AgText>
          </AgCard>
        )}

        {satelliteSession ? (
          <View style={styles.imageSection}>
            <AgText variant="label" weight="semibold" style={styles.primaryText}>
              {t("satellite.waterlogging.sceneHeading")}
            </AgText>
            <AgText variant="caption" style={styles.resultMeta}>
              {t("satellite.waterlogging.sceneContext")}
            </AgText>
            <LatestImageCard session={satelliteSession} onOpen={setViewer} />
          </View>
        ) : farmId && hasBoundary && !dashboard.isLoading ? (
          <View style={styles.imageUnavailableCard}>
            <AgText weight="semibold" style={styles.primaryText}>
              {t("satellite.waterlogging.sceneUnavailable")}
            </AgText>
            <AgText variant="bodySmall" style={styles.mutedText}>
              {t("satellite.waterlogging.sceneUnavailableBody")}
            </AgText>
          </View>
        ) : null}

        {farmId && hasBoundary ? (
          <AgButton
            light
            title={t("satellite.waterlogging.refresh")}
            leftIcon={<RefreshCw size={18} color={SATELLITE_UI.text} />}
            loading={refresh.isPending}
            onPress={onRefresh}
          />
        ) : null}

        {history.isError && farmId ? (
          <AgCard style={styles.surfaceCard}>
            <AgText style={styles.primaryText}>{t("satellite.waterlogging.history")}</AgText>
            <AgErrorState light onRetry={() => void history.refetch()} />
          </AgCard>
        ) : null}
        {(history.data?.length ?? 0) > 0 ? (
          <View className="gap-2">
            <AgText variant="label" weight="semibold" style={styles.primaryText}>
              {t("satellite.waterlogging.history")}
            </AgText>
            {history.data!.slice(0, 10).map((item) => (
              <ResultCard key={item.id} result={item} />
            ))}
          </View>
        ) : null}
      </ScrollView>
      <SatelliteImageViewer image={viewer} onClose={() => setViewer(null)} />
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1, paddingHorizontal: 20 },
  content: { gap: 12, paddingBottom: 112 },
  resultCard: {
    gap: 8,
    padding: 17,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: SATELLITE_UI.cyan,
    backgroundColor: SATELLITE_UI.surface,
    ...SATELLITE_SHADOW,
  },
  surfaceCard: {
    backgroundColor: SATELLITE_UI.surface,
    borderColor: SATELLITE_UI.border,
  },
  primaryText: { color: SATELLITE_UI.text },
  mutedText: { color: "#43564D", lineHeight: 21 },
  resultTitle: { color: SATELLITE_UI.text },
  resultGuidance: { color: SATELLITE_UI.text, lineHeight: 23 },
  resultMeta: { color: "#43564D", lineHeight: 20 },
  resultMetaStrong: { color: SATELLITE_UI.text, lineHeight: 20 },
  missingText: { color: "#7A461C", lineHeight: 20, fontWeight: "600" },
  reviewNote: {
    padding: 12,
    borderRadius: 14,
    backgroundColor: "#FFF3D6",
  },
  reviewText: { color: "#65410F", lineHeight: 21 },
  imageSection: { gap: 7 },
  imageUnavailableCard: {
    gap: 6,
    padding: 16,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: SATELLITE_UI.border,
    backgroundColor: SATELLITE_UI.surface,
  },
});
