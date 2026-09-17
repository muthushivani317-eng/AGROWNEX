import { useMutation, useQuery } from "@tanstack/react-query";
import { type Href, useRouter } from "expo-router";
import {
  AlertTriangle,
  ArrowLeft,
  CalendarClock,
  CheckCircle2,
  ChevronRight,
  CloudSun,
  RefreshCw,
  ShieldAlert,
  Sprout,
} from "lucide-react-native";
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, View } from "react-native";
import { useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { AgButton, AgScreen, AgText } from "@/components/ui";
import { ApiError } from "@/types";
import { FarmSelector } from "@/features/weather/components/FarmSelector";
import { useSelectedFarm } from "@/features/weather";
import { useGrowthTimeline } from "@/features/growth";
import { evaluateRisk, getCurrentRisk, getRiskHistory } from "./api";
import { diseaseRiskErrorMessageKey } from "./errors";
import { type DiseaseRiskAlert, farmerMessageOrFallback } from "./types";

const C = {
  ink: "#173B2B",
  muted: "#5F6F67",
  bg: "#F8F5E9",
  paper: "#FFFDF8",
  border: "#DDD7C6",
  green: "#176B36",
  amber: "#B77908",
  amberBg: "#FFF4D8",
  greenBg: "#EAF3E5",
};

function openAssessment(router: ReturnType<typeof useRouter>, id: string) {
  router.push({
    pathname: "/disease-risk/[id]",
    params: { id },
  } as unknown as Href);
}

export function formatAssessmentTimestamp(value: string, language = "en") {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleString(language.startsWith("ta") ? "ta-IN" : "en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function AssessmentCard({
  item,
  onPress,
  compact = false,
}: {
  item: DiseaseRiskAlert;
  onPress: () => void;
  compact?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const alert = item.riskLevel != null || item.diseaseKey != null;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={farmerMessageOrFallback(item.farmerMessageKey, t)}
      onPress={onPress}
      style={[
        styles.assessmentCard,
        compact && styles.compactAssessment,
      ]}
    >
      <View
        style={[
          styles.iconTile,
          { backgroundColor: alert ? C.amberBg : C.greenBg },
        ]}
      >
        {alert ? (
          <AlertTriangle size={24} color={C.amber} />
        ) : (
          <CheckCircle2 size={24} color={C.green} />
        )}
      </View>
      <View style={styles.flexCopy}>
        <AgText
          variant={compact ? "body" : "headingS"}
          weight="semibold"
          style={styles.ink}
        >
          {farmerMessageOrFallback(item.farmerMessageKey, t)}
        </AgText>
        <View style={styles.metaRow}>
          <Sprout size={16} color={C.muted} />
          <AgText variant="bodySmall" style={styles.muted}>
            {t("diseaseRisk.crop", { crop: item.crop })}
          </AgText>
        </View>
        <View style={styles.metaRow}>
          <CalendarClock size={16} color={C.muted} />
          <AgText variant="bodySmall" style={styles.muted}>
            {item.cached
              ? t("diseaseRisk.cached", {
                  time: formatAssessmentTimestamp(
                    item.generatedAt,
                    i18n.resolvedLanguage ?? i18n.language,
                  ),
                })
              : t("diseaseRisk.current")}
          </AgText>
        </View>
      </View>
      <View style={styles.arrowCircle}>
        <ChevronRight size={20} color={C.green} />
      </View>
    </Pressable>
  );
}

function StateCard({
  icon,
  title,
  hint,
  action,
}: {
  icon: ReactNode;
  title: string;
  hint: string;
  action?: ReactNode;
}) {
  return (
    <View style={styles.stateCard}>
      <View style={styles.stateIcon}>{icon}</View>
      <AgText variant="headingS" weight="semibold" center style={styles.ink}>
        {title}
      </AgText>
      <AgText center style={styles.muted}>
        {hint}
      </AgText>
      {action}
    </View>
  );
}

export function DiseaseRiskScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const farm = useSelectedFarm();
  const farmId = farm.selected?.id;
  const refreshLock = useRef(false);
  const evaluationLock = useRef(false);
  const [refreshing, setRefreshing] = useState(false);
  const growthTimeline = useGrowthTimeline(null, farmId ?? null);
  const cropCycleId = growthTimeline.data?.session?.id ?? null;
  const growthFailed = growthTimeline.isError && !(
    growthTimeline.error instanceof ApiError &&
    growthTimeline.error.status === 404 &&
    growthTimeline.error.errorCode === "growth_session_not_found"
  );
  const current = useQuery({
    queryKey: ["disease-risk", "current", farmId],
    enabled: Boolean(farmId),
    queryFn: () => getCurrentRisk(farmId!),
    refetchOnMount: "always",
    retry: false,
  });
  const history = useQuery({
    queryKey: ["disease-risk", "history", farmId],
    enabled: Boolean(farmId),
    queryFn: () => getRiskHistory(farmId!),
    retry: false,
  });
  const evaluate = useMutation({
    mutationFn: () => evaluateRisk(farmId!, cropCycleId!),
    onSuccess: (result) => {
      void current.refetch();
      void history.refetch();
      openAssessment(router, result.id);
    },
    onSettled: () => { evaluationLock.current = false; },
  });
  const refresh = async () => {
    if (refreshLock.current || evaluate.isPending) return;
    refreshLock.current = true;
    setRefreshing(true);
    try {
      await Promise.all([
        farm.refetch(),
        ...(farmId ? [current.refetch(), history.refetch(), growthTimeline.refetch()] : []),
      ]);
    } finally { refreshLock.current = false; setRefreshing(false); }
  };
  const checkDisabled = evaluate.isPending || refreshing || farm.isError || growthTimeline.isFetching || growthTimeline.isError || !cropCycleId;
  const loading = farm.isLoading || current.isLoading;
  const failed = farm.isError || current.isError;
  const loadError = farm.isError ? farm.error : current.error;
  const earlierAssessments = (history.data ?? []).filter(
    (item) => item.id !== current.data?.id,
  );

  return (
    <AgScreen
      padded={false}
      backgroundColor={C.bg}
      testID="disease-risk-screen"
    >
      <ScrollView contentContainerStyle={[styles.page, { paddingHorizontal: 20 }]}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => void refresh()} tintColor={C.green} />}>
      <View style={styles.topRow}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t("common.back")}
          onPress={() => router.back()}
          hitSlop={10}
          style={styles.backButton}
        >
          <ArrowLeft size={27} color={C.ink} />
        </Pressable>
        <View style={styles.brandIcon}>
          <ShieldAlert size={27} color={C.green} />
        </View>
        <AgText variant="label" weight="bold" style={styles.eyebrow}>
          {t("diseaseRisk.eyebrow")}
        </AgText>
      </View>
      <AgText variant="headingXL" weight="bold" style={styles.ink}>
        {t("diseaseRisk.title")}
      </AgText>
      <AgText variant="bodyLarge" style={styles.muted}>
        {t("diseaseRisk.subtitle")}
      </AgText>

      <View style={styles.safetyCard}>
        <View style={styles.safetyIcon}>
          <ShieldAlert size={24} color={C.amber} />
        </View>
        <View style={styles.flexCopy}>
          <AgText weight="semibold" style={styles.ink}>
            {t("diseaseRisk.safetyTitle")}
          </AgText>
          <AgText variant="bodySmall" style={styles.muted}>
            {t("diseaseRisk.notDiagnosis")}
          </AgText>
        </View>
      </View>
      <FarmSelector
        farms={farm.farms}
        selectedId={farmId ?? null}
        onSelect={(id) => { if (!evaluate.isPending) { evaluate.reset(); farm.select(id); } }}
        light
      />

      {farmId ? (
        <View style={styles.actionCard}>
          <View style={styles.actionHeading}>
            <View style={styles.scanIcon}>
              <CloudSun size={26} color={C.green} />
            </View>
            <View style={styles.flexCopy}>
              <AgText variant="headingS" weight="semibold" style={styles.ink}>
                {t("diseaseRisk.checkTitle")}
              </AgText>
              <AgText variant="bodySmall" style={styles.muted}>
                {t("diseaseRisk.checkHint")}
              </AgText>
            </View>
          </View>
          <AgButton
            light
            size="lg"
            title={t("diseaseRisk.checkNow")}
            loading={evaluate.isPending}
            disabled={checkDisabled}
            onPress={() => {
              if (checkDisabled || evaluationLock.current) return;
              evaluationLock.current = true;
              evaluate.mutate();
            }}
            rightIcon={
              !evaluate.isPending ? (
                <RefreshCw size={21} color="#101713" />
              ) : null
            }
          />
          {growthTimeline.isLoading ? <ActivityIndicator color={C.green} /> : null}
          {growthFailed ? <View accessibilityRole="alert">
            <AgText color="danger">{t(diseaseRiskErrorMessageKey(growthTimeline.error))}</AgText>
            <AgButton title={t("common.retry")} disabled={growthTimeline.isFetching} onPress={() => void growthTimeline.refetch()} />
          </View> : null}
          {!growthTimeline.isLoading && !growthFailed && !cropCycleId ? (
            <AgText color="danger" variant="bodySmall">
              {t("diseaseRisk.noCropCycle")}
            </AgText>
          ) : null}
          {evaluate.isError ? (
            <AgText color="danger" variant="bodySmall">
              {t(diseaseRiskErrorMessageKey(evaluate.error))}
            </AgText>
          ) : null}
        </View>
      ) : null}

      {loading ? (
        <StateCard
          icon={<ActivityIndicator size="large" color={C.green} />}
          title={t("diseaseRisk.loadingTitle")}
          hint={t("diseaseRisk.loadingHint")}
        />
      ) : null}
      {failed ? (
        <StateCard
          icon={<AlertTriangle size={30} color={C.amber} />}
          title={t("diseaseRisk.errorTitle")}
          hint={t(diseaseRiskErrorMessageKey(loadError))}
          action={
            <AgButton
              light
              variant="outline"
              title={t("common.retry")}
              disabled={refreshing}
              onPress={() => void refresh()}
              leftIcon={<RefreshCw size={20} color={C.green} />}
            />
          }
        />
      ) : null}
      {!farm.isLoading && !farm.isError && !farm.selected ? (
        <StateCard
          icon={<Sprout size={31} color={C.green} />}
          title={t("diseaseRisk.noFarmTitle")}
          hint={t("diseaseRisk.noFarm")}
        />
      ) : null}
      {farm.selected && !loading && !failed && !current.data ? (
        <StateCard
          icon={<ShieldAlert size={31} color={C.green} />}
          title={t("diseaseRisk.emptyTitle")}
          hint={t("diseaseRisk.emptyHint")}
        />
      ) : null}

      {current.data && !failed ? (
        <View style={styles.section}>
          <View style={styles.sectionHeading}>
            <AgText variant="headingM" weight="bold" style={styles.ink}>
              {t("diseaseRisk.latestTitle")}
            </AgText>
            <View style={styles.liveBadge}>
              <View style={styles.liveDot} />
              <AgText variant="caption" weight="bold" style={styles.greenText}>
                {t("diseaseRisk.savedBadge")}
              </AgText>
            </View>
          </View>
          <AssessmentCard
            item={current.data}
            onPress={() => openAssessment(router, current.data!.id)}
          />
          {current.data.ruleVerificationStatus ===
          "SOURCED_PUBLIC_REFERENCE" ? (
            <AgText variant="bodySmall" style={styles.sourceNotice}>
              {t("diseaseRisk.sourcedNotReviewedNotice")}
            </AgText>
          ) : null}
        </View>
      ) : null}

      {farmId && history.isLoading ? <ActivityIndicator color={C.green} /> : null}
      {farmId && history.isError ? <StateCard
        icon={<AlertTriangle size={30} color={C.amber} />}
        title={t("diseaseRisk.history")}
        hint={t(diseaseRiskErrorMessageKey(history.error))}
        action={<AgButton title={t("common.retry")} disabled={history.isFetching} onPress={() => void history.refetch()} />}
      /> : null}
      {earlierAssessments.length > 0 && !history.isError ? (
        <View style={styles.section}>
          <View style={styles.sectionHeading}>
            <AgText variant="headingM" weight="bold" style={styles.ink}>
              {t("diseaseRisk.history")}
            </AgText>
            <AgText variant="bodySmall" style={styles.muted}>
              {t("diseaseRisk.historyCount", {
                count: earlierAssessments.length,
              })}
            </AgText>
          </View>
          <View style={styles.historyList}>
            {earlierAssessments.map((item) => (
              <AssessmentCard
                key={item.id}
                compact
                item={item}
                onPress={() => openAssessment(router, item.id)}
              />
            ))}
          </View>
        </View>
      ) : null}
      </ScrollView>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  page: { paddingTop: 8, paddingBottom: 48, gap: 16 },
  flexCopy: { flex: 1, gap: 5 },
  ink: { color: C.ink },
  muted: { color: C.muted },
  greenText: { color: C.green },
  pressed: { opacity: 0.72 },
  topRow: {
    minHeight: 52,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  backButton: {
    width: 48,
    height: 48,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.paper,
    alignItems: "center",
    justifyContent: "center",
  },
  brandIcon: {
    width: 48,
    height: 48,
    borderRadius: 16,
    backgroundColor: C.greenBg,
    alignItems: "center",
    justifyContent: "center",
  },
  eyebrow: { color: C.amber, letterSpacing: 0.9, textTransform: "uppercase" },
  safetyCard: {
    flexDirection: "row",
    gap: 12,
    padding: 16,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#E8CB83",
    backgroundColor: C.amberBg,
  },
  safetyIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: C.paper,
    alignItems: "center",
    justifyContent: "center",
  },
  actionCard: {
    gap: 16,
    padding: 18,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.paper,
  },
  actionHeading: { flexDirection: "row", alignItems: "center", gap: 12 },
  scanIcon: {
    width: 50,
    height: 50,
    borderRadius: 17,
    backgroundColor: C.greenBg,
    alignItems: "center",
    justifyContent: "center",
  },
  stateCard: {
    minHeight: 250,
    padding: 24,
    gap: 14,
    borderRadius: 26,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.paper,
    alignItems: "center",
    justifyContent: "center",
  },
  stateIcon: {
    width: 82,
    height: 82,
    borderRadius: 28,
    backgroundColor: C.greenBg,
    alignItems: "center",
    justifyContent: "center",
  },
  section: { gap: 12 },
  sectionHeading: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  liveBadge: {
    minHeight: 32,
    paddingHorizontal: 11,
    borderRadius: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    backgroundColor: C.greenBg,
  },
  liveDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: C.green },
  assessmentCard: {
    minHeight: 150,
    padding: 16,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.paper,
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 13,
    paddingRight: 68,
    position: "relative",
    elevation: 1,
  },
  compactAssessment: { minHeight: 124 },
  iconTile: {
    width: 52,
    height: 52,
    borderRadius: 17,
    alignItems: "center",
    justifyContent: "center",
  },
  metaRow: { flexDirection: "row", alignItems: "flex-start", gap: 7 },
  arrowCircle: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: C.greenBg,
    alignItems: "center",
    justifyContent: "center",
    position: "absolute",
    right: 16,
    top: 16,
  },
  sourceNotice: {
    color: "#745B22",
    backgroundColor: C.amberBg,
    borderRadius: 14,
    padding: 12,
  },
  historyList: { gap: 10 },
});
