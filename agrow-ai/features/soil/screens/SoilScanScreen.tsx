import { useLocalSearchParams, useRouter } from "expo-router";
import type { TFunction } from "i18next";
import {
  CheckCircle2,
  Clock3,
  FlaskConical,
  MapPinned,
  Satellite,
  ScanSearch,
} from "lucide-react-native";
import { ActivityIndicator, RefreshControl, ScrollView, StyleSheet, View } from "react-native";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  AgButton,
  AgEmptyState,
  AgErrorState,
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";
import { SOIL_TYPES } from "@/features/farm/constants";
import { SoilSamplingMap } from "../components/SoilSamplingMap";
import { SoilFeatureHeader } from "../components/SoilFeatureHeader";
import { SOIL_SHADOW, SOIL_UI } from "../design";
import {
  useRunSoilScan,
  useSoilScan,
  useSoilScanHistory,
} from "../hooks/useSoilScan";
import { formatSamplingReason } from "../utils/formatSamplingReason";
import { getIndicatorAvailabilityLabel } from "../utils/getIndicatorAvailabilityLabel";
import type { SoilScanPhase } from "../services/soilScanOrchestrator";

// Reuse the exact same value -> label-key map the farm registration form uses
// for soil type (features/farm/constants.ts), so a soil-map texture estimate
// and a farmer's own registered soil type render identically ("sandy" always
// reads as "Sandy" either way).
const SOIL_TYPE_LABEL_KEY: Record<string, string> = Object.fromEntries(
  SOIL_TYPES.map((option) => [option.value, option.labelKey]),
);

/** Turn a snake_case backend value (e.g. "possible_waterlogging",
 * "slightly_acidic") into readable text without a full per-value translation
 * table -- honest and readable is better than blank while that table doesn't
 * exist yet. */
function humanize(raw: string): string {
  return raw
    .split("_")
    .map((word) => (word ? word[0].toUpperCase() + word.slice(1) : word))
    .join(" ");
}

/** The indicator's headline value: the known soil-type label when we have
 * one, else a humanized version of whatever the backend sent. Numbers are
 * shown as-is. `null`/`undefined` renders nothing (status already covers
 * "not available"). */
function formatIndicatorValue(
  value: string | number | null | undefined,
  t: TFunction,
): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return String(value);
  const labelKey = SOIL_TYPE_LABEL_KEY[value];
  return labelKey ? t(labelKey) : humanize(value);
}

/** A short, concrete detail line for indicators whose real sourced numbers
 * are worth showing alongside the headline value/rating -- pH, EC/salinity,
 * and (2026-08-19) the SoilGrids texture composition. Returns null when none
 * of these keys are present so other indicators render nothing extra. */
function formatIndicatorDetail(
  code: string,
  details: Record<string, unknown>,
): string | null {
  const num = (v: unknown) => (typeof v === "number" ? v : null);
  const ph = num(details.ph);
  if (ph !== null) return `pH ${ph}`;
  const ec = num(details.ec_salinity);
  if (ec !== null) return `EC ${ec} dS/m`;
  const clay = num(details.clay_pct);
  const sand = num(details.sand_pct);
  const silt = num(details.silt_pct);
  if (clay !== null && sand !== null && silt !== null) {
    return `Clay ${clay}% · Sand ${sand}% · Silt ${silt}%`;
  }
  if (code === "organic_carbon_estimate") {
    const low = num(details.uncertainty_low);
    const high = num(details.uncertainty_high);
    const resolution = num(details.resolution_m);
    return (
      [
        low !== null && high !== null ? `Mapped range ${low}–${high}%` : null,
        resolution !== null ? `${resolution} m map resolution` : null,
      ]
        .filter(Boolean)
        .join(" · ") || null
    );
  }
  if (code === "erosion_runoff") {
    const slope = num(details.mean_slope_degrees);
    const relief = num(details.elevation_range_m);
    return (
      [
        slope !== null ? `Mapped slope ${slope}°` : null,
        relief !== null ? `Elevation range ${relief} m` : null,
      ]
        .filter(Boolean)
        .join(" · ") || null
    );
  }
  return null;
}

export function SoilScanScreen() {
  const params = useLocalSearchParams<{ farmId?: string | string[] }>();
  const farmId = typeof params.farmId === "string" ? params.farmId.trim() || undefined : undefined;
  const router = useRouter();
  const { t } = useTranslation();
  const query = useSoilScan(farmId);
  const [scanPhase, setScanPhase] = useState<SoilScanPhase>("idle");
  const run = useRunSoilScan(farmId, setScanPhase);
  const history = useSoilScanHistory(farmId);
  const scan = query.data;
  if (!farmId) {
    return (
      <AgScreen backgroundColor={SOIL_UI.canvas}>
        <SoilFeatureHeader title={t("soil.scanTitle")} subtitle={t("soil.scanSafety")} onBack={() => router.back()} />
        <AgEmptyState light title={t("soil.noFarmTitle")} message={t("soil.noFarmMessage")} />
      </AgScreen>
    );
  }
  const missingCodes = new Set(
    scan?.indicators
      .filter((item) => item.status !== "available")
      .map((item) => item.code) ?? [],
  );
  const needsSatellite = [
    "soil_moisture", "drought_stress", "poor_performing_zones", "soil_cover",
  ].some((code) => missingCodes.has(code));
  const needsWaterlogging = missingCodes.has("waterlogging_drainage");
  const needsSoilType = missingCodes.has("texture_likelihood");
  const needsLabReport = [
    "salinity_risk", "organic_matter_trend", "acidity_ph_risk",
  ].some((code) => missingCodes.has(code));
  const progressLabel =
    scanPhase === "checking_satellite"
      ? t("soil.checkingSatellite")
      : scanPhase === "refreshing_satellite"
        ? t("soil.analyzingField")
        : scanPhase === "refreshing_waterlogging"
          ? t("soil.refreshingWaterlogging")
        : scanPhase === "preparing_soil"
          ? t("soil.preparingInsights")
          : t("soil.runScan");
  return (
    <AgScreen padded={false} backgroundColor={SOIL_UI.canvas}>
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={query.isRefetching || history.isRefetching}
            enabled={!run.isPending}
            tintColor={SOIL_UI.green}
            onRefresh={() => {
              if (run.isPending) return;
              void query.refetch();
              void history.refetch();
            }}
          />
        }
      >
        <SoilFeatureHeader
          title={t("soil.scanTitle")}
          subtitle={t("soil.scanSafety")}
          onBack={() => router.back()}
        />
        <View style={styles.scanHero}>
          <View style={styles.scanHeroIcon}>
            {run.isPending ? (
              <ActivityIndicator color={SOIL_UI.white} />
            ) : (
              <ScanSearch size={30} color={SOIL_UI.white} />
            )}
          </View>
          <View style={styles.scanHeroCopy}>
            <AgText variant="headingS" weight="bold" style={styles.heroText}>
              {run.isPending ? progressLabel : t("soil.runScan")}
            </AgText>
            <AgText variant="bodySmall" style={styles.heroMuted}>
              {run.isPending
                ? t("soil.preparingInsights")
                : t("soil.scanSafety")}
            </AgText>
          </View>
          <AgButton
            title={run.isPending ? progressLabel : t("soil.runScan")}
            variant="secondary"
            disabled={run.isPending}
            onPress={() => run.mutate()}
          />
        </View>
        {run.isPending ? (
          <View style={styles.progressRow} accessibilityRole="progressbar">
            <Satellite size={19} color={SOIL_UI.green} />
            <AgText variant="bodySmall" style={styles.mutedText}>
              {progressLabel}
            </AgText>
          </View>
        ) : null}
        {/* "Run scan" only ever toggled its own pending label -- a failed
            mutation (offline, timeout, server error) silently reverted the
            button to "Scan this farm" with no indication anything went
            wrong (2026-08 pre-release live-testing pass). */}
        {run.isError ? (
          <View style={styles.errorCard} accessibilityRole="alert">
            <AgText style={styles.errorText}>{t("soil.scanFailed")}</AgText>
          </View>
        ) : null}
        {query.isLoading ? (
          <AgSkeleton style={{ height: 160, width: "100%", borderRadius: 18 }} />
        ) : null}
        {query.isError ? (
          <View style={styles.sectionCard}>
            {!scan && (query.error as { status?: number } | null)?.status === 404 ? (
              <AgText style={styles.mutedText}>{t("soil.noSavedScan")}</AgText>
            ) : (
              <AgErrorState light onRetry={() => void query.refetch()} />
            )}
          </View>
        ) : null}
        {query.data?.cacheState === "cached" ? (
          <View style={styles.cachedNote}>
            <Clock3 size={18} color={SOIL_UI.earth} />
            <AgText variant="bodySmall" style={styles.earthText}>
              {t("soil.cachedScan", { date: query.data.generatedAt })}
            </AgText>
          </View>
        ) : null}
        {scan && missingCodes.size > 0 ? (
          <View style={styles.sectionCard} testID="soil-prerequisites">
            <AgText variant="headingM" weight="bold" style={styles.sectionTitle}>
              {t("soil.prerequisitesTitle")}
            </AgText>
            <AgText variant="bodySmall" style={styles.mutedText}>
              {t("soil.prerequisitesBody")}
            </AgText>
            {!scan.aoiVerified ? (
              <AgButton light variant="outline" title={t("soil.addBoundary")}
                onPress={() => router.push(`/farm/${farmId}/boundary`)} />
            ) : null}
            {needsSatellite ? (
              <AgButton light variant="outline" title={t("soil.runSatellite")}
                onPress={() => router.push({ pathname: "/satellite", params: { farmId } })} />
            ) : null}
            {needsWaterlogging ? (
              <AgButton light variant="outline" title={t("soil.runWaterlogging")}
                onPress={() => router.push({ pathname: "/satellite/waterlogging", params: { farmId } })} />
            ) : null}
            {needsSoilType ? (
              <AgButton light variant="outline" title={t("soil.estimateSoilTexture")}
                disabled={run.isPending}
                onPress={() => run.mutate()} />
            ) : null}
            {needsLabReport ? (
              <AgButton light variant="outline" title={t("soil.uploadSoilReport")}
                onPress={() => router.push({ pathname: "/soil/upload", params: { farmId } })} />
            ) : null}
            {Object.entries(scan.providerStates).map(([provider, status]) => (
              <AgText key={provider} variant="caption" style={styles.evidenceText}>
                {t("soil.providerStatus")}: {humanize(provider)} · {humanize(status)}
              </AgText>
            ))}
          </View>
        ) : null}
        {query.data?.indicators.map((item) => {
          const value =
            item.status === "available"
              ? formatIndicatorValue(item.value, t)
              : null;
          const detail =
            item.status === "available"
              ? formatIndicatorDetail(item.code, item.details)
              : null;
          const availabilityLabel = getIndicatorAvailabilityLabel(
            item.code,
            item.status,
          );
          return (
            <View key={item.code} style={styles.indicatorCard}>
              <View style={styles.indicatorTopRow}>
                <View style={styles.indicatorIcon}>
                  {availabilityLabel === "lab_report_required" ? (
                    <FlaskConical size={22} color={SOIL_UI.earth} />
                  ) : (
                    <CheckCircle2 size={22} color={SOIL_UI.green} />
                  )}
                </View>
                <AgText weight="bold" style={styles.indicatorTitle}>
                  {t(`soil.scanIndicators.${item.code}`)}
                </AgText>
              </View>
              <AgText
                variant="bodySmall"
                style={[
                  styles.availabilityText,
                  availabilityLabel === "available"
                    ? styles.availabilityAvailable
                    : availabilityLabel === "lab_report_required"
                      ? styles.availabilityLabRequired
                      : styles.availabilityInsufficient,
                ]}
              >
                {availabilityLabel === "available"
                  ? t("soil.scanAvailable")
                  : availabilityLabel === "lab_report_required"
                    ? t("soil.labReportRequired")
                    : t("soil.scanInsufficient")}
              </AgText>
              {/* The actual reading -- previously computed by the backend for
                  every "available" indicator (a pH rating, a moisture status, a
                  texture class...) but never rendered here, so even a fully
                  working row only ever said "Available" with no value (found
                  2026-08-19 investigating a "values still not available"
                  report). Shown only once we have both a real value AND a
                  successful (non-error) status, so nothing is invented. */}
              {value ? (
                <AgText
                  variant="headingM"
                  weight="bold"
                  style={styles.valueText}
                >
                  {value}
                </AgText>
              ) : null}
              {detail ? (
                <AgText variant="bodySmall" style={styles.mutedText}>
                  {detail}
                </AgText>
              ) : null}
              {/* The "why" for this specific row -- unblocks a real reading vs. a
                  fresh field's honest "no evidence yet" (found 2026-08-19: every
                  insufficient row showed the identical generic message, so a
                  mostly-working scan read as completely broken). */}
              <AgText variant="bodySmall" style={styles.explanationText}>
                {t(item.explanationCode, { defaultValue: "" })}
              </AgText>
              <AgText variant="caption" style={styles.evidenceText}>
                {t(`soil.evidenceClasses.${item.evidenceClass}`, {
                  defaultValue: item.evidenceClass,
                })}
              </AgText>
              {item.sources.length ? (
                <View style={styles.sourceChip}>
                  <AgText variant="caption" style={styles.sourceText}>
                    {t("soil.sources")}: {item.sources.join(", ")}
                  </AgText>
                </View>
              ) : null}
              {item.observationTimestamps.map((timestamp) => (
                <AgText key={timestamp} variant="caption" style={styles.evidenceText}>
                  {t("soil.observedAt")}: {new Date(timestamp).toLocaleString()}
                </AgText>
              ))}
            </View>
          );
        })}
        {query.data?.samplingPlan ? (
          <View style={styles.sectionCard}>
            <View style={styles.sectionHeading}>
              <MapPinned size={24} color={SOIL_UI.green} />
              <AgText
                variant="headingM"
                weight="bold"
                style={styles.sectionTitle}
              >
                {t("soil.samplingNavigator")}
              </AgText>
            </View>
            <AgText style={styles.mutedText}>{t("soil.samplingSafety")}</AgText>
            <SoilSamplingMap scan={query.data} />
            {query.data.samplingPlan.points.map((point) => (
              <View key={point.zoneId} style={styles.samplingPoint}>
                <View style={styles.samplingPointHeader}>
                  <MapPinned size={18} color={SOIL_UI.green} />
                  <AgText weight="bold" style={styles.samplingPointTitle}>
                    {t("soil.samplingLocation")}
                  </AgText>
                  <View style={styles.zoneBadge}>
                    <AgText variant="caption" weight="semibold" style={styles.zoneBadgeText}>
                      {point.zoneId}
                    </AgText>
                  </View>
                </View>
                <AgText variant="bodySmall" style={styles.samplingPointReason}>
                  {t("soil.whySampleHere")}:{" "}
                  {formatSamplingReason(point.reason)}
                </AgText>
              </View>
            ))}
          </View>
        ) : query.data ? (
          <View style={styles.sectionCard}>
            <AgText style={styles.mutedText}>
              {t("soil.insufficientSpatialEvidence")}
            </AgText>
          </View>
        ) : null}
        {history.isLoading ? <AgSkeleton style={{ height: 80, width: "100%", borderRadius: 18 }} /> : null}
        {history.isError ? (
          <View style={styles.sectionCard} testID="soil-history-error">
            <AgText style={styles.sectionTitle}>{t("soil.previousScans")}</AgText>
            <AgErrorState light onRetry={() => void history.refetch()} />
          </View>
        ) : null}
        {history.data?.length ? (
          <View style={styles.sectionCard}>
            <View style={styles.sectionHeading}>
              <Clock3 size={23} color={SOIL_UI.earth} />
              <AgText
                variant="headingM"
                weight="bold"
                style={styles.sectionTitle}
              >
                {t("soil.previousScans")}
              </AgText>
            </View>
            {history.data.map((scan) => (
              <AgText
                key={scan.id}
                variant="bodySmall"
                style={styles.historyDate}
              >
                {new Date(scan.generatedAt).toLocaleString()}
              </AgText>
            ))}
          </View>
        ) : null}
      </ScrollView>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  content: { gap: 14, paddingHorizontal: 20, paddingBottom: 112 },
  scanHero: {
    padding: 18,
    borderRadius: 22,
    backgroundColor: SOIL_UI.green,
    gap: 13,
    ...SOIL_SHADOW,
  },
  scanHeroIcon: {
    width: 54,
    height: 54,
    borderRadius: 18,
    backgroundColor: "#287447",
    alignItems: "center",
    justifyContent: "center",
  },
  scanHeroCopy: { gap: 3 },
  heroText: { color: SOIL_UI.white },
  heroMuted: { color: "#DDEDE2", lineHeight: 20 },
  progressRow: {
    minHeight: 48,
    borderRadius: 14,
    backgroundColor: SOIL_UI.greenSoft,
    paddingHorizontal: 14,
    flexDirection: "row",
    alignItems: "center",
    gap: 9,
  },
  sectionCard: {
    padding: 16,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: SOIL_UI.border,
    backgroundColor: SOIL_UI.surface,
    gap: 10,
    ...SOIL_SHADOW,
  },
  indicatorCard: {
    padding: 16,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: SOIL_UI.border,
    backgroundColor: SOIL_UI.surface,
    gap: 7,
  },
  indicatorTopRow: { flexDirection: "row", alignItems: "center", gap: 11 },
  indicatorIcon: {
    width: 42,
    height: 42,
    borderRadius: 13,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: SOIL_UI.greenSoft,
  },
  indicatorTitle: { flex: 1, color: SOIL_UI.text, lineHeight: 22 },
  availabilityText: { fontWeight: "700", lineHeight: 20 },
  availabilityAvailable: { color: SOIL_UI.green },
  availabilityLabRequired: { color: "#7A461C" },
  availabilityInsufficient: { color: "#754B22" },
  valueText: { color: SOIL_UI.green, marginTop: 2 },
  mutedText: { color: SOIL_UI.muted, lineHeight: 21 },
  explanationText: { color: SOIL_UI.text, lineHeight: 21 },
  evidenceText: { color: "#42564B", lineHeight: 20 },
  sourceChip: {
    alignSelf: "flex-start",
    borderRadius: 12,
    backgroundColor: SOIL_UI.greenSoft,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  sourceText: { color: SOIL_UI.green },
  sectionHeading: { flexDirection: "row", alignItems: "center", gap: 9 },
  sectionTitle: { flex: 1, color: SOIL_UI.text },
  samplingPoint: {
    padding: 14,
    borderRadius: 16,
    backgroundColor: SOIL_UI.surfaceSoft,
    borderWidth: 1,
    borderColor: "#D5E3D2",
    gap: 8,
  },
  samplingPointHeader: {
    minHeight: 28,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  samplingPointTitle: { flex: 1, minWidth: 0, color: SOIL_UI.text },
  samplingPointReason: { color: "#3F5148", lineHeight: 21 },
  zoneBadge: {
    maxWidth: "45%",
    borderRadius: 999,
    backgroundColor: SOIL_UI.greenSoft,
    paddingHorizontal: 9,
    paddingVertical: 4,
  },
  zoneBadgeText: { color: SOIL_UI.green },
  historyDate: {
    color: SOIL_UI.muted,
    paddingVertical: 7,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: SOIL_UI.border,
  },
  cachedNote: {
    minHeight: 46,
    borderRadius: 14,
    paddingHorizontal: 13,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: "#FFF3D6",
  },
  earthText: { color: SOIL_UI.earth, flex: 1 },
  errorCard: {
    padding: 14,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#E7AAA5",
    backgroundColor: "#FFF0EF",
  },
  errorText: { color: SOIL_UI.danger },
});
