import { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  TouchableOpacity,
  View,
} from "react-native";
import { Image } from "expo-image";
import { useRouter } from "expo-router";
import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  ChevronDown,
  ChevronUp,
  LandPlot,
  Leaf,
  MapPinned,
  Plus,
  Sprout,
} from "lucide-react-native";
import { useTranslation } from "react-i18next";

import {
  AgBadge,
  AgDatePicker,
  AgErrorState,
  AgInput,
  AgScreen,
  AgSkeleton,
  AgText,
  CropSelector,
} from "@/components/ui";
import { COMMON_CROPS } from "@/constants/crops";
import { useLanguage } from "@/hooks/useLanguage";

import {
  useCreateOrganicCropCycle,
  useCreateOrganicPlot,
  useOrganicCropCyclePlan,
  useOrganicCropCycles,
  useOrganicPlots,
} from "../hooks/useOrganicConversion";
import type {
  OrganicCropCycle,
  OrganicPlot,
} from "../services/organicConversionApi";

const C = {
  bg: "#F7FAF3",
  card: "#FFFFFF",
  green: "#13753B",
  greenDark: "#093D2D",
  greenSoft: "#EBF7E8",
  text: "#102F2C",
  slate: "#657084",
  border: "#DCE5DF",
  orange: "#C85115",
  orangeSoft: "#FFF0DE",
} as const;

const landscapeImage = require("../../../assets/images/organic-dashboard-landscape.png");

function cropLabel(cropId: string, language: string): string {
  const crop = COMMON_CROPS.find((item) => item.id === cropId);
  if (!crop) return cropId;
  return language === "ta" ? crop.ta : crop.en;
}

function SaveButton({
  title,
  onPress,
  loading,
  disabled,
}: {
  title: string;
  onPress: () => void;
  loading: boolean;
  disabled?: boolean;
}) {
  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.82}
      disabled={loading || disabled}
      accessibilityRole="button"
      accessibilityState={{ disabled: loading || disabled }}
      style={[styles.saveButton, (loading || disabled) && styles.disabled]}
    >
      {loading ? (
        <ActivityIndicator color="#FFFFFF" />
      ) : (
        <>
          <AgText weight="bold" style={styles.saveText}>
            {title}
          </AgText>
          <ArrowRight size={26} color="#FFFFFF" strokeWidth={2.5} />
        </>
      )}
    </TouchableOpacity>
  );
}

/** Plot and crop-cycle capture backed by the reviewed organic-plan API. */
export function OrganicConversionPlanScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const plotsQuery = useOrganicPlots(farmId);
  const createPlot = useCreateOrganicPlot(farmId);
  const [addingPlot, setAddingPlot] = useState(false);
  const [plotName, setPlotName] = useState("");
  const [plotArea, setPlotArea] = useState("");

  const submitPlot = () => {
    if (!plotName.trim()) return;
    createPlot.mutate(
      {
        name: plotName.trim(),
        area_hectares: plotArea.trim() ? Number(plotArea.trim()) : null,
      },
      {
        onSuccess: () => {
          setAddingPlot(false);
          setPlotName("");
          setPlotArea("");
        },
      },
    );
  };

  return (
    <AgScreen
      scroll
      padded={false}
      keyboardAvoiding
      backgroundColor={C.bg}
      contentContainerStyle={styles.screen}
    >
      <View style={styles.hero}>
        <Image
          source={landscapeImage}
          contentFit="cover"
          style={styles.heroImage}
        />
        <View style={styles.heroWash} />
        <TouchableOpacity
          onPress={() => router.back()}
          activeOpacity={0.75}
          accessibilityRole="button"
          accessibilityLabel={t("common.back")}
          style={styles.backButton}
        >
          <ArrowLeft size={28} color={C.greenDark} strokeWidth={2.5} />
        </TouchableOpacity>

        <AgText weight="bold" style={styles.heroTitle}>
          {t("organic.conversionPlanTitle")}
        </AgText>
        <View style={styles.heroIntroRow}>
          <TouchableOpacity
            onPress={() => setAddingPlot((current) => !current)}
            activeOpacity={0.78}
            accessibilityRole="button"
            accessibilityLabel={t("organic.addPlot")}
            style={styles.addPlotCircle}
          >
            <Plus size={34} color="#FFFFFF" strokeWidth={2.2} />
          </TouchableOpacity>
          <AgText style={styles.heroIntro}>
            {t("organic.conversionPlanIntro")}
          </AgText>
        </View>
      </View>

      <View style={styles.pageContent}>
        {addingPlot ? (
          <View style={[styles.card, styles.newPlotCard]}>
            <View style={styles.formHeading}>
              <View style={styles.iconCircle}>
                <MapPinned size={29} color={C.green} strokeWidth={2.1} />
              </View>
              <View style={styles.headingCopy}>
                <AgText weight="bold" style={styles.formTitle}>
                  {t("organic.addPlot")}
                </AgText>
                <AgText style={styles.formHint}>
                  {t("organic.noPlotsMessage")}
                </AgText>
              </View>
            </View>
            <View style={styles.fieldGap}>
              <AgInput
                light
                label={t("organic.plotName")}
                value={plotName}
                onChangeText={setPlotName}
                fieldStyle={styles.inputField}
                labelStyle={styles.fieldLabel}
              />
              <AgInput
                light
                label={t("organic.plotAreaHectares")}
                value={plotArea}
                onChangeText={setPlotArea}
                keyboardType="decimal-pad"
                fieldStyle={styles.inputField}
                labelStyle={styles.fieldLabel}
              />
            </View>
            <SaveButton
              title={t("common.save")}
              onPress={submitPlot}
              loading={createPlot.isPending}
              disabled={!plotName.trim()}
            />
          </View>
        ) : null}

        {plotsQuery.isLoading ? (
          <>
            <AgSkeleton style={styles.plotSkeleton} />
            <AgSkeleton style={styles.formSkeleton} />
          </>
        ) : plotsQuery.isError ? (
          <View style={[styles.card, styles.errorCard]}>
            <AgErrorState
              light
              message={t("organic.plotsLoadError")}
              onRetry={() => void plotsQuery.refetch()}
            />
          </View>
        ) : !plotsQuery.data?.length ? (
          <View style={[styles.card, styles.emptyCard]}>
            <View style={styles.emptyArtwork}>
              <LandPlot size={54} color={C.green} strokeWidth={1.7} />
              <Sprout size={32} color="#67A945" style={styles.emptySprout} />
            </View>
            <AgText weight="bold" style={styles.emptyTitle}>
              {t("organic.noPlots")}
            </AgText>
            <AgText style={styles.emptyMessage}>
              {t("organic.noPlotsMessage")}
            </AgText>
            <TouchableOpacity
              onPress={() => setAddingPlot(true)}
              activeOpacity={0.8}
              accessibilityRole="button"
              style={styles.outlineButton}
            >
              <Plus size={21} color={C.green} />
              <AgText weight="semibold" style={styles.outlineButtonText}>
                {t("organic.addPlot")}
              </AgText>
            </TouchableOpacity>
          </View>
        ) : (
          plotsQuery.data.map((plot) => <PlotCard key={plot.id} plot={plot} />)
        )}
      </View>
    </AgScreen>
  );
}

function PlotCard({ plot }: { plot: OrganicPlot }) {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const cyclesQuery = useOrganicCropCycles(plot.id);
  const createCycle = useCreateOrganicCropCycle(plot.id);
  const [addingCycle, setAddingCycle] = useState(false);
  const [cropPickerOpen, setCropPickerOpen] = useState(false);
  const [cropId, setCropId] = useState<string | null>(null);
  const [sowingDate, setSowingDate] = useState("");
  const [harvestStart, setHarvestStart] = useState("");
  const [harvestEnd, setHarvestEnd] = useState("");

  const submitCycle = () => {
    if (!cropId) return;
    createCycle.mutate(
      {
        crop_id: cropId,
        sowing_date: sowingDate || null,
        expected_harvest_start: harvestStart || null,
        expected_harvest_end: harvestEnd || null,
      },
      {
        onSuccess: () => {
          setAddingCycle(false);
          setCropId(null);
          setSowingDate("");
          setHarvestStart("");
          setHarvestEnd("");
        },
      },
    );
  };

  return (
    <View style={[styles.card, styles.plotCard]}>
      <View style={styles.plotIdentity}>
        <Image
          source={landscapeImage}
          contentFit="cover"
          style={styles.plotImage}
        />
        <View style={styles.plotDetails}>
          <AgText weight="bold" style={styles.plotName}>
            {plot.name}
          </AgText>
          {plot.area_hectares ? (
            <View style={styles.areaRow}>
              <LandPlot size={22} color={C.green} strokeWidth={2.2} />
              <AgText style={styles.areaText}>
                {t("organic.plotAreaValue", { value: plot.area_hectares })}
              </AgText>
            </View>
          ) : null}
          {plot.notice ? (
            <View style={styles.noticePill}>
              <Leaf size={18} color={C.orange} fill={C.orange} />
              <AgText style={styles.noticeText}>{plot.notice}</AgText>
            </View>
          ) : null}
        </View>
      </View>

      {cyclesQuery.isLoading ? (
        <AgSkeleton style={styles.cycleSkeleton} />
      ) : cyclesQuery.isError ? (
        <View style={styles.inlineError}>
          <AgErrorState
            light
            message={t("organic.cropCyclesLoadError")}
            onRetry={() => void cyclesQuery.refetch()}
          />
        </View>
      ) : (
        <View style={styles.cycleList}>
          {(cyclesQuery.data ?? []).map((cycle) => (
            <CropCycleRow key={cycle.id} cycle={cycle} />
          ))}
        </View>
      )}

      {addingCycle ? (
        <View style={styles.cycleForm}>
          <AgText weight="bold" style={styles.cycleFormTitle}>
            {t("organic.addCropCycle")}
          </AgText>

          <View>
            <AgText style={styles.fieldLabel}>{t("organic.chooseCrop")}</AgText>
            <Pressable
              onPress={() => setCropPickerOpen(true)}
              accessibilityRole="button"
              accessibilityLabel={t("organic.chooseCrop")}
              style={styles.cropPickerButton}
            >
              <View style={styles.pickerLeading}>
                <View style={styles.fieldIcon}>
                  <Leaf
                    size={24}
                    color={C.green}
                    fill="#75BA55"
                    strokeWidth={1.7}
                  />
                </View>
                <AgText
                  style={[styles.pickerText, !cropId && styles.placeholderText]}
                >
                  {cropId
                    ? cropLabel(cropId, language)
                    : t("organic.chooseCrop")}
                </AgText>
              </View>
              <ChevronDown size={24} color="#727B89" strokeWidth={2.3} />
            </Pressable>
          </View>

          <CropSelector
            visible={cropPickerOpen}
            selectedCrop={cropId}
            onSelect={(id) => {
              setCropId(id);
              setCropPickerOpen(false);
            }}
            onClose={() => setCropPickerOpen(false)}
          />

          <AgDatePicker
            label={t("organic.sowingDate")}
            placeholder="YYYY-MM-DD"
            value={sowingDate}
            onChange={setSowingDate}
            leftAccessory={
              <CalendarDays size={24} color={C.green} strokeWidth={2.1} />
            }
            fieldStyle={styles.dateField}
            textStyle={styles.dateText}
            labelStyle={styles.fieldLabel}
          />
          <AgDatePicker
            label={t("organic.harvestStart")}
            placeholder="YYYY-MM-DD"
            value={harvestStart}
            onChange={setHarvestStart}
            leftAccessory={
              <CalendarDays size={24} color={C.green} strokeWidth={2.1} />
            }
            fieldStyle={styles.dateField}
            textStyle={styles.dateText}
            labelStyle={styles.fieldLabel}
          />
          <AgDatePicker
            label={t("organic.harvestEnd")}
            placeholder="YYYY-MM-DD"
            value={harvestEnd}
            onChange={setHarvestEnd}
            leftAccessory={
              <CalendarDays size={24} color={C.green} strokeWidth={2.1} />
            }
            fieldStyle={styles.dateField}
            textStyle={styles.dateText}
            labelStyle={styles.fieldLabel}
          />

          <SaveButton
            title={t("common.save")}
            onPress={submitCycle}
            loading={createCycle.isPending}
            disabled={!cropId}
          />
        </View>
      ) : (
        <TouchableOpacity
          onPress={() => setAddingCycle(true)}
          activeOpacity={0.8}
          accessibilityRole="button"
          style={styles.addCycleButton}
        >
          <Plus size={22} color={C.green} strokeWidth={2.4} />
          <AgText weight="semibold" style={styles.addCycleText}>
            {t("organic.addCropCycle")}
          </AgText>
        </TouchableOpacity>
      )}
    </View>
  );
}

function CropCycleRow({ cycle }: { cycle: OrganicCropCycle }) {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const [expanded, setExpanded] = useState(false);
  const planQuery = useOrganicCropCyclePlan(expanded ? cycle.id : null);

  return (
    <View style={styles.cycleRow}>
      <Pressable
        onPress={() => setExpanded((current) => !current)}
        accessibilityRole="button"
        accessibilityState={{ expanded }}
        style={styles.cycleHeader}
      >
        <View style={styles.cycleIcon}>
          <Leaf size={23} color={C.green} fill="#70B852" strokeWidth={1.7} />
        </View>
        <View style={styles.cycleCopy}>
          <AgText weight="semibold" style={styles.cycleName}>
            {cropLabel(cycle.crop_id, language)}
          </AgText>
          {cycle.sowing_date ? (
            <AgText style={styles.cycleDate}>
              {t("organic.sownOn", { date: cycle.sowing_date })}
            </AgText>
          ) : null}
        </View>
        {expanded ? (
          <ChevronUp size={22} color={C.slate} />
        ) : (
          <ChevronDown size={22} color={C.slate} />
        )}
      </Pressable>

      {expanded ? (
        <View style={styles.planArea}>
          {planQuery.isLoading ? (
            <AgSkeleton style={styles.planSkeleton} />
          ) : planQuery.isError ? (
            <AgErrorState
              light
              message={t("organic.planLoadError")}
              onRetry={() => void planQuery.refetch()}
            />
          ) : planQuery.data?.status !== "ready" ||
            !planQuery.data.tasks.length ? (
            <View style={styles.awaitingPlan}>
              <CalendarDays size={22} color={C.orange} />
              <AgText style={styles.awaitingText}>
                {t("organic.planNeedsSowingDate")}
              </AgText>
            </View>
          ) : (
            <>
              <AgText style={styles.planNotice}>
                {language === "ta"
                  ? planQuery.data.notice_ta
                  : planQuery.data.notice_en}
              </AgText>
              {planQuery.data.tasks.map((task) => (
                <View key={task.id} style={styles.taskRow}>
                  <View style={styles.taskHeading}>
                    <AgText weight="semibold" style={styles.taskTitle}>
                      {language === "ta"
                        ? task.title_ta
                        : (task.title_en ?? task.title_ta)}
                    </AgText>
                    <AgBadge label={task.due_on} tone="neutral" />
                  </View>
                  {task.week != null ? (
                    <AgText weight="semibold" style={styles.taskWeek}>
                      {t("organic.planWeek", { week: task.week })}
                    </AgText>
                  ) : null}
                  <AgText style={styles.taskBody}>
                    {language === "ta"
                      ? task.body_ta
                      : (task.body_en ?? task.body_ta)}
                  </AgText>
                </View>
              ))}
            </>
          )}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { paddingBottom: 42 },
  hero: {
    minHeight: 420,
    paddingHorizontal: 22,
    paddingTop: 12,
    paddingBottom: 28,
    overflow: "hidden",
  },
  heroImage: { position: "absolute", top: 0, right: 0, bottom: 0, left: 0 },
  heroWash: {
    position: "absolute",
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    backgroundColor: "rgba(250,253,249,0.76)",
  },
  backButton: {
    width: 54,
    height: 54,
    borderRadius: 27,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(235,247,232,0.95)",
  },
  heroTitle: {
    marginTop: 28,
    color: C.text,
    fontSize: 37,
    lineHeight: 44,
    letterSpacing: -0.8,
  },
  heroIntroRow: {
    marginTop: 24,
    flexDirection: "row",
    alignItems: "flex-start",
  },
  addPlotCircle: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#2F9A49",
    shadowColor: "#27773C",
    shadowOpacity: 0.24,
    shadowRadius: 13,
    shadowOffset: { width: 0, height: 7 },
    elevation: 5,
  },
  heroIntro: {
    flex: 1,
    marginLeft: 18,
    color: C.slate,
    fontSize: 17,
    lineHeight: 26,
  },
  pageContent: { marginTop: -22, paddingHorizontal: 14, gap: 16 },
  card: {
    borderRadius: 26,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.card,
    padding: 18,
    shadowColor: "#254936",
    shadowOpacity: 0.09,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 8 },
    elevation: 3,
  },
  newPlotCard: { marginBottom: 2 },
  formHeading: { flexDirection: "row", alignItems: "center" },
  iconCircle: {
    width: 54,
    height: 54,
    borderRadius: 27,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: C.greenSoft,
  },
  headingCopy: { flex: 1, marginLeft: 14 },
  formTitle: { color: C.text, fontSize: 21, lineHeight: 28 },
  formHint: { marginTop: 2, color: C.slate, fontSize: 14, lineHeight: 20 },
  fieldGap: { marginTop: 18, gap: 14 },
  inputField: {
    minHeight: 62,
    borderRadius: 16,
    borderColor: C.border,
    backgroundColor: "#FBFDF9",
  },
  fieldLabel: { marginBottom: 8, color: C.slate, fontSize: 15, lineHeight: 21 },
  saveButton: {
    minHeight: 62,
    marginTop: 20,
    borderRadius: 18,
    paddingHorizontal: 22,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 13,
    backgroundColor: C.green,
  },
  saveText: { color: "#FFFFFF", fontSize: 19, lineHeight: 25 },
  disabled: { opacity: 0.48 },
  plotSkeleton: { width: "100%", height: 210, borderRadius: 26 },
  formSkeleton: { width: "100%", height: 420, borderRadius: 26 },
  errorCard: { minHeight: 280 },
  emptyCard: { minHeight: 310, alignItems: "center", justifyContent: "center" },
  emptyArtwork: {
    width: 112,
    height: 92,
    borderRadius: 28,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: C.greenSoft,
  },
  emptySprout: { position: "absolute", right: 6, top: 4 },
  emptyTitle: { marginTop: 18, color: C.text, fontSize: 22, lineHeight: 29 },
  emptyMessage: {
    maxWidth: 290,
    marginTop: 7,
    color: C.slate,
    fontSize: 15,
    lineHeight: 22,
    textAlign: "center",
  },
  outlineButton: {
    minHeight: 52,
    marginTop: 20,
    borderRadius: 16,
    borderWidth: 1.5,
    borderColor: C.green,
    paddingHorizontal: 22,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  outlineButtonText: { color: C.green, fontSize: 16, lineHeight: 22 },
  plotCard: { padding: 15 },
  plotIdentity: {
    borderRadius: 20,
    backgroundColor: "#F2F9EE",
    padding: 13,
    flexDirection: "row",
    alignItems: "center",
  },
  plotImage: { width: 91, height: 100, borderRadius: 16 },
  plotDetails: { flex: 1, marginLeft: 15 },
  plotName: { color: C.text, fontSize: 23, lineHeight: 30 },
  areaRow: { marginTop: 7, flexDirection: "row", alignItems: "center", gap: 8 },
  areaText: { color: C.slate, fontSize: 16, lineHeight: 22 },
  noticePill: {
    marginTop: 9,
    alignSelf: "stretch",
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 7,
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    backgroundColor: C.orangeSoft,
  },
  noticeText: { flex: 1, color: C.orange, fontSize: 12, lineHeight: 17 },
  cycleSkeleton: { width: "100%", height: 78, marginTop: 16, borderRadius: 17 },
  inlineError: { minHeight: 220, marginTop: 12 },
  cycleList: { marginTop: 14, gap: 10 },
  cycleForm: { marginTop: 20, gap: 18 },
  cycleFormTitle: { color: C.text, fontSize: 22, lineHeight: 29 },
  cropPickerButton: {
    minHeight: 65,
    borderRadius: 17,
    borderWidth: 1.5,
    borderColor: C.border,
    backgroundColor: "#FBFDF9",
    paddingHorizontal: 15,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  pickerLeading: {
    flex: 1,
    minWidth: 0,
    flexDirection: "row",
    alignItems: "center",
  },
  fieldIcon: {
    width: 39,
    height: 39,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: C.greenSoft,
  },
  pickerText: {
    flex: 1,
    marginLeft: 12,
    color: C.text,
    fontSize: 17,
    lineHeight: 23,
  },
  placeholderText: { color: C.slate },
  dateField: {
    minHeight: 65,
    borderRadius: 17,
    borderColor: C.border,
    backgroundColor: "#FFFFFF",
  },
  dateText: { color: C.text, fontSize: 17, lineHeight: 23 },
  addCycleButton: {
    minHeight: 56,
    marginTop: 17,
    borderRadius: 17,
    borderWidth: 1.5,
    borderColor: C.green,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 9,
    backgroundColor: "#FFFFFF",
  },
  addCycleText: { color: C.green, fontSize: 16, lineHeight: 22 },
  cycleRow: {
    borderRadius: 17,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: "#FBFDF9",
    overflow: "hidden",
  },
  cycleHeader: {
    minHeight: 72,
    paddingHorizontal: 13,
    paddingVertical: 10,
    flexDirection: "row",
    alignItems: "center",
  },
  cycleIcon: {
    width: 45,
    height: 45,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: C.greenSoft,
  },
  cycleCopy: { flex: 1, marginHorizontal: 12 },
  cycleName: { color: C.text, fontSize: 17, lineHeight: 23 },
  cycleDate: { marginTop: 2, color: C.slate, fontSize: 13, lineHeight: 18 },
  planArea: { borderTopWidth: 1, borderTopColor: C.border, padding: 12 },
  planSkeleton: { width: "100%", height: 58, borderRadius: 13 },
  awaitingPlan: {
    borderRadius: 13,
    padding: 12,
    flexDirection: "row",
    alignItems: "center",
    gap: 9,
    backgroundColor: C.orangeSoft,
  },
  awaitingText: { flex: 1, color: C.orange, fontSize: 14, lineHeight: 20 },
  taskRow: {
    marginTop: 8,
    borderRadius: 13,
    backgroundColor: C.greenSoft,
    padding: 12,
  },
  taskHeading: { flexDirection: "row", alignItems: "flex-start", gap: 8 },
  taskTitle: { flex: 1, color: C.text, fontSize: 15, lineHeight: 21 },
  taskBody: { marginTop: 4, color: C.slate, fontSize: 13, lineHeight: 19 },
  taskWeek: { marginTop: 2, color: C.green, fontSize: 13, lineHeight: 18 },
  planNotice: {
    borderRadius: 13,
    padding: 12,
    color: C.orange,
    fontSize: 13,
    lineHeight: 19,
    backgroundColor: C.orangeSoft,
  },
});
