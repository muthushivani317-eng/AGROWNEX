import { Image } from "expo-image";
import { useRouter } from "expo-router";
import {
  ArrowLeft,
  Bug,
  Camera,
  CheckCircle2,
  CircleHelp,
  Droplets,
  FileText,
  Hammer,
  IndianRupee,
  Layers3,
  Leaf,
  MinusCircle,
  MoreHorizontal,
  Package,
  Plus,
  RefreshCw,
  Search,
  Sprout,
  TrendingDown,
  TrendingUp,
  Wheat,
  X,
} from "lucide-react-native";
import type { ComponentType } from "react";
import { useState } from "react";
import {
  Alert,
  StyleSheet,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from "react-native";
import { useTranslation } from "react-i18next";

import {
  AgBadge,
  AgButton,
  AgErrorState,
  AgInput,
  AgPressable,
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";
import {
  captureFromCamera,
  pickFromGallery,
} from "@/features/disease/utils/pickDiseaseImage";
import { PRACTICE_TYPES } from "../constants";
import {
  useCreateOrganicPractice,
  useOrganicPractices,
  useUploadOrganicEvidence,
} from "../hooks/useOrganic";
import { useOrganicSync } from "../hooks/useOrganicSync";
import type {
  OrganicEvidenceInput,
  OrganicOutcomeStatus,
  OrganicPracticeType,
} from "../types";

const C = {
  bg: "#F8F7ED",
  surface: "#FFFDF8",
  ink: "#092F22",
  muted: "#66726C",
  green: "#23783D",
  pale: "#EAF5E6",
  border: "#D9D7C9",
  amber: "#E9770B",
  blue: "#2B8CB8",
};
type Icon = ComponentType<{
  size?: number;
  color?: string;
  strokeWidth?: number;
}>;
const ICONS: Record<OrganicPracticeType, Icon> = {
  amendment: Leaf,
  seed_treatment: Sprout,
  biological_treatment: RefreshCw,
  botanical_spray: Leaf,
  trap: Bug,
  mechanical_weeding: Hammer,
  mulching: Layers3,
  green_manure: Sprout,
  crop_rotation: RefreshCw,
  irrigation_drainage: Droplets,
  scouting: Search,
  harvest: Wheat,
  custom: MoreHorizontal,
};
const ACCENTS: Record<OrganicPracticeType, string> = {
  amendment: C.green,
  seed_treatment: "#40953E",
  biological_treatment: C.amber,
  botanical_spray: C.green,
  trap: "#D65F10",
  mechanical_weeding: "#4D7D88",
  mulching: C.amber,
  green_manure: C.green,
  crop_rotation: C.green,
  irrigation_drainage: C.blue,
  scouting: "#34433D",
  harvest: C.amber,
  custom: C.muted,
};
const OUTCOMES: OrganicOutcomeStatus[] = [
  "not_reported",
  "improved",
  "no_change",
  "worse",
  "unknown",
];
const OUTCOME_ICONS: Record<OrganicOutcomeStatus, Icon> = {
  not_reported: CheckCircle2,
  improved: TrendingUp,
  no_change: MinusCircle,
  worse: TrendingDown,
  unknown: CircleHelp,
};
const OUTCOME_TONES: Record<
  OrganicOutcomeStatus,
  "success" | "warning" | "danger" | "neutral"
> = {
  not_reported: "neutral",
  improved: "success",
  no_change: "neutral",
  worse: "danger",
  unknown: "neutral",
};

function Chip({
  label,
  selected,
  icon: IconView,
  color = C.green,
  compact,
  variant,
  onPress,
}: {
  label: string;
  selected: boolean;
  icon: Icon;
  color?: string;
  compact: boolean;
  variant: "practice" | "outcome";
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      accessibilityRole="radio"
      accessibilityLabel={label}
      accessibilityState={{ checked: selected }}
      onPress={onPress}
      activeOpacity={0.78}
      style={[
        s.chip,
        variant === "practice" ? s.practiceChip : s.outcomeChip,
        compact && s.chipCompact,
        selected && s.chipSelected,
      ]}
    >
      <View
        style={[
          s.chipIcon,
          { backgroundColor: `${color}14` },
          selected && s.chipIconSelected,
        ]}
      >
        <IconView size={22} strokeWidth={2.3} color={color} />
      </View>
      <AgText
        variant="bodySmall"
        weight={selected ? "semibold" : "medium"}
        style={s.chipLabel}
      >
        {label}
      </AgText>
      {selected ? (
        <View style={s.selectedMark}>
          <CheckCircle2 size={17} color={C.green} fill="#FFFFFF" />
        </View>
      ) : null}
    </TouchableOpacity>
  );
}

export function OrganicLogbookScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const compact = useWindowDimensions().width < 390;
  const query = useOrganicPractices(farmId);
  const create = useCreateOrganicPractice(farmId);
  const upload = useUploadOrganicEvidence(farmId);
  useOrganicSync();
  const [adding, setAdding] = useState(true);
  const [type, setType] = useState<OrganicPracticeType>("amendment");
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unit, setUnit] = useState("");
  const [area, setArea] = useState("");
  const [cost, setCost] = useState("");
  const [outcome, setOutcome] = useState<OrganicOutcomeStatus>("not_reported");
  const [evidence, setEvidence] = useState<OrganicEvidenceInput | null>(null);
  const reset = () => {
    setAdding(false);
    setTitle("");
    setNotes("");
    setQuantity("");
    setUnit("");
    setArea("");
    setCost("");
    setOutcome("not_reported");
    setEvidence(null);
  };
  const uploadPhoto = async (camera: boolean) => {
    const picked = await (camera ? captureFromCamera : pickFromGallery)({
      base64: false,
    });
    if (picked)
      upload.mutate(
        { fileUri: picked.uri, mimeType: picked.mimeType },
        {
          onSuccess: (a) =>
            setEvidence({
              evidenceType: "photo",
              uploadAttestationId: a.id,
              uploadReceipt: a.upload_receipt,
              retentionConsent: true,
            }),
          onError: () => Alert.alert(t("organic.evidenceUploadError")),
        },
      );
  };
  const attach = () =>
    Alert.alert(t("organic.attachPhoto"), undefined, [
      { text: t("organic.camera"), onPress: () => void uploadPhoto(true) },
      { text: t("organic.gallery"), onPress: () => void uploadPhoto(false) },
      { text: t("common.cancel"), style: "cancel" },
    ]);
  const submit = () => {
    if (!title.trim()) return Alert.alert(t("organic.titleRequired"));
    if (Boolean(quantity.trim()) !== Boolean(unit.trim()))
      return Alert.alert(t("organic.quantityUnitRequiredTogether"));
    create.mutate(
      {
        type,
        title: title.trim(),
        notes: notes.trim() || null,
        occurredAt: new Date().toISOString(),
        quantity: quantity.trim() ? Number(quantity) : null,
        unit: unit.trim() || null,
        treatedAreaHectares: area.trim() ? Number(area) : null,
        expenseAmountInr: cost.trim() ? Number(cost) : null,
        outcomeStatus: outcome,
        evidence: evidence ? [evidence] : [],
      },
      {
        onSuccess: ({ offline }) => {
          reset();
          Alert.alert(
            t(offline ? "organic.savedOffline" : "organic.practiceSaved"),
          );
        },
      },
    );
  };
  const input = {
    light: true,
    fieldBorderColor: C.border,
    fieldBackgroundColor: "#FFF",
  } as const;

  return (
    <AgScreen
      scroll
      keyboardAvoiding
      backgroundColor={C.bg}
      contentContainerStyle={s.screen}
      testID="organic-logbook-screen"
    >
      <View style={s.hero}>
        <Image
          source={require("../../../assets/images/organic-dashboard-landscape.png")}
          contentFit="cover"
          contentPosition="right center"
          style={StyleSheet.absoluteFill}
          accessibilityIgnoresInvertColors
        />
        <View style={s.heroWash} />
        <AgPressable
          accessibilityRole="button"
          accessibilityLabel={t("common.back")}
          onPress={() => router.back()}
          style={s.back}
        >
          <ArrowLeft size={26} color={C.ink} />
        </AgPressable>
        <View style={s.heroCopy}>
          <AgText variant="headingL" weight="bold" style={s.heroTitle}>
            {t("organic.logbookTitle")}
          </AgText>
          <AgText variant="body" style={s.subtitle}>
            {t("organic.logbookSubtitle")}
          </AgText>
        </View>
      </View>

      {adding ? (
        <View style={s.form}>
          <View style={s.formHead}>
            <View style={s.plus}>
              <Plus size={27} color="#FFF" />
            </View>
            <AgText variant="headingS" weight="bold" style={s.flexTitle}>
              {t("organic.addPractice")}
            </AgText>
            <AgPressable
              accessibilityRole="button"
              accessibilityLabel={t("common.close")}
              onPress={() => setAdding(false)}
              style={s.close}
            >
              <X size={20} color={C.muted} />
            </AgPressable>
          </View>
          <AgText variant="label" weight="semibold" style={s.label}>
            {t("organic.practiceTypeLabel")}
          </AgText>
          <View style={s.chips}>
            {PRACTICE_TYPES.map((v) => (
              <Chip
                key={v}
                label={t(`organic.practice.${v}`)}
                selected={type === v}
                icon={ICONS[v]}
                color={ACCENTS[v]}
                compact={compact}
                variant="practice"
                onPress={() => setType(v)}
              />
            ))}
          </View>
          <View style={s.block}>
            <AgInput
              {...input}
              label={t("organic.practiceTitle")}
              placeholder={t("organic.practiceTitlePlaceholder")}
              value={title}
              onChangeText={setTitle}
              leftAccessory={<FileText size={21} color={C.muted} />}
              returnKeyType="next"
            />
          </View>
          <View style={s.block}>
            <AgInput
              {...input}
              label={t("organic.notes")}
              placeholder={t("organic.notesPlaceholder")}
              value={notes}
              onChangeText={setNotes}
              multiline
              leftAccessory={<FileText size={21} color={C.muted} />}
              fieldStyle={s.notesField}
              style={s.notesInput}
            />
          </View>
          <View style={[s.pair, compact && s.pairCompact]}>
            <View style={s.half}>
              <AgInput
                {...input}
                label={t("organic.quantityLabel")}
                placeholder={t("organic.quantityPlaceholder")}
                value={quantity}
                onChangeText={setQuantity}
                keyboardType="decimal-pad"
                leftAccessory={<TrendingUp size={21} color={C.green} />}
              />
            </View>
            <View style={s.half}>
              <AgInput
                {...input}
                label={t("organic.unitLabel")}
                placeholder={t("organic.unitPlaceholder")}
                value={unit}
                onChangeText={setUnit}
                leftAccessory={<Package size={21} color={C.green} />}
              />
            </View>
          </View>
          <View style={[s.pair, compact && s.pairCompact]}>
            <View style={s.half}>
              <AgInput
                {...input}
                label={t("organic.treatedAreaLabel")}
                placeholder={t("organic.treatedAreaPlaceholder")}
                value={area}
                onChangeText={setArea}
                keyboardType="decimal-pad"
                leftAccessory={<Layers3 size={21} color={C.green} />}
              />
            </View>
            <View style={s.half}>
              <AgInput
                {...input}
                label={t("organic.costLabel")}
                placeholder={t("organic.costPlaceholder")}
                value={cost}
                onChangeText={setCost}
                keyboardType="decimal-pad"
                leftAccessory={<IndianRupee size={21} color={C.green} />}
              />
            </View>
          </View>
          <AgText variant="label" weight="semibold" style={s.outcomeLabel}>
            {t("organic.outcomeLabel")}
          </AgText>
          <View style={s.chips}>
            {OUTCOMES.map((v) => (
              <Chip
                key={v}
                label={t(`organic.outcomeStatus.${v}`)}
                selected={outcome === v}
                icon={OUTCOME_ICONS[v]}
                color={v === "worse" ? C.amber : C.green}
                compact={compact}
                variant="outcome"
                onPress={() => setOutcome(v)}
              />
            ))}
          </View>
          {evidence ? (
            <View style={s.photo}>
              <Camera size={22} color={C.green} />
              <AgText variant="bodySmall" weight="semibold" style={s.photoText}>
                {t("organic.photoAttached")}
              </AgText>
              <AgPressable
                accessibilityRole="button"
                accessibilityLabel={t("organic.removePhoto")}
                onPress={() => setEvidence(null)}
                style={s.close}
              >
                <X size={18} color={C.muted} />
              </AgPressable>
            </View>
          ) : (
            <View style={s.attach}>
              <AgButton
                light
                variant="outline"
                title={t("organic.attachPhoto")}
                leftIcon={<Camera size={22} color={C.green} />}
                loading={upload.isPending}
                onPress={attach}
              />
            </View>
          )}
          <AgButton
            light
            variant="success"
            size="lg"
            title={t("common.save")}
            loading={create.isPending}
            onPress={submit}
          />
        </View>
      ) : (
        <AgPressable
          accessibilityRole="button"
          accessibilityLabel={t("organic.addPractice")}
          onPress={() => setAdding(true)}
          style={s.addBar}
        >
          <Plus size={22} color="#FFF" />
          <AgText weight="bold" style={s.white}>
            {t("organic.addPractice")}
          </AgText>
        </AgPressable>
      )}

      <View style={s.history}>
        <AgText variant="headingS" weight="bold" style={s.historyTitle}>
          {t("organic.practiceHistoryTitle")}
        </AgText>
        {query.isLoading ? (
          <>
            <AgSkeleton className="mt-4 h-24 w-full" />
            <AgSkeleton className="mt-3 h-24 w-full" />
          </>
        ) : query.isError ? (
          <AgErrorState
            message={t("organic.loadError")}
            onRetry={() => void query.refetch()}
          />
        ) : !query.data?.length ? (
          <View style={s.empty}>
            <Image
              source={require("../../../assets/images/organic-dashboard-landscape.png")}
              contentFit="cover"
              contentPosition="left center"
              style={StyleSheet.absoluteFill}
              accessibilityIgnoresInvertColors
            />
            <View style={s.emptyWash} />
            <View style={s.emptyPlant}>
              <Sprout size={48} color={C.green} />
            </View>
            <View style={s.emptyCopy}>
              <AgText variant="headingS" weight="bold" style={s.historyTitle}>
                {t("organic.emptyTitle")}
              </AgText>
              <AgText variant="bodySmall" style={s.muted}>
                {t("organic.emptyDescription")}
              </AgText>
              <AgPressable
                accessibilityRole="button"
                accessibilityLabel={t("organic.addPractice")}
                onPress={() => setAdding(true)}
                style={s.emptyAction}
              >
                <Plus size={18} color={C.green} />
                <AgText variant="bodySmall" weight="semibold" style={s.green}>
                  {t("organic.addPractice")}
                </AgText>
              </AgPressable>
            </View>
          </View>
        ) : (
          query.data.map((row) => {
            const RowIcon = ICONS[row.type];
            return (
              <View key={row.id} style={s.row}>
                <View style={s.rowIcon}>
                  <RowIcon size={23} color={ACCENTS[row.type]} />
                </View>
                <View style={s.rowCopy}>
                  <AgText weight="semibold" style={s.historyTitle}>
                    {row.title}
                  </AgText>
                  <AgText variant="caption" style={s.green}>
                    {t(`organic.practice.${row.type}`)} ·{" "}
                    {new Date(row.occurredAt).toLocaleDateString()}
                  </AgText>
                  {row.notes ? (
                    <AgText variant="bodySmall" style={s.muted}>
                      {row.notes}
                    </AgText>
                  ) : null}
                  <View style={s.badges}>
                    {row.syncStatus === "pending" ? (
                      <AgBadge
                        label={t("organic.pendingSync")}
                        tone="warning"
                      />
                    ) : null}
                    {row.quantity != null ? (
                      <AgBadge
                        label={t("organic.quantityValue", {
                          quantity: row.quantity,
                          unit: row.unit,
                        })}
                        tone="neutral"
                      />
                    ) : null}
                    {row.treatedAreaHectares != null ? (
                      <AgBadge
                        label={t("organic.treatedAreaValue", {
                          area: row.treatedAreaHectares,
                        })}
                        tone="neutral"
                      />
                    ) : null}
                    {row.expenseAmountInr != null ? (
                      <AgBadge
                        label={t("organic.costValue", {
                          amount: row.expenseAmountInr,
                        })}
                        tone="neutral"
                      />
                    ) : null}
                    {row.outcomeStatus !== "not_reported" ? (
                      <AgBadge
                        label={t(`organic.outcomeStatus.${row.outcomeStatus}`)}
                        tone={OUTCOME_TONES[row.outcomeStatus]}
                      />
                    ) : null}
                    {row.evidence.length ? (
                      <AgBadge
                        label={t("organic.evidenceCount", {
                          count: row.evidence.length,
                        })}
                        tone="neutral"
                      />
                    ) : null}
                  </View>
                </View>
              </View>
            );
          })
        )}
      </View>
    </AgScreen>
  );
}

const s = StyleSheet.create({
  screen: { paddingHorizontal: 0, paddingBottom: 44 },
  hero: {
    minHeight: 228,
    overflow: "hidden",
    paddingHorizontal: 20,
    paddingTop: 12,
    justifyContent: "flex-end",
  },
  heroWash: {
    ...StyleSheet.absoluteFill,
    backgroundColor: "rgba(255,253,248,0.58)",
  },
  back: {
    position: "absolute",
    left: 20,
    top: 12,
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: "rgba(248,250,241,0.95)",
    alignItems: "center",
    justifyContent: "center",
  },
  heroCopy: {
    maxWidth: 600,
    marginBottom: 14,
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderRadius: 18,
    backgroundColor: "rgba(255,253,248,0.82)",
  },
  heroTitle: { color: C.ink, fontSize: 30, lineHeight: 37 },
  subtitle: {
    color: "#52625B",
    maxWidth: 560,
    marginTop: 5,
    fontSize: 15,
    lineHeight: 22,
  },
  form: {
    marginHorizontal: 16,
    backgroundColor: C.surface,
    borderColor: "#E4E1D3",
    borderWidth: 1,
    borderRadius: 22,
    padding: 16,
    shadowColor: "#1D3D2A",
    shadowOpacity: 0.1,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 7 },
    elevation: 4,
  },
  formHead: { minHeight: 48, flexDirection: "row", alignItems: "center" },
  plus: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: C.green,
    alignItems: "center",
    justifyContent: "center",
    marginRight: 12,
  },
  flexTitle: { flex: 1, color: C.ink },
  close: {
    width: 48,
    height: 48,
    alignItems: "center",
    justifyContent: "center",
  },
  label: { color: C.ink, marginTop: 18, marginBottom: 8 },
  chips: {
    width: "100%",
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "stretch",
    gap: 8,
  },
  chip: {
    position: "relative",
    minHeight: 74,
    width: "31.8%",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 8,
    paddingVertical: 10,
    borderRadius: 16,
    borderWidth: 1.25,
    borderColor: "#D8DCD4",
    backgroundColor: "#FFF",
  },
  practiceChip: { minHeight: 86 },
  outcomeChip: { minHeight: 82 },
  chipCompact: { width: "48.6%" },
  chipSelected: {
    borderColor: "#87BF7A",
    backgroundColor: "#EEF8EB",
  },
  chipIcon: {
    width: 38,
    height: 38,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  chipIconSelected: { backgroundColor: "#DDF1D7" },
  chipLabel: {
    minHeight: 38,
    marginTop: 6,
    color: C.ink,
    lineHeight: 18,
    textAlign: "center",
  },
  selectedMark: {
    position: "absolute",
    top: 7,
    right: 7,
    width: 20,
    height: 20,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#FFFFFF",
  },
  block: { marginTop: 16 },
  notesField: { minHeight: 88, alignItems: "flex-start", paddingTop: 16 },
  notesInput: { minHeight: 72, textAlignVertical: "top", paddingTop: 0 },
  pair: { flexDirection: "row", gap: 12, marginTop: 16 },
  pairCompact: { flexDirection: "column" },
  half: { flex: 1, minWidth: 0 },
  outcomeLabel: { color: C.ink, marginTop: 18, marginBottom: 8 },
  attach: { marginTop: 18, marginBottom: 10 },
  photo: {
    minHeight: 58,
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: C.green,
    borderRadius: 14,
    paddingLeft: 16,
    marginTop: 18,
    marginBottom: 10,
  },
  photoText: { color: C.green, flex: 1, marginLeft: 10 },
  addBar: {
    minHeight: 58,
    marginHorizontal: 16,
    marginTop: 16,
    borderRadius: 18,
    backgroundColor: C.green,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },
  white: { color: "#FFF" },
  history: { paddingHorizontal: 16, paddingTop: 22 },
  historyTitle: { color: C.ink, marginBottom: 6 },
  empty: {
    minHeight: 220,
    overflow: "hidden",
    flexDirection: "row",
    alignItems: "center",
    borderRadius: 22,
    borderWidth: 1,
    borderColor: "#E4E1D3",
    backgroundColor: C.surface,
    padding: 18,
  },
  emptyWash: {
    ...StyleSheet.absoluteFill,
    backgroundColor: "rgba(255,253,248,0.68)",
  },
  emptyPlant: {
    width: 92,
    height: 92,
    borderRadius: 46,
    backgroundColor: "rgba(234,245,230,0.94)",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 16,
  },
  emptyCopy: { flex: 1 },
  muted: { color: C.muted, marginTop: 5 },
  green: { color: C.green, marginTop: 2 },
  emptyAction: {
    minHeight: 48,
    alignSelf: "flex-start",
    marginTop: 14,
    paddingHorizontal: 16,
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: C.green,
    backgroundColor: "rgba(255,255,255,0.88)",
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  row: {
    flexDirection: "row",
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#E1E1D6",
    backgroundColor: C.surface,
    padding: 14,
    marginTop: 10,
  },
  rowIcon: {
    width: 48,
    height: 48,
    borderRadius: 16,
    backgroundColor: C.pale,
    alignItems: "center",
    justifyContent: "center",
    marginRight: 12,
  },
  rowCopy: { flex: 1 },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: 7, marginTop: 10 },
});
