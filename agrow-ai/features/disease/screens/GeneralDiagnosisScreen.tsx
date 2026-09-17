import {
  AlertTriangle,
  ArrowLeft,
  Camera,
  CheckCircle2,
  ChevronRight,
  History as HistoryIcon,
  Images,
  Leaf,
  RotateCcw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Sprout,
  Sun,
} from "lucide-react-native";
import { useRouter } from "expo-router";
import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { ActivityIndicator, Pressable as AgPressable, ScrollView, StyleSheet, View } from "react-native";
import { Image } from "expo-image";

import { AgButton, AgScreen, AgText } from "@/components/ui";
import { DISEASE_DETECTION_CROP_IDS } from "@/constants/crops";
import { useLanguage } from "@/hooks/useLanguage";
import { useSelectedFarm } from "@/features/weather";

import { QUALITY_ISSUE_KEY } from "../constants";
import { predictDiseaseGeneral } from "../services/predictApi";
import type { CaptureMethod, DiseaseReport, PickedImage } from "../types";
import { checkImageQuality } from "../utils/imageQuality";
import { captureFromCamera, pickFromGallery } from "../utils/pickDiseaseImage";

/**
 * General-release diagnosis flow (any authenticated farmer, any crop).
 *
 * Deliberately a separate, self-contained screen rather than folded into the
 * controlled-tester `DiseaseScreen` state machine: that screen's crop
 * identification, confirmation-token, and strict response parsing exist to
 * support the internal/pilot/KVK testing workflow and shouldn't be
 * reinterpreted for the general farmer path. `DiseaseScreen` renders this
 * screen instead of its "tester role required" message when the signed-in
 * user is a regular farmer.
 */
type Step = "crop" | "photo" | "preview" | "submitting" | "result" | "error";

const ENTRY = {
  background: "#F8F5EC",
  surface: "#FFFDF8",
  border: "#D9CDB5",
  text: "#173B2B",
  muted: "#4F5D55",
  green: "#165B33",
  gold: "#C27A00",
} as const;

const REPORT = {
  surface: "#FFFDF8",
  surfaceSoft: "#F1F6ED",
  border: "#D8D2C3",
  text: "#173B2B",
  body: "#354A40",
  muted: "#5A6A61",
  green: "#17663A",
  greenSoft: "#E5F1E1",
  warning: "#8A4B08",
  warningSoft: "#FFF3D6",
} as const;

import { formatDiagnosisName } from '../utils/diagnosisName';
export { formatDiagnosisName } from '../utils/diagnosisName';

// Translate known image-validation failures without exposing raw server text.
// Unknown 422s remain validation failures, not invented service outages.
export function friendlyDiagnosisError(
  error: unknown,
  t: (key: string, options?: { defaultValue?: string }) => string,
): string {
  const isTimeout =
    error != null &&
    typeof error === "object" &&
    (error as { isTimeout?: boolean }).isTimeout === true;
  if (isTimeout) {
    return t("disease.diagnosisTimedOut", {
      defaultValue:
        "The photo is taking longer than usual to analyze. Please try again in a moment.",
    });
  }
  const isNetwork =
    error != null &&
    typeof error === "object" &&
    (error as { isNetwork?: boolean }).isNetwork === true;
  if (isNetwork) {
    return t("common.offlineMessage", {
      defaultValue: "Check your internet connection and try again.",
    });
  }
  const failure = error && typeof error === "object"
    ? error as { status?: number; errorCode?: string } : {};
  const code = failure.errorCode;
  if (code === "EXTREME_DARKNESS") {
    return t("disease.photoTooDark", { defaultValue: "The photo is too dark. Take another photo in natural light." });
  }
  if (code === "EXTREME_BRIGHTNESS") {
    return t("disease.photoTooBright", { defaultValue: "The photo is too bright. Avoid glare and take another photo." });
  }
  if (failure.status === 413 || code === "IMAGE_SIZE_INVALID") {
    return t("disease.photoSizeInvalid", { defaultValue: "The photo is empty or too large. Choose a smaller photo or take a new one." });
  }
  if (failure.status === 415 || code === "IMAGE_FORMAT_UNSUPPORTED") {
    return t("disease.photoFormatInvalid", { defaultValue: "This photo format is not supported. Choose a JPEG or PNG photo." });
  }
  if (failure.status === 422) {
    return t("disease.photoRejected", { defaultValue: "This photo or its details could not be accepted. Check the selected crop and choose a clear, well-lit photo of the affected leaf." });
  }
  return t("disease.generalDiagnosisFailed", {
    defaultValue:
      "The diagnosis service is temporarily unavailable. Please try again.",
  });
}

export function GeneralDiagnosisScreen() {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const { selected: farm } = useSelectedFarm();
  const router = useRouter();

  const [step, setStep] = useState<Step>("crop");
  const [crop, setCrop] = useState<string | null>(null);
  const [picked, setPicked] = useState<PickedImage | null>(null);
  const [qualityIssues, setQualityIssues] = useState<string[]>([]);
  const [result, setResult] = useState<DiseaseReport | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const submissionInFlight = useRef(false);

  const cropDisplayName = (cropId: string) =>
    t(`disease.cropNames.${cropId}`, { defaultValue: cropId });

  // Same fallback chain as DiseaseDetailScreen: prefer the selected app
  // language, then fall back to whichever explanation is actually present.
  // Previously this screen always rendered explanationEnglish, so a Tamil-
  // language farmer using the general (non-tester) diagnosis flow always saw
  // English text.
  const explanation = result
    ? (language === "ta"
        ? result.explanationTamil
        : result.explanationEnglish) ||
      result.explanationEnglish ||
      result.explanationTamil
    : null;

  const reset = () => {
    setStep("crop");
    setCrop(null);
    setPicked(null);
    setQualityIssues([]);
    setResult(null);
    setErrorMessage(null);
  };

  const chooseCrop = (nextCrop: string) => {
    setCrop(nextCrop);
    setStep("photo");
  };

  const takePhoto = async (source: CaptureMethod) => {
    const image =
      source === "camera"
        ? await captureFromCamera({ base64: false })
        : await pickFromGallery({ base64: false });
    if (!image) return;
    setPicked(image);
    setQualityIssues(checkImageQuality(image).issues);
    setStep("preview");
  };

  const submit = async () => {
    if (!crop || !picked || submissionInFlight.current) return;
    submissionInFlight.current = true;
    setStep("submitting");
    setErrorMessage(null);
    try {
      const report = await predictDiseaseGeneral(
        crop,
        { uri: picked.uri, mimeType: picked.mimeType },
        farm?.id,
      );
      setResult(report);
      setStep("result");
    } catch (error) {
      setErrorMessage(friendlyDiagnosisError(error, t));
      setStep("error");
    } finally {
      submissionInFlight.current = false;
    }
  };

  return (
    <AgScreen
      testID="general-diagnosis-screen"
      scroll
      backgroundColor={ENTRY.background}
      contentContainerStyle={styles.screenContent}
    >
      {/* This is the general-release farmer diagnosis flow -- now the actual
          entry point most real users hit (see the routing fix in
          DiseaseScreen.tsx). Its first step had no way to leave the screen
          except the OS back gesture: 'photo' and later steps have an
          explicit in-flow "Back"/"Retake" button, but 'crop' -- the very
          first thing a farmer sees -- didn't (2026-08 pre-release UI pass). */}
      {step === "crop" ? (
        <AgPressable
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={t("common.back")}
          hitSlop={8}
          style={styles.screenBackButton}
        >
          <ArrowLeft size={26} color={ENTRY.text} />
        </AgPressable>
      ) : null}
      {step === "crop" ? (
        <View style={styles.entryFlow}>
          <View style={styles.brandRow}>
            <View style={styles.brandMark}>
              <Sprout size={28} color={ENTRY.green} />
            </View>
            <AgText variant="headingS" weight="bold" style={styles.brandText}>
              AgrowAI
            </AgText>
            <AgPressable
              onPress={() => router.push("/disease/history")}
              accessibilityRole="button"
              accessibilityLabel={t("disease.viewHistory")}
              style={styles.historyLink}
            >
              <HistoryIcon size={19} color={ENTRY.text} />
              <AgText
                variant="bodySmall"
                weight="semibold"
                style={styles.entryText}
              >
                {t("disease.viewHistory")}
              </AgText>
            </AgPressable>
          </View>

          <View style={styles.entryIntro}>
            <AgText variant="caption" weight="bold" style={styles.eyebrow}>
              {t("disease.plantHealth")}
            </AgText>
            <AgText variant="headingXL" weight="bold" style={styles.entryTitle}>
              {t("disease.title")}
            </AgText>
            <AgText variant="body" style={styles.entryMuted}>
              {t("disease.welcomeMessage")}
            </AgText>
          </View>

          <View style={styles.cropPanel}>
            <View style={styles.cropPanelHeader}>
              <AgText variant="headingS" weight="bold" style={styles.entryText}>
                {t("disease.selectCropTitle")}
              </AgText>
              <AgText variant="bodySmall" style={styles.entryMuted}>
                {t("disease.selectCropHint")}
              </AgText>
            </View>
            <View testID="general-crop-grid" style={styles.cropList}>
              {DISEASE_DETECTION_CROP_IDS.map((item) => (
                <AgPressable
                  key={item}
                  testID={`general-crop-${item}`}
                  onPress={() => chooseCrop(item)}
                  style={styles.cropRow}
                  accessibilityRole="button"
                  accessibilityLabel={cropDisplayName(item)}
                  accessibilityHint={t("disease.chooseCropAccessibility", {
                    crop: cropDisplayName(item),
                  })}
                >
                  <View
                    style={styles.cropIcon}
                    accessible={false}
                    accessibilityElementsHidden
                    importantForAccessibility="no-hide-descendants"
                  >
                    <Leaf size={23} color={ENTRY.green} strokeWidth={1.8} />
                  </View>
                  <View style={styles.cropCardCopy}>
                    <AgText
                      variant="body"
                      weight="semibold"
                      numberOfLines={2}
                      style={[styles.cropRowLabel, styles.entryText]}
                    >
                      {cropDisplayName(item)}
                    </AgText>
                  </View>
                  <View style={styles.cropArrow}>
                    <ChevronRight size={18} color={ENTRY.green} />
                  </View>
                </AgPressable>
              ))}
            </View>
          </View>
        </View>
      ) : null}

      {step === "photo" && crop ? (
        <View style={styles.entryFlow}>
          <View style={styles.photoHeader}>
            <AgPressable
              onPress={reset}
              accessibilityRole="button"
              accessibilityLabel={t("common.back")}
              style={styles.headerButton}
            >
              <ArrowLeft size={25} color={ENTRY.text} />
            </AgPressable>
            <View style={styles.photoBrand}>
              <Sprout size={31} color={ENTRY.green} />
              <AgText weight="bold" style={styles.brandText}>
                AgrowAI
              </AgText>
            </View>
            <AgPressable
              onPress={() => router.push("/disease/history")}
              accessibilityRole="button"
              accessibilityLabel={t("disease.viewHistory")}
              style={styles.historyLink}
            >
              <HistoryIcon size={20} color={ENTRY.text} />
              <AgText
                variant="bodySmall"
                weight="semibold"
                style={styles.entryText}
              >
                {t("disease.viewHistory")}
              </AgText>
            </AgPressable>
          </View>
          <View style={styles.entryIntro}>
            <AgText variant="caption" weight="bold" style={styles.eyebrow}>
              {t("disease.plantHealth")}
            </AgText>
            <AgText variant="headingXL" weight="bold" style={styles.entryTitle}>
              {t("disease.title")}
            </AgText>
            <AgText variant="body" style={styles.entryMuted}>
              {t("disease.photoHintGeneral", {
                defaultValue:
                  "Photograph the affected leaf or plant part clearly in good light.",
              })}
            </AgText>
          </View>
          <View style={styles.scanPanel}>
            <View style={styles.scanLeaf}>
              <Leaf size={148} color={ENTRY.green} strokeWidth={1.15} />
              <View style={styles.lesion} />
            </View>
            <View style={styles.guideRow}>
              <Guide icon={Sun} label={t("disease.goodLight")} />
              <View style={styles.guideDivider} />
              <Guide icon={Search} label={t("disease.closeView")} />
              <View style={styles.guideDivider} />
              <Guide icon={Leaf} label={t("disease.oneLeaf")} />
            </View>
          </View>
          <AgPressable
            onPress={() => void takePhoto("camera")}
            accessibilityRole="button"
            accessibilityLabel={t("disease.useCamera", {
              defaultValue: "Take photo",
            })}
            style={styles.cameraButton}
          >
            <Camera size={24} color={ENTRY.text} />
            <AgText
              variant="bodyLarge"
              weight="semibold"
              style={styles.cameraButtonText}
            >
              {t("disease.useCamera", { defaultValue: "Take photo" })}
            </AgText>
          </AgPressable>
          <AgPressable
            onPress={() => void takePhoto("gallery")}
            accessibilityRole="button"
            accessibilityLabel={t("disease.useGallery", {
              defaultValue: "Choose from gallery",
            })}
            style={styles.galleryButton}
          >
            <Images size={23} color={ENTRY.green} />
            <AgText
              variant="bodyLarge"
              weight="semibold"
              style={styles.brandText}
            >
              {t("disease.useGallery", { defaultValue: "Choose from gallery" })}
            </AgText>
          </AgPressable>
          <View style={styles.controlNote}>
            <ShieldCheck size={28} color={ENTRY.gold} />
            <View style={styles.noteCopy}>
              <AgText weight="bold" style={styles.entryText}>
                {t("disease.youStayInControl")}
              </AgText>
              <AgText variant="bodySmall" style={styles.entryMuted}>
                {t("disease.youStayInControlMessage")}
              </AgText>
            </View>
          </View>
        </View>
      ) : null}

      {step === "preview" && picked ? (
        <View style={styles.previewCard}>
          <Image
            source={{ uri: picked.uri }}
            style={styles.preview}
            contentFit="cover"
          />
          {qualityIssues.length > 0 ? (
            <View style={styles.warningBox}>
              <AlertTriangle size={18} color={REPORT.warning} />
              <AgText variant="bodySmall" style={styles.warningText}>
                {qualityIssues
                  .map((issue) => t(QUALITY_ISSUE_KEY[issue] ?? issue))
                  .join(" • ")}
              </AgText>
            </View>
          ) : null}
          <AgButton
            light
            title={t("disease.analyzePhoto", { defaultValue: "Analyze photo" })}
            onPress={() => void submit()}
          />
          <AgButton
            light
            title={t("disease.retakePhoto", { defaultValue: "Retake photo" })}
            variant="ghost"
            onPress={() => setStep("photo")}
          />
        </View>
      ) : null}

      {step === "submitting" ? (
        <View
          style={styles.analysisCard}
          accessibilityRole="progressbar"
          accessibilityLiveRegion="polite"
        >
          <View style={styles.analysisIcon}>
            <ActivityIndicator size="large" color={REPORT.green} />
          </View>
          <AgText variant="caption" weight="bold" style={styles.reportEyebrow}>
            {t("disease.plantHealth")}
          </AgText>
          <AgText variant="headingS" weight="bold" style={styles.analysisTitle}>
            {t("disease.analyzing", { defaultValue: "Analyzing your photo…" })}
          </AgText>
          <AgText variant="bodySmall" center style={styles.analysisHint}>
            {crop
              ? cropDisplayName(crop)
              : t("disease.title", { defaultValue: "Crop diagnosis" })}
          </AgText>
        </View>
      ) : null}

      {step === "error" ? (
        <View style={styles.errorCard}>
          <View style={styles.errorIcon}>
            <ShieldAlert size={28} color={REPORT.warning} />
          </View>
          <AgText variant="headingS" weight="bold" style={styles.reportTitle}>
            {t("disease.diagnosisFailedTitle", {
              defaultValue: "Couldn't analyze this photo",
            })}
          </AgText>
          <AgText variant="bodySmall" style={styles.reportBody}>
            {errorMessage}
          </AgText>
          <AgButton
            light
            title={t("common.retry", { defaultValue: "Try again" })}
            onPress={() => setStep("preview")}
          />
          <AgButton
            light
            title={t("disease.chooseAnotherPhoto", { defaultValue: "Choose another photo" })}
            onPress={() => setStep("photo")}
          />
          <AgButton
            light
            title={t("disease.startOver", { defaultValue: "Start over" })}
            variant="ghost"
            onPress={reset}
          />
        </View>
      ) : null}

      {step === "result" && result ? (
        <ScrollView contentContainerStyle={styles.resultScroll}>
          <View style={styles.report}>
            <View style={styles.reportHero}>
              <View style={styles.evidenceRail} />
              <View style={styles.resultHeader}>
                <View style={styles.resultStatusIcon}>
                  {result.needsExpertReview ? (
                    <AlertTriangle size={27} color={REPORT.warning} />
                  ) : (
                    <CheckCircle2 size={27} color={REPORT.green} />
                  )}
                </View>
                <View style={styles.resultHeaderCopy}>
                  <AgText
                    variant="caption"
                    weight="bold"
                    style={styles.reportEyebrow}
                  >
                    {t("disease.plantHealth")}
                  </AgText>
                  <AgText
                    variant="headingS"
                    weight="bold"
                    style={styles.reportTitle}
                  >
                    {formatDiagnosisName(result.disease) ??
                      t("disease.noDiseaseIdentified", {
                        defaultValue: "No specific diagnosis",
                      })}
                  </AgText>
                  {result.confidence != null ? (
                    <View style={styles.confidenceBadge}>
                      <AgText
                        variant="caption"
                        weight="semibold"
                        style={styles.confidenceText}
                      >
                        {t("disease.confidenceLabel", {
                          defaultValue: "Confidence: {{value}}%",
                          value: result.confidence,
                        })}
                      </AgText>
                    </View>
                  ) : null}
                </View>
              </View>

              {result.verificationLevel ? (
                <View style={styles.verificationBadge}>
                  {result.verificationLevel === "verified_by_local_model" ? (
                    <ShieldCheck size={15} color={REPORT.green} />
                  ) : (
                    <Sparkles size={15} color={REPORT.muted} />
                  )}
                  <AgText
                    variant="caption"
                    weight="semibold"
                    style={styles.verificationText}
                  >
                    {result.verificationLevel === "verified_by_local_model"
                      ? t("disease.verifiedByLocalModel", {
                          defaultValue: "Verified by trained AI model",
                        })
                      : t("disease.aiVisionEstimateBadge", {
                          defaultValue: "AI estimate — not lab-verified",
                        })}
                  </AgText>
                </View>
              ) : null}
            </View>

            {result.needsExpertReview ? (
              <View style={styles.warningBox}>
                <AlertTriangle size={18} color={REPORT.warning} />
                <AgText variant="bodySmall" style={styles.warningText}>
                  {t("disease.aiEstimateNotice", {
                    defaultValue:
                      "This is an AI-assisted estimate, not an official diagnosis. Please confirm with your local Agriculture Officer or KVK before taking action.",
                  })}
                </AgText>
              </View>
            ) : null}

            {explanation ? (
              <View style={styles.explanationCard}>
                <AgText variant="bodySmall" style={styles.reportBody}>
                  {explanation}
                </AgText>
              </View>
            ) : null}

            <ResultSection
              title={t("disease.symptomsToWatch", {
                defaultValue: "Symptoms observed",
              })}
              items={result.symptoms}
            />
            <ResultSection
              title={t("disease.whyThisMayOccur", {
                defaultValue: "Likely causes",
              })}
              items={result.causes}
            />
            <ResultSection
              title={t("disease.immediateActions", {
                defaultValue: "General care",
              })}
              items={result.recommendations}
            />
            <ResultSection
              title={t("disease.prevention", { defaultValue: "Prevention" })}
              items={result.prevention}
            />

            <View style={styles.reportActions}>
              <AgButton
                light
                title={t("disease.diagnoseAnother", {
                  defaultValue: "Diagnose another photo",
                })}
                variant="secondary"
                onPress={reset}
                leftIcon={<RotateCcw size={18} color={ENTRY.green} />}
              />
              <AgButton
                light
                title={t("disease.viewHistory")}
                variant="ghost"
                onPress={() => router.push("/disease/history")}
                leftIcon={<HistoryIcon size={18} color={ENTRY.green} />}
              />
            </View>
          </View>
        </ScrollView>
      ) : null}
    </AgScreen>
  );
}

function Guide({ icon: Icon, label }: { icon: typeof Sun; label: string }) {
  return (
    <View style={styles.guideItem}>
      <Icon size={25} color={ENTRY.green} />
      <AgText
        variant="caption"
        weight="semibold"
        center
        style={styles.entryText}
      >
        {label}
      </AgText>
    </View>
  );
}

function ResultSection({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <View style={styles.section}>
      <View style={styles.sectionRail} />
      <AgText weight="bold" variant="body" style={styles.sectionTitle}>
        {title}
      </AgText>
      {items.map((item, index) => (
        <View key={`${title}-${index}`} style={styles.bulletRow}>
          <View style={styles.bulletDot} />
          <AgText variant="bodySmall" style={styles.bulletText}>
            {item}
          </AgText>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  screenContent: { paddingTop: 6, paddingBottom: 30 },
  entryFlow: { width: "100%", alignSelf: "stretch", gap: 16 },
  screenBackButton: {
    width: 48,
    height: 48,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: ENTRY.border,
    backgroundColor: ENTRY.surface,
  },
  brandRow: {
    minHeight: 48,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  brandMark: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#EDF4E8",
  },
  brandText: { color: ENTRY.green },
  entryText: { color: ENTRY.text },
  entryMuted: { color: ENTRY.muted, lineHeight: 22 },
  entryIntro: { gap: 5 },
  eyebrow: { color: ENTRY.gold, letterSpacing: 0.7 },
  entryTitle: { color: ENTRY.green, lineHeight: 40 },
  cropPanel: {
    padding: 14,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: ENTRY.border,
    backgroundColor: ENTRY.surface,
  },
  cropPanelHeader: { gap: 3, marginBottom: 13 },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  headerTitle: { flex: 1 },
  historyLink: {
    marginLeft: "auto",
    minHeight: 48,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 5,
    paddingHorizontal: 4,
  },
  cropList: {
    width: "100%",
    flexDirection: "column",
    gap: 10,
  },
  cropRow: {
    width: "100%",
    minWidth: 0,
    minHeight: 76,
    padding: 12,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: ENTRY.border,
    backgroundColor: "#F7FAF3",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "flex-start",
    gap: 12,
  },
  cropIcon: {
    width: 48,
    height: 48,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#E7F1E3",
  },
  cropCardCopy: { flex: 1, minWidth: 0, paddingRight: 38 },
  cropRowLabel: { minWidth: 0, lineHeight: 21 },
  cropArrow: {
    position: "absolute",
    top: 23,
    right: 12,
    width: 30,
    height: 30,
    borderRadius: 15,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#EDF4E8",
  },
  pressed: { opacity: 0.76 },
  photoHeader: {
    minHeight: 54,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  headerButton: {
    width: 48,
    height: 48,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: ENTRY.border,
    backgroundColor: ENTRY.surface,
    alignItems: "center",
    justifyContent: "center",
  },
  photoBrand: {
    position: "absolute",
    left: 58,
    right: 102,
    alignItems: "center",
    justifyContent: "center",
  },
  scanPanel: {
    overflow: "hidden",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: ENTRY.border,
    backgroundColor: ENTRY.surface,
  },
  scanLeaf: { minHeight: 190, alignItems: "center", justifyContent: "center" },
  lesion: {
    position: "absolute",
    width: 15,
    height: 15,
    borderRadius: 8,
    right: "39%",
    top: "43%",
    borderWidth: 3,
    borderColor: "#F4BF4F",
    backgroundColor: "#D88A00",
  },
  guideRow: {
    minHeight: 68,
    flexDirection: "row",
    alignItems: "center",
    borderTopWidth: 1,
    borderTopColor: ENTRY.border,
  },
  guideItem: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 3,
    paddingHorizontal: 4,
  },
  guideDivider: { width: 1, height: 42, backgroundColor: ENTRY.border },
  cameraButton: {
    minHeight: 56,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 9,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#C98B00",
    backgroundColor: "#F2B632",
  },
  cameraButtonText: { color: ENTRY.text },
  galleryButton: {
    minHeight: 56,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 9,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: ENTRY.green,
    backgroundColor: ENTRY.surface,
  },
  controlNote: {
    minHeight: 78,
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
    padding: 13,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#E8C477",
    backgroundColor: "#FFF8E8",
  },
  noteCopy: { flex: 1, gap: 3 },
  preview: { width: "100%", height: 240, borderRadius: 16 },
  previewCard: {
    width: "100%",
    gap: 16,
    marginTop: 16,
    padding: 16,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: REPORT.border,
    backgroundColor: REPORT.surface,
  },
  warningBox: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
    borderWidth: 1,
    borderColor: "#E1B566",
    borderRadius: 14,
    padding: 12,
    backgroundColor: REPORT.warningSoft,
  },
  warningText: { flex: 1, color: REPORT.warning, lineHeight: 21 },
  analysisCard: {
    width: "100%",
    maxWidth: 680,
    minHeight: 230,
    alignSelf: "center",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    marginTop: 18,
    paddingHorizontal: 24,
    paddingVertical: 36,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: REPORT.border,
    backgroundColor: REPORT.surface,
  },
  analysisIcon: {
    width: 72,
    height: 72,
    marginBottom: 4,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 36,
    backgroundColor: REPORT.greenSoft,
  },
  analysisTitle: { color: REPORT.text, textAlign: "center", lineHeight: 30 },
  analysisHint: { color: REPORT.muted, lineHeight: 21 },
  errorCard: {
    width: "100%",
    maxWidth: 680,
    alignSelf: "center",
    gap: 14,
    marginTop: 18,
    padding: 18,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: REPORT.border,
    backgroundColor: REPORT.surface,
  },
  errorIcon: {
    width: 52,
    height: 52,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 16,
    backgroundColor: REPORT.warningSoft,
  },
  resultScroll: {
    width: "100%",
    maxWidth: 720,
    alignSelf: "center",
    paddingTop: 12,
    paddingBottom: 36,
  },
  report: { width: "100%", gap: 12 },
  reportHero: {
    overflow: "hidden",
    gap: 14,
    padding: 18,
    paddingLeft: 22,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: REPORT.border,
    backgroundColor: REPORT.surface,
  },
  evidenceRail: {
    position: "absolute",
    top: 0,
    bottom: 0,
    left: 0,
    width: 6,
    backgroundColor: REPORT.green,
  },
  resultHeader: { flexDirection: "row", alignItems: "flex-start", gap: 12 },
  resultStatusIcon: {
    width: 52,
    height: 52,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 16,
    backgroundColor: REPORT.greenSoft,
  },
  resultHeaderCopy: { flex: 1, minWidth: 0, gap: 5 },
  reportEyebrow: {
    color: REPORT.green,
    letterSpacing: 0.7,
    textTransform: "uppercase",
  },
  reportTitle: { color: REPORT.text, lineHeight: 29 },
  reportBody: { color: REPORT.body, lineHeight: 23 },
  confidenceBadge: {
    alignSelf: "flex-start",
    paddingHorizontal: 9,
    paddingVertical: 4,
    borderRadius: 999,
    backgroundColor: REPORT.greenSoft,
  },
  confidenceText: { color: REPORT.green },
  verificationBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    alignSelf: "flex-start",
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: REPORT.greenSoft,
  },
  verificationText: { color: REPORT.green },
  explanationCard: {
    padding: 16,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: REPORT.border,
    backgroundColor: REPORT.surface,
  },
  section: {
    overflow: "hidden",
    gap: 10,
    padding: 16,
    paddingLeft: 20,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: REPORT.border,
    backgroundColor: REPORT.surfaceSoft,
  },
  sectionRail: {
    position: "absolute",
    top: 0,
    bottom: 0,
    left: 0,
    width: 4,
    backgroundColor: "#78A768",
  },
  sectionTitle: { color: REPORT.text, lineHeight: 23 },
  bulletRow: { flexDirection: "row", alignItems: "flex-start", gap: 10 },
  bulletDot: {
    width: 7,
    height: 7,
    marginTop: 7,
    borderRadius: 4,
    backgroundColor: REPORT.green,
  },
  bulletText: { flex: 1, color: REPORT.body, lineHeight: 22 },
  reportActions: { gap: 8, marginTop: 4 },
});
