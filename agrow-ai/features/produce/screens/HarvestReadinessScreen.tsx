import { useRouter } from "expo-router";
import {
  AlertTriangle,
  ArrowLeft,
  CalendarClock,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  CloudOff,
  RefreshCw,
  ShieldCheck,
  Sprout,
  Wheat,
} from "lucide-react-native";
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, View } from "react-native";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { AgButton, AgScreen, AgText } from "@/components/ui";
import { useFarm } from "@/features/farm/hooks/useFarms";
import { useGrowthTimeline } from "@/features/growth/hooks/useGrowth";
import { useSelectedFarm } from "@/features/weather";
import { FarmSelector } from "@/features/weather/components/FarmSelector";

import type { HarvestReadinessState } from "../harvestReadiness";
import { resolveHarvestCycleId } from "../harvestCycle";
import { isMissingGrowthSession } from "../harvestReadinessErrors";
import {
  useConfirmHarvestReadiness,
  useEvaluateHarvestReadiness,
  useHarvestReadiness,
  useHarvestReadinessHistory,
} from "../hooks/useHarvestReadiness";

const C = {
  ink: "#173B2B",
  muted: "#5F6F67",
  bg: "#F8F5E9",
  paper: "#FFFDF8",
  border: "#DDD7C6",
  green: "#176B36",
  greenBg: "#EAF3E5",
  gold: "#B77908",
  goldBg: "#FFF4D8",
  red: "#B43A32",
  redBg: "#FCEAE6",
};

function toneFor(state: HarvestReadinessState) {
  if (state === "farmer_confirmed_ready" || state === "possibly_ready") {
    return { color: C.green, background: C.greenBg, icon: CheckCircle2 };
  }
  if (state === "not_ready" || state === "farmer_confirmed_not_ready") {
    return { color: C.red, background: C.redBg, icon: AlertTriangle };
  }
  return { color: C.gold, background: C.goldBg, icon: ClipboardCheck };
}

function friendlyEvidence(
  value: string,
  t: ReturnType<typeof useTranslation>["t"],
) {
  const key = `harvestReadiness.evidence.${value}`;
  const translated = t(key);
  return translated === key ? t("harvestReadiness.evidence.other") : translated;
}

function StateCard({
  icon,
  title,
  hint,
  children,
}: {
  icon: ReactNode;
  title: string;
  hint: string;
  children?: ReactNode;
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
      {children}
    </View>
  );
}

export function HarvestReadinessScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const farms = useSelectedFarm();
  const farmDetail = useFarm(farms.selected?.id);
  const timeline = useGrowthTimeline(null, farms.selected?.id ?? null, Boolean(farms.selected));
  const refreshLock = useRef(false);
  const mutationLock = useRef(false);
  const [refreshing, setRefreshing] = useState(false);
  const hasMinimumCycleData = Boolean(
    farmDetail.data?.crop && farmDetail.data?.sowingDate,
  );
  const cycleId = farms.selected && hasMinimumCycleData
    ? resolveHarvestCycleId(
        farms.selected.id,
        farmDetail.data?.sowingDate,
        timeline.data?.session?.id,
      )
    : null;
  const readiness = useHarvestReadiness(farms.selected?.id, cycleId);
  const evaluate = useEvaluateHarvestReadiness();
  const confirm = useConfirmHarvestReadiness();
  const value = readiness.data;
  const history = useHarvestReadinessHistory(value?.id);
  const state = value?.state ?? "not_assessed";
  const tone = toneFor(state);
  const StatusIcon = tone.icon;
  const missingGrowthSession = isMissingGrowthSession(timeline.error);
  const loading =
    farms.isLoading ||
    farmDetail.isLoading ||
    timeline.isLoading ||
    readiness.isLoading;
  const error =
    farms.isError ||
    farmDetail.isError ||
    (timeline.isError && !missingGrowthSession) ||
    readiness.isError;

  const busy = evaluate.isPending || confirm.isPending;
  useEffect(() => {
    evaluate.reset();
    confirm.reset();
  }, [farms.selected?.id, cycleId]); // Clear feedback belonging to a previous farm/cycle.

  const refresh = async () => {
    if (refreshLock.current || mutationLock.current) return;
    refreshLock.current = true;
    setRefreshing(true);
    try {
      await Promise.allSettled([
        farms.refetch(),
        ...(farms.selected ? [farmDetail.refetch(), timeline.refetch()] : []),
        ...(cycleId ? [readiness.refetch()] : []),
        ...(value?.id ? [history.refetch()] : []),
      ]);
    } finally {
      refreshLock.current = false;
      setRefreshing(false);
    }
  };

  const check = () => {
    if (!farms.selected || !cycleId || loading || error || refreshLock.current || mutationLock.current) return;
    mutationLock.current = true;
    evaluate.mutate({ farmId: farms.selected.id, cycleId }, {
      onSettled: () => { mutationLock.current = false; },
    });
  };
  const confirmReady = (ready: boolean) => {
    if (!value?.id || value.cached || state !== "awaiting_farmer_confirmation" || loading || error || refreshLock.current || mutationLock.current) return;
    mutationLock.current = true;
    confirm.mutate({ id: value.id, ready }, {
      onSettled: () => { mutationLock.current = false; },
    });
  };

  return (
    <AgScreen
      padded={false}
      backgroundColor={C.bg}
      testID="harvest-readiness-screen"
    >
      <ScrollView
        contentContainerStyle={styles.page}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={C.green} />}
      >
      <View style={styles.headerRow}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t("common.back")}
          hitSlop={10}
          onPress={() => router.back()}
          style={styles.backButton}
        >
          <ArrowLeft size={27} color={C.ink} />
        </Pressable>
        <View style={styles.brandIcon}>
          <Wheat size={28} color={C.gold} />
        </View>
        <AgText variant="label" weight="bold" style={styles.eyebrow}>
          {t("harvestReadiness.eyebrow")}
        </AgText>
      </View>

      <AgText variant="headingXL" weight="bold" style={styles.ink}>
        {t("harvestReadiness.title")}
      </AgText>
      <AgText variant="bodyLarge" style={styles.muted}>
        {t("harvestReadiness.subtitle")}
      </AgText>

      <View style={styles.safetyCard}>
        <View style={styles.safetyIcon}>
          <ShieldCheck size={24} color={C.gold} />
        </View>
        <View style={styles.flexCopy}>
          <AgText weight="semibold" style={styles.ink}>
            {t("harvestReadiness.safetyTitle")}
          </AgText>
          <AgText variant="bodySmall" style={styles.muted}>
            {t("harvestReadiness.noDatePromise")}
          </AgText>
        </View>
      </View>

      <FarmSelector
        farms={farms.farms}
        selectedId={farms.selected?.id ?? null}
        onSelect={(id) => { if (!mutationLock.current && !refreshLock.current) farms.select(id); }}
        light
      />

      {loading ? (
        <StateCard
          icon={<ActivityIndicator size="large" color={C.green} />}
          title={t("harvestReadiness.loadingTitle")}
          hint={t("harvestReadiness.loadingHint")}
        />
      ) : null}

      {!loading && error ? (
        <StateCard
          icon={<CloudOff size={31} color={C.gold} />}
          title={t("harvestReadiness.errorTitle")}
          hint={t("harvestReadiness.unavailable")}
        >
          <AgButton
            light
            variant="outline"
            title={t("common.retry")}
            leftIcon={<RefreshCw size={20} color={C.green} />}
            onPress={refresh}
            disabled={refreshing}
          />
        </StateCard>
      ) : null}

      {!loading && !error && !farms.selected ? (
        <StateCard
          icon={<Sprout size={31} color={C.green} />}
          title={t("harvestReadiness.noFarmTitle")}
          hint={t("harvestReadiness.noFarm")}
        />
      ) : null}

      {!loading && !error && farms.selected && !hasMinimumCycleData ? (
        <StateCard
          icon={<CalendarClock size={31} color={C.gold} />}
          title={t("harvestReadiness.noCycleTitle")}
          hint={t("harvestReadiness.noCycle")}
        >
          <AgButton
            light
            title={t("harvestReadiness.startCycle")}
            onPress={() =>
              router.push(`/farm/${farms.selected!.id}/edit` as never)
            }
          />
        </StateCard>
      ) : null}

      {!loading && !error && cycleId ? (
        <>
          <View style={styles.sectionHeading}>
            <AgText variant="headingM" weight="bold" style={styles.ink}>
              {t("harvestReadiness.status")}
            </AgText>
            {value?.cached ? (
              <View style={styles.cachedBadge}>
                <AgText variant="caption" weight="bold" style={styles.goldText}>
                  {t("harvestReadiness.savedBadge")}
                </AgText>
              </View>
            ) : null}
          </View>

          <View style={styles.readinessCard}>
            <View style={styles.statusTop}>
              <View
                style={[
                  styles.statusIcon,
                  { backgroundColor: tone.background },
                ]}
              >
                <StatusIcon size={30} color={tone.color} />
              </View>
              <View style={styles.flexCopy}>
                <AgText
                  variant="label"
                  weight="bold"
                  style={{ color: tone.color }}
                >
                  {t("harvestReadiness.statusLabel")}
                </AgText>
                <AgText variant="headingM" weight="bold" style={styles.ink}>
                  {t(`harvestReadiness.states.${state}`)}
                </AgText>
              </View>
            </View>

            {value?.cached ? (
              <AgText variant="bodySmall" style={styles.savedNotice}>
                {t("harvestReadiness.cached")}
              </AgText>
            ) : null}

            {value?.evidenceObserved.length ? (
              <View style={styles.evidenceSection}>
                <AgText weight="semibold" style={styles.ink}>
                  {t("harvestReadiness.availableEvidence")}
                </AgText>
                {value.evidenceObserved.map((item) => (
                  <View key={item} style={styles.evidenceRow}>
                    <CheckCircle2 size={19} color={C.green} />
                    <AgText style={styles.evidenceText}>
                      {friendlyEvidence(item, t)}
                    </AgText>
                  </View>
                ))}
              </View>
            ) : null}

            {value?.missing.length ? (
              <View style={styles.missingCard}>
                <AlertTriangle size={21} color={C.gold} />
                <View style={styles.flexCopy}>
                  <AgText weight="semibold" style={styles.ink}>
                    {t("harvestReadiness.missingEvidence")}
                  </AgText>
                  {value.missing.map((item) => (
                    <AgText key={item} variant="bodySmall" style={styles.muted}>
                      {friendlyEvidence(item, t)}
                    </AgText>
                  ))}
                </View>
              </View>
            ) : null}

            {value?.conflicts.length ? (
              <View style={styles.conflictCard}>
                <AlertTriangle size={21} color={C.red} />
                <AgText style={styles.conflictText}>
                  {t("harvestReadiness.conflictHint")}
                </AgText>
              </View>
            ) : null}

            <AgButton
              light
              size="lg"
              title={t("harvestReadiness.check")}
              loading={evaluate.isPending}
              disabled={busy || refreshing}
              onPress={check}
              leftIcon={
                !evaluate.isPending ? (
                  <RefreshCw size={21} color="#101713" />
                ) : null
              }
              rightIcon={
                !evaluate.isPending ? (
                  <ChevronRight size={21} color="#101713" />
                ) : null
              }
            />
            {evaluate.isError ? (
              <AgText color="danger" variant="bodySmall">
                {t("harvestReadiness.unavailable")}
              </AgText>
            ) : null}
          </View>

          {value?.state === "awaiting_farmer_confirmation" && value.id && !value.cached ? (
            <View style={styles.confirmCard}>
              <View style={styles.confirmTop}>
                <View style={styles.confirmIcon}>
                  <ClipboardCheck size={26} color={C.green} />
                </View>
                <View style={styles.flexCopy}>
                  <AgText
                    variant="headingS"
                    weight="semibold"
                    style={styles.ink}
                  >
                    {t("harvestReadiness.confirmTitle")}
                  </AgText>
                  <AgText variant="bodySmall" style={styles.muted}>
                    {t("harvestReadiness.confirmHint")}
                  </AgText>
                </View>
              </View>
              <AgButton
                light
                variant="success"
                title={t("harvestReadiness.confirmReady")}
                loading={confirm.isPending}
                disabled={busy || refreshing}
                onPress={() => confirmReady(true)}
              />
              <AgButton
                light
                variant="outline"
                title={t("harvestReadiness.confirmNotReady")}
                disabled={busy || refreshing}
                onPress={() => confirmReady(false)}
              />
              {confirm.isError ? (
                <AgText color="danger" variant="bodySmall">
                  {t("harvestReadiness.confirmError")}
                </AgText>
              ) : null}
            </View>
          ) : null}
        </>
      ) : null}

      {!loading && !error && value?.id && history.isLoading ? (
        <StateCard icon={<ActivityIndicator color={C.green} />} title={t("harvestReadiness.history")} hint={t("common.loading")} />
      ) : null}
      {!loading && !error && value?.id && history.isError ? (
        <StateCard icon={<CloudOff size={31} color={C.gold} />} title={t("harvestReadiness.history")} hint={t("harvestReadiness.unavailable")}>
          <AgButton light title={t("common.retry")} disabled={refreshing} onPress={refresh} />
        </StateCard>
      ) : null}
      {!loading && !error && !history.isError && history.data?.length ? (
        <View style={styles.historySection}>
          <View style={styles.sectionHeading}>
            <AgText variant="headingM" weight="bold" style={styles.ink}>
              {t("harvestReadiness.history")}
            </AgText>
            <AgText variant="bodySmall" style={styles.muted}>
              {t("harvestReadiness.historyCount", {
                count: history.data.length,
              })}
            </AgText>
          </View>
          {history.data.map((entry) => {
            const historyTone = toneFor(
              entry.nextState as HarvestReadinessState,
            );
            return (
              <View key={entry.id} style={styles.historyRow}>
                <View
                  style={[
                    styles.historyDot,
                    { backgroundColor: historyTone.color },
                  ]}
                />
                <View style={styles.flexCopy}>
                  <AgText weight="semibold" style={styles.ink}>
                    {t(`harvestReadiness.states.${entry.nextState}`)}
                  </AgText>
                  <AgText variant="bodySmall" style={styles.muted}>
                    {entry.createdAt}
                  </AgText>
                </View>
              </View>
            );
          })}
        </View>
      ) : null}
      </ScrollView>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  page: { paddingHorizontal: 20, paddingTop: 8, paddingBottom: 48, gap: 16 },
  ink: { color: C.ink },
  muted: { color: C.muted },
  goldText: { color: C.gold },
  flexCopy: { flex: 1, gap: 5 },
  evidenceText: { color: C.ink, flex: 1 },
  conflictText: { color: C.red, flex: 1 },
  pressed: { opacity: 0.72 },
  headerRow: {
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
    backgroundColor: C.goldBg,
    alignItems: "center",
    justifyContent: "center",
  },
  eyebrow: { color: C.gold, letterSpacing: 0.9, textTransform: "uppercase" },
  safetyCard: {
    flexDirection: "row",
    gap: 12,
    padding: 16,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#E8CB83",
    backgroundColor: C.goldBg,
  },
  safetyIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: C.paper,
    alignItems: "center",
    justifyContent: "center",
  },
  stateCard: {
    minHeight: 260,
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
  sectionHeading: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  cachedBadge: {
    minHeight: 32,
    paddingHorizontal: 12,
    borderRadius: 16,
    backgroundColor: C.goldBg,
    alignItems: "center",
    justifyContent: "center",
  },
  readinessCard: {
    padding: 20,
    gap: 16,
    borderRadius: 26,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.paper,
  },
  statusTop: { flexDirection: "row", alignItems: "flex-start", gap: 14 },
  statusIcon: {
    width: 62,
    height: 62,
    borderRadius: 21,
    alignItems: "center",
    justifyContent: "center",
  },
  savedNotice: {
    color: "#745B22",
    backgroundColor: C.goldBg,
    padding: 12,
    borderRadius: 14,
  },
  evidenceSection: { gap: 10 },
  evidenceRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  missingCard: {
    padding: 14,
    borderRadius: 17,
    flexDirection: "row",
    gap: 11,
    backgroundColor: C.goldBg,
  },
  conflictCard: {
    padding: 14,
    borderRadius: 17,
    flexDirection: "row",
    gap: 11,
    backgroundColor: C.redBg,
  },
  confirmCard: {
    padding: 20,
    gap: 12,
    borderRadius: 26,
    borderWidth: 1,
    borderColor: "#BFD4BE",
    backgroundColor: "#EEF5E9",
  },
  confirmTop: { flexDirection: "row", alignItems: "center", gap: 13 },
  confirmIcon: {
    width: 50,
    height: 50,
    borderRadius: 17,
    backgroundColor: C.paper,
    alignItems: "center",
    justifyContent: "center",
  },
  historySection: { gap: 10 },
  historyRow: {
    minHeight: 78,
    padding: 15,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.paper,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  historyDot: { width: 12, height: 12, borderRadius: 6 },
});
