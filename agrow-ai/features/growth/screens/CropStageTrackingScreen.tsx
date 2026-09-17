import { useRouter } from "expo-router";
import { ArrowLeft, History, Sprout } from "lucide-react-native";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { ScrollView, StyleSheet, View } from "react-native";

import {
  AgButton,
  AgCard,
  AgOfflineBanner,
  AgPressable,
  AgScreen,
  AgText,
} from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";
import { useFarm } from "@/features/farm/hooks/useFarms";
import { resolveHarvestCycleId } from "@/features/produce/harvestCycle";
import { useSelectedFarm } from "@/features/weather";
import { FarmSelector } from "@/features/weather/components/FarmSelector";
import { ApiError } from "@/types";

import {
  useGrowthTimeline,
  useStageHistory,
  useStageState,
  useStageTransition,
} from "../hooks/useGrowth";
import { submitStageTransition } from "../services/apiGrowthProvider";
import {
  pendingStageTransitions,
  queueStageTransition,
  syncPendingStageTransitions,
} from "../services/stageOfflineQueue";
import type { GrowthStage, StageTransitionInput } from "../types";

const STAGES: GrowthStage[] = [
  "germination",
  "seedling",
  "vegetative",
  "flowering",
  "fruiting",
  "maturity",
  "harvest",
];

export function CropStageTrackingScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const { farms, selected, select } = useSelectedFarm();
  const farmDetail = useFarm(selected?.id);
  const timeline = useGrowthTimeline(null, selected?.id ?? null);
  const cycle = timeline.data?.session ?? null;
  const hasMinimumCycleData = Boolean(
    farmDetail.data?.crop && farmDetail.data?.sowingDate,
  );
  const cycleId =
    selected && hasMinimumCycleData
      ? resolveHarvestCycleId(
          selected.id,
          farmDetail.data?.sowingDate,
          cycle?.id,
        )
      : null;
  const stage = useStageState(selected?.id, cycleId);
  const history = useStageHistory(stage.data?.id);
  const transition = useStageTransition();
  const [selectedStage, setSelectedStage] = useState<GrowthStage | null>(null);
  const [pending, setPending] = useState(false);
  const [conflict, setConflict] = useState(false);

  useEffect(() => {
    setPending(pendingStageTransitions().length > 0);
    void syncPendingStageTransitions(submitStageTransition).then((result) => {
      setPending(result.remaining > 0);
      if (result.synced > 0) {
        void stage.refetch();
      }
    });
  }, [selected?.id, cycleId]);

  const submit = async (event: "confirm" | "correct", value: GrowthStage) => {
    if (!selected || !cycleId) return;
    const input: StageTransitionInput = {
      farmId: selected.id,
      cropCycleId: cycleId,
      event,
      stage: value,
      expectedVersion: stage.data?.version ?? null,
      idempotencyKey: `stage-${event}-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      reason:
        event === "correct" ? "farmer_observation" : "farmer_confirmation",
    };
    try {
      await transition.mutateAsync(input);
      setSelectedStage(null);
      setPending(false);
      setConflict(false);
    } catch (error) {
      if (error instanceof ApiError && error.isNetwork) {
        queueStageTransition(input);
        setPending(true);
      } else if (error instanceof ApiError && error.status === 409) {
        setConflict(true);
      }
    }
  };

  return (
    <AgScreen padded={false} backgroundColor="#FBF8F0">
      <AgOfflineBanner />
      <ScrollView
        contentContainerStyle={{ padding: 20, gap: 16, paddingBottom: 80 }}
      >
        <AgPressable
          accessibilityRole="button"
          accessibilityLabel={t("common.back")}
          onPress={() => router.back()}
          hitSlop={8}
        >
          <ArrowLeft size={30} color="#101713" />
        </AgPressable>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
          <Sprout size={34} color={colors.primary} />
          <AgText variant="headingL" weight="bold" style={styles.ink}>
            {t("growth.stageTracking.workflowTitle")}
          </AgText>
        </View>
        <FarmSelector
          farms={farms}
          selectedId={selected?.id ?? null}
          onSelect={select}
          light
        />

        {!selected ? <AgText style={styles.body}>{t("growth.stageTracking.noFarm")}</AgText> : null}
        {selected && !hasMinimumCycleData && !farmDetail.isLoading ? (
          <AgCard className="gap-3" style={styles.card}>
            <AgText style={styles.body}>{t("growth.stageTracking.noCropCycle")}</AgText>
            <AgButton
              light
              title={t("harvestReadiness.startCycle")}
              onPress={() => router.replace(`/farm/${selected.id}/edit` as never)}
            />
          </AgCard>
        ) : null}
        {cycleId ? (
          <AgCard className="gap-3" style={styles.card}>
            <AgText variant="headingS" weight="bold" style={styles.ink}>
              {t("growth.stageTracking.currentStage")}
            </AgText>
            <AgText style={styles.body}>
              {stage.data?.confirmedStage
                ? t(`growth.stage.${stage.data.confirmedStage}`)
                : t("growth.stageTracking.noVerifiedModel")}
            </AgText>
            {stage.data?.suggestedStage ? (
              <AgButton
                title={t("growth.stageTracking.confirmSuggestion")}
                onPress={() =>
                  void submit("confirm", stage.data!.suggestedStage!)
                }
              />
            ) : null}
            <AgText variant="bodySmall" style={styles.muted}>
              {t("growth.stageTracking.farmerReportNotExpert")}
            </AgText>
            <View style={{ gap: 8 }}>
              {STAGES.map((item) => (
                <AgButton
                  key={item}
                  title={t(`growth.stage.${item}`)}
                  variant={selectedStage === item ? "primary" : "outline"}
                  onPress={() => setSelectedStage(item)}
                />
              ))}
            </View>
            {selectedStage ? (
              <AgButton
                title={t("growth.stageTracking.saveCorrection")}
                onPress={() => void submit("correct", selectedStage)}
                loading={transition.isPending}
              />
            ) : null}
            {pending ? (
              <AgText style={styles.muted}>
                {t("growth.stageTracking.pendingSync")}
              </AgText>
            ) : null}
            {conflict ? (
              <AgText color="danger">
                {t("growth.stageTracking.conflict")}
              </AgText>
            ) : null}
          </AgCard>
        ) : null}

        {history.data?.length ? (
          <AgCard className="gap-2" style={styles.card}>
            <View style={{ flexDirection: "row", gap: 8 }}>
              <History size={20} color={colors.primary} />
              <AgText weight="bold" style={styles.ink}>{t("growth.stageTracking.history")}</AgText>
            </View>
            {history.data.map((item) => (
              <AgText key={item.id} variant="bodySmall" style={styles.body}>
                {item.stage ? t(`growth.stage.${item.stage}`) : item.nextState}{" "}
                ·{" "}
                {item.event === "correct"
                  ? t("growth.stageTracking.farmerCorrected")
                  : t("growth.stageTracking.farmerConfirmed")}
              </AgText>
            ))}
          </AgCard>
        ) : null}
      </ScrollView>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: '#FFFFFF', borderColor: '#D7DDCF' },
  ink: { color: '#101713' },
  body: { color: '#26332B' },
  muted: { color: '#536158' },
});
