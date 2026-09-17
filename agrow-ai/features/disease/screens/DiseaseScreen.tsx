import { Image } from "expo-image";
import { useRouter } from "expo-router";
import {
  ArrowLeft,
  Camera,
  History,
  Images,
  Lightbulb,
  Leaf,
  ScanLine,
  ShieldCheck,
  Sprout,
  Sun,
  Search,
  TriangleAlert,
} from "lucide-react-native";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { ActivityIndicator, StyleSheet, View } from "react-native";

import {
  AgButton,
  AgCard,
  AgPressable,
  AgScreen,
  AgText,
} from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";
import { useLanguage } from "@/hooks/useLanguage";
import { useSelectedFarm, useWeather } from "@/features/weather";
import { INSIGHT_MESSAGE_KEY } from "@/features/weather/constants";
import { useAuthStore } from "@/features/auth/store/authStore";
import { buildProfile } from "@/config/env";
import { httpClient } from "@/services/apiClient";
import {
  confirmInternalCrop,
  identifyCropInternalOnly,
  type CropIdentificationStatus,
  type SupportedCropId,
} from "@/features/cropIdentification";
import { BananaDiseaseDetectionScreen } from "@/features/bananaV3/screens/BananaDiseaseDetectionScreen";
import { GeneralDiagnosisScreen } from "./GeneralDiagnosisScreen";
import {
  AcceptedDiagnosisCard,
  CropPhotoConfirmation,
  UncertainDiagnosisCard,
  classifyCropDiagnosisFailure,
  cropDiagnosisAdapter,
  findDiseaseCapability,
  submitCropDiagnosisFeedback,
  useDiseaseCapabilities,
} from "@/features/multiCropDiagnosis";
import { GuidedDiagnosisCard } from "@/features/multiCropDiagnosis/components/GuidedDiagnosisCard";
import type {
  CropDiagnosisResult,
  CropSafetyStatus,
} from "@/features/multiCropDiagnosis/types";
import { VerifiedDiseaseKnowledgeCard } from "@/features/multiCropDiagnosis/components/VerifiedDiseaseKnowledgeCard";
import {
  RecommendationResultCard,
  type DiseaseRecommendation,
} from "../components/RecommendationResultCard";
import {
  loadDiseaseRecommendation,
  loadRestrictedDiseaseRecommendation,
} from "../services/recommendationApi";
import { logger } from "@/lib/logger";

import { QUALITY_ISSUE_KEY } from "../constants";
import type { CaptureMethod, PickedImage } from "../types";
import { checkImageQuality } from "../utils/imageQuality";
import { captureFromCamera, pickFromGallery } from "../utils/pickDiseaseImage";

const SUPPORTED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"] as const;
const ENTRY_BG = "#F8F5EC";
const ENTRY_SURFACE = "#FFFDF8";
const ENTRY_BORDER = "#D9CDB5";
const ENTRY_TEXT = "#173B2B";
const ENTRY_MUTED = "#4F5D55";
const ENTRY_GREEN = "#165B33";
const ENTRY_WARNING = "#C27A00";

const IDENTIFICATION_QUALITY_ISSUE_KEY: Record<string, string> = {
  too_small: "disease.identificationQualityTooSmall",
  unsupported_type: "disease.identificationQualityUnsupported",
  too_large: "disease.identificationQualityTooLarge",
};

export type DiseaseSubmissionFailure =
  | "image_missing"
  | "crop_missing"
  | "authentication_unavailable"
  | "crop_confirmation_required"
  | "crop_confirmation_already_used"
  | "unsupported_crop"
  | "unsupported_image"
  | "image_read_failed"
  | "request_already_running";

export function validateDiseaseSubmission(input: {
  imagePresent: boolean;
  crop: string;
  mimeType: string;
  tokenPresent: boolean;
  requestRunning: boolean;
  capabilityAuthorized?: boolean;
}): DiseaseSubmissionFailure | null {
  if (input.requestRunning) return "request_already_running";
  if (!input.imagePresent) return "image_missing";
  if (!input.crop) return "crop_missing";
  if (!input.tokenPresent) return "authentication_unavailable";
  if (input.capabilityAuthorized === false) return "unsupported_crop";
  if (!(SUPPORTED_MIME_TYPES as readonly string[]).includes(input.mimeType)) {
    return "unsupported_image";
  }
  return null;
}

export function DiseaseScreen() {
  const { t } = useTranslation();
  const cropDisplayName = (cropId: string) =>
    t(`disease.cropNames.${cropId}`, { defaultValue: cropId });
  const router = useRouter();
  const { colors } = useAppTheme();
  const { language } = useLanguage();
  const { selected: weatherFarm } = useSelectedFarm();
  const hasCoords =
    weatherFarm?.latitude != null && weatherFarm?.longitude != null;
  const { data: weatherData } = useWeather(
    weatherFarm
      ? {
          farmId: weatherFarm.id,
          latitude: weatherFarm.latitude,
          longitude: weatherFarm.longitude,
          name: weatherFarm.name,
        }
      : {},
    Boolean(weatherFarm) && hasCoords,
  );
  const tokenPresent = useAuthStore((state) => Boolean(state.tokens?.idToken));
  const capabilitySessionKey = useAuthStore(
    (state) => state.user?.id ?? "anonymous",
  );
  const capabilityQuery = useDiseaseCapabilities(
    tokenPresent,
    capabilitySessionKey,
  );
  const capabilitySnapshot = capabilityQuery.data;
  const availableCrops = (capabilitySnapshot?.crops ?? [])
    .filter((item) => item.visible && item.selectable)
    .map((item) => (item.cropId === "rice" ? "paddy" : item.cropId))
    .filter((item): item is SupportedCropId =>
      ["banana", "paddy", "cotton", "groundnut", "redgram", "chilli"].includes(
        item,
      ),
    );
  const [crop, setCrop] = useState("");
  const [cropIdentificationStatus, setCropIdentificationStatus] = useState<
    | CropIdentificationStatus
    | "idle"
    | "submitting"
    | "network_error"
    | "image_rejected"
    | "server_error"
  >("idle");
  const [cropSuggestionConfidence, setCropSuggestionConfidence] = useState<
    number | null
  >(null);
  const [cropIdentificationRequestId, setCropIdentificationRequestId] =
    useState<string | null>(null);
  const [suggestedCrop, setSuggestedCrop] = useState<SupportedCropId | null>(
    null,
  );
  const [cropProbabilities, setCropProbabilities] = useState<
    Record<string, number>
  >({});
  const [cropConfirmationToken, setCropConfirmationToken] = useState<
    string | null
  >(null);
  const [confirmationSubmitting, setConfirmationSubmitting] = useState(false);
  const [analysisSubmitting, setAnalysisSubmitting] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const isKvkFieldTest = buildProfile === "kvk_field_test";
  const [reviewConsent, setReviewConsent] = useState<boolean | null>(null);
  const [reviewSubmitting, setReviewSubmitting] = useState(false);
  const [reviewSaved, setReviewSaved] = useState(false);
  const [reviewCorrect, setReviewCorrect] = useState<boolean | null>(null);
  const [correctedLabel, setCorrectedLabel] = useState<string | null>(null);

  const [picked, setPicked] = useState<PickedImage | null>(null);
  const [issues, setIssues] = useState<string[]>([]);
  const [submitError, setSubmitError] =
    useState<DiseaseSubmissionFailure | null>(null);
  const [cropConfirmed, setCropConfirmed] = useState(false);
  const [jointResult, setJointResult] = useState<CropDiagnosisResult | null>(
    null,
  );
  const [recommendation, setRecommendation] =
    useState<DiseaseRecommendation | null>(null);
  const [identificationFailure, setIdentificationFailure] =
    useState<CropSafetyStatus | null>(null);
  const [requiresFreshPhoto, setRequiresFreshPhoto] = useState(false);
  const submissionInFlight = useRef(false);
  const cropIdRequestInFlight = useRef(false);
  const confirmationRequestInFlight = useRef(false);

  const sprayInsight = weatherData?.insights.find(
    (insight) => insight.category === "spraying",
  );
  const sprayMessageKey = sprayInsight
    ? INSIGHT_MESSAGE_KEY[sprayInsight.code]
    : undefined;
  const sprayMessage = sprayInsight
    ? sprayMessageKey
      ? t(sprayMessageKey, sprayInsight.params)
      : sprayInsight.message
    : null;
  const sprayAdvisory =
    sprayInsight && sprayMessage ? (
      <AgCard className="mt-3 border border-info/30 bg-info/5">
        <AgText variant="bodySmall" weight="semibold">
          {t("weather.categorySpraying")}: {sprayMessage}
        </AgText>
      </AgCard>
    ) : null;

  useEffect(() => {
    logger.info("disease.screen", "disease_screen_mounted");
  }, []);

  const identifyPhotoCrop = async (source: CaptureMethod) => {
    const image =
      source === "camera"
        ? await captureFromCamera({ base64: false })
        : await pickFromGallery({ base64: false });
    if (!image) return;
    const imageIssues = checkImageQuality(image).issues;
    setPicked(image);
    setIssues(imageIssues);
    setCrop("");
    setCropConfirmed(false);
    setCropSuggestionConfidence(null);
    setCropIdentificationRequestId(null);
    setSuggestedCrop(null);
    setCropProbabilities({});
    setCropConfirmationToken(null);
    setAnalysisComplete(false);
    setJointResult(null);
    setReviewConsent(null);
    setReviewSaved(false);
    setReviewCorrect(null);
    setCorrectedLabel(null);
    setRecommendation(null);
    setIdentificationFailure(null);
    setRequiresFreshPhoto(false);
    if (imageIssues.length) {
      imageIssues.forEach((issueCode) => {
        logger.warn("DiseaseScreen", "image quality check failed:", issueCode);
      });
      setCropIdentificationStatus("invalid_image");
      return;
    }
    await runCropIdentification(image);
  };

  const runCropIdentification = async (image: PickedImage) => {
    if (cropIdRequestInFlight.current) return;
    cropIdRequestInFlight.current = true;
    setCropIdentificationStatus("submitting");
    try {
      const result = await identifyCropInternalOnly(image);
      setIdentificationFailure(null);
      setCropIdentificationStatus(
        result.identified_crop ? "identified" : "uncertain",
      );
      setCropSuggestionConfidence(result.confidence);
      setCropIdentificationRequestId(result.request_id);
      setSuggestedCrop(result.identified_crop);
      setCropProbabilities(result.calibrated_probabilities ?? {});
      if (result.identified_crop) {
        const capability = findDiseaseCapability(
          capabilitySnapshot,
          result.identified_crop,
        );
        if (capability?.selectable) setCrop(result.identified_crop);
        else setCropIdentificationStatus("unsupported");
      }
    } catch (error) {
      console.error("[DiseaseScreen] crop identification failed:", error);
      const classified = classifyCropDiagnosisFailure(error);
      setIdentificationFailure(
        classified.outcome === "blocked" ? classified.status : "server_error",
      );
      const message = error instanceof Error ? error.message : "";
      setCropIdentificationStatus(
        message === "CROP_IMAGE_REJECTED"
          ? "image_rejected"
          : message === "NETWORK_UNREACHABLE"
            ? "network_error"
            : "server_error",
      );
    } finally {
      cropIdRequestInFlight.current = false;
    }
  };

  const changeCrop = () => {
    setCrop("");
    setPicked(null);
    setIssues([]);
    setSubmitError(null);
    setCropConfirmed(false);
    setJointResult(null);
    setCropIdentificationStatus("idle");
    setCropSuggestionConfidence(null);
    setCropIdentificationRequestId(null);
    setSuggestedCrop(null);
    setCropProbabilities({});
    setCropConfirmationToken(null);
    setAnalysisComplete(false);
    setIdentificationFailure(null);
    setRequiresFreshPhoto(false);
  };

  const selectCropAlternative = (nextCrop: SupportedCropId) => {
    setCrop(nextCrop);
    setCropConfirmed(false);
    setCropConfirmationToken(null);
    setAnalysisComplete(false);
    setSubmitError(null);
  };

  // Regular farmers (not internal/pilot/KVK testers) are blocked from the
  // controlled-tester flow below purely by role, not by any real lack of
  // crop data. Route them to the general-release, OpenAI-vision-backed
  // diagnosis screen instead of the blocking "tester role required"
  // message — this is the actual farmer-facing disease detection path.
  // Every other gating condition (signed out, still loading, query error,
  // zero crops in the registry) falls through unchanged to the block below.
  //
  // BUG (found in production during the 2026-08 pre-release smoke test):
  // this used to also require `availableCrops.length > 0`. `availableCrops`
  // is filtered from `capabilitySnapshot.crops` by `item.selectable` -- i.e.
  // it's the tester-only crop-identification model list. For exactly the
  // population this branch exists to help (regular farmers, whose crops are
  // never `selectable` because they're not testers), that list is *always*
  // empty, so the guard could never pass for a real farmer and every one of
  // them fell through to the "authorized controlled testers only" dead end
  // below instead of reaching GeneralDiagnosisScreen -- i.e. disease
  // detection, the app's headline feature, was unusable in production.
  if (
    tokenPresent &&
    !capabilityQuery.isPending &&
    !capabilityQuery.isError &&
    !capabilitySnapshot?.cropIdentification.selectable &&
    capabilitySnapshot?.cropIdentification.disabledReason ===
      "TESTER_ROLE_REQUIRED"
  ) {
    return <GeneralDiagnosisScreen />;
  }

  if (
    !tokenPresent ||
    capabilityQuery.isPending ||
    capabilityQuery.isError ||
    !capabilitySnapshot?.cropIdentification.selectable ||
    availableCrops.length === 0
  ) {
    const messageKey = !tokenPresent
      ? "disease.errorSignIn"
      : capabilityQuery.isPending
        ? "disease.capabilitiesLoading"
        : capabilityQuery.isError
          ? "disease.capabilitiesUnavailable"
          : capabilitySnapshot?.cropIdentification.disabledReason ===
              "TESTER_ROLE_REQUIRED"
            ? "disease.testerRoleRequired"
            : availableCrops.length === 0
              ? "disease.noCropsAvailable"
              : "disease.releaseNotAuthorized";
    return (
      <AgScreen testID="disease-detection-screen" scroll>
        <AgCard className="mt-4 gap-2">
          <AgText weight="bold">{t("disease.availabilityTitle")}</AgText>
          <AgText color="muted">{t(messageKey)}</AgText>
          {capabilityQuery.isError ||
          !capabilitySnapshot?.cropIdentification.selectable ||
          availableCrops.length === 0 ? (
            <AgButton
              title={t("disease.retryCapabilities")}
              variant="secondary"
              onPress={() => void capabilityQuery.refetch()}
            />
          ) : null}
          <AgButton
            title={t("common.back")}
            variant="ghost"
            onPress={() => router.back()}
          />
        </AgCard>
      </AgScreen>
    );
  }

  if (!crop) {
    return (
      <AgScreen
        testID="disease-detection-screen"
        scroll
        backgroundColor={ENTRY_BG}
        contentContainerStyle={entryStyles.screenContent}
      >
        {!picked ? (
          <>
            <View style={entryStyles.header}>
              <AgPressable
                haptic={false}
                onPress={() => router.back()}
                accessibilityRole="button"
                accessibilityLabel={t("common.back")}
                style={({ pressed }) => [
                  entryStyles.headerButton,
                  pressed && entryStyles.pressed,
                ]}
              >
                <ArrowLeft size={28} color={ENTRY_TEXT} />
              </AgPressable>
              <View style={entryStyles.brand} accessibilityLabel={t("auth.brandAccessibility")}>
                <Sprout size={38} color={ENTRY_GREEN} strokeWidth={1.7} />
                <AgText variant="bodySmall" weight="bold" style={entryStyles.brandText}>
                  AgrowAI
                </AgText>
              </View>
              <AgPressable
                haptic={false}
                onPress={() => router.push("/disease/history")}
                accessibilityRole="button"
                accessibilityLabel={t("disease.viewHistory")}
                style={({ pressed }) => [entryStyles.historyButton, pressed && entryStyles.pressed]}
              >
                <History size={24} color={ENTRY_TEXT} />
                <AgText variant="bodySmall" weight="semibold" style={entryStyles.primaryText}>
                  {t("disease.viewHistory")}
                </AgText>
              </AgPressable>
            </View>

            <View style={entryStyles.intro}>
              <AgText variant="caption" weight="bold" style={entryStyles.eyebrow}>
                {t("disease.plantHealth")}
              </AgText>
              <AgText variant="headingXL" weight="bold" style={entryStyles.title} accessibilityRole="header">
                {t("disease.title")}
              </AgText>
              <AgText variant="body" style={entryStyles.introMessage}>
                {t("disease.welcomeMessage")}
              </AgText>
            </View>

            <View
              style={entryStyles.scanCard}
              accessible={false}
              importantForAccessibility="no-hide-descendants"
            >
              <View style={[entryStyles.scanCorner, entryStyles.topLeft]} />
              <View style={[entryStyles.scanCorner, entryStyles.topRight]} />
              <View style={[entryStyles.scanCorner, entryStyles.bottomLeft]} />
              <View style={[entryStyles.scanCorner, entryStyles.bottomRight]} />
              <View style={entryStyles.leafStage}>
                <Leaf size={150} color={ENTRY_GREEN} strokeWidth={1.15} />
                <View style={entryStyles.lesion} />
              </View>
              <View style={entryStyles.photoGuideRow}>
                <View style={entryStyles.photoGuideItem}>
                  <Sun size={27} color={ENTRY_GREEN} />
                  <AgText variant="caption" weight="semibold" center style={entryStyles.primaryText}>{t("disease.goodLight")}</AgText>
                </View>
                <View style={entryStyles.guideDivider} />
                <View style={entryStyles.photoGuideItem}>
                  <Search size={27} color={ENTRY_GREEN} />
                  <AgText variant="caption" weight="semibold" center style={entryStyles.primaryText}>{t("disease.closeView")}</AgText>
                </View>
                <View style={entryStyles.guideDivider} />
                <View style={entryStyles.photoGuideItem}>
                  <Leaf size={27} color={ENTRY_GREEN} />
                  <AgText variant="caption" weight="semibold" center style={entryStyles.primaryText}>{t("disease.oneLeaf")}</AgText>
                </View>
              </View>
            </View>

            <AgPressable
              onPress={() => void identifyPhotoCrop("camera")}
              disabled={cropIdentificationStatus === "submitting"}
              accessibilityRole="button"
              accessibilityLabel={t("disease.takePhoto")}
              accessibilityHint={t("disease.takePhotoSubtitle")}
              accessibilityState={{
                disabled: cropIdentificationStatus === "submitting",
              }}
              style={({ pressed }) => [
                entryStyles.actionCard,
                entryStyles.primaryAction,
                pressed && entryStyles.pressed,
              ]}
            >
              <Camera size={27} color={ENTRY_TEXT} />
              <AgText variant="headingS" weight="semibold" style={entryStyles.primaryActionText}>{t("disease.takePhoto")}</AgText>
            </AgPressable>

            <AgPressable
              onPress={() => void identifyPhotoCrop("gallery")}
              disabled={cropIdentificationStatus === "submitting"}
              accessibilityRole="button"
              accessibilityLabel={t("disease.chooseGallery")}
              accessibilityHint={t("disease.chooseGallerySubtitle")}
              accessibilityState={{
                disabled: cropIdentificationStatus === "submitting",
              }}
              style={({ pressed }) => [
                entryStyles.actionCard,
                entryStyles.secondaryAction,
                pressed && entryStyles.pressed,
              ]}
            >
              <Images size={25} color={ENTRY_GREEN} />
              <AgText variant="headingS" weight="semibold" style={entryStyles.greenText}>{t("disease.chooseGallery")}</AgText>
            </AgPressable>

            <View style={entryStyles.controlCard}>
              <View
                style={entryStyles.controlIcon}
                accessible={false}
                importantForAccessibility="no-hide-descendants"
              >
                <ShieldCheck size={34} color={ENTRY_WARNING} />
              </View>
              <View style={entryStyles.flexCopy}>
                <AgText
                  variant="body"
                  weight="semibold"
                  style={entryStyles.controlTitle}
                >
                  {t("disease.youStayInControl")}
                </AgText>
                <AgText variant="bodySmall" style={entryStyles.mutedText}>
                  {t("disease.youStayInControlMessage")}
                </AgText>
                <AgText variant="caption" style={entryStyles.controlCaution}>
                  {t("disease.cropIdentificationCaution")}
                </AgText>
              </View>
            </View>

            <View style={entryStyles.tipCard}>
              <Lightbulb size={25} color={ENTRY_GREEN} />
              <View style={entryStyles.flexCopy}>
                <AgText variant="bodySmall" weight="bold" style={entryStyles.primaryText}>{t("disease.photoTipTitle")}</AgText>
                <AgText variant="bodySmall" style={entryStyles.primaryText}>{t("disease.photoTipMessage")}</AgText>
              </View>
            </View>

            <AgText variant="caption" center style={entryStyles.disclaimer}>
              {t("disease.entryDisclaimer")}
            </AgText>
          </>
        ) : (
          <View className="mt-5 gap-3">
            <Image
              source={{ uri: picked.uri }}
              style={{ width: "100%", aspectRatio: 1, borderRadius: 16 }}
              contentFit="cover"
            />
            {cropIdentificationStatus === "submitting" ? (
              <ActivityIndicator color={colors.primary} />
            ) : null}
            {cropIdentificationStatus === "invalid_image" ? (
              <AgCard className="gap-2">
                <AgText weight="bold">{t("disease.qualityTitle")}</AgText>
                {issues.map((issueCode) => (
                  <AgText key={issueCode} color="muted">
                    {t(
                      IDENTIFICATION_QUALITY_ISSUE_KEY[issueCode] ??
                        "disease.qualityGeneric",
                    )}
                  </AgText>
                ))}
                <AgText variant="caption">
                  {t("disease.verifyOfficialExpert")}
                </AgText>
              </AgCard>
            ) : null}
            {cropIdentificationStatus === "network_error" ? (
              <AgCard className="gap-2">
                <AgText weight="bold">
                  {t("disease.identificationConnectionTitle")}
                </AgText>
                <AgText color="muted">
                  {t("disease.identificationConnectionMessage")}
                </AgText>
                <AgButton
                  title={t("disease.retryIdentification")}
                  variant="secondary"
                  onPress={() => void runCropIdentification(picked)}
                  disabled={cropIdRequestInFlight.current}
                />
              </AgCard>
            ) : null}
            {cropIdentificationStatus === "image_rejected" ? (
              <AgCard className="gap-2">
                <AgText weight="bold">{t("disease.imageRejectedTitle")}</AgText>
                <AgText color="muted">
                  {t("disease.imageRejectedMessage")}
                </AgText>
                <AgButton
                  title={t("disease.retakePhoto")}
                  variant="secondary"
                  onPress={changeCrop}
                />
              </AgCard>
            ) : null}
            {cropIdentificationStatus === "server_error" ? (
              <AgCard className="gap-2">
                <AgText weight="bold">{t("disease.serverErrorTitle")}</AgText>
                <AgText color="muted">{t("disease.serverErrorMessage")}</AgText>
                <AgButton
                  title={t("disease.retryIdentification")}
                  variant="secondary"
                  onPress={() => void runCropIdentification(picked)}
                  disabled={cropIdRequestInFlight.current}
                />
              </AgCard>
            ) : null}
            {identificationFailure &&
            identificationFailure !== "server_error" ? (
              <AgCard className="gap-2">
                <AgText color="danger">
                  {t(`disease.errors.${identificationFailure}`)}
                </AgText>
              </AgCard>
            ) : null}
            {cropIdentificationStatus === "uncertain" ||
            cropIdentificationStatus === "unsupported" ? (
              <AgCard className="gap-2">
                <AgText weight="bold">
                  {t("disease.identificationUncertain")}
                </AgText>
                <AgText color="muted">{t("disease.cropChoicePrompt")}</AgText>
              </AgCard>
            ) : null}
            {cropIdentificationStatus === "non_plant" ? (
              <AgCard>
                <AgText color="danger">{t("disease.nonPlantBlocked")}</AgText>
              </AgCard>
            ) : null}
            {cropIdentificationStatus !== "submitting" ? (
              <View className="gap-2">
                <AgText weight="semibold">
                  {t("disease.cropChoicePrompt")}
                </AgText>
                {availableCrops.map((cropId) => (
                  <AgButton
                    key={cropId}
                    title={cropDisplayName(cropId)}
                    variant="secondary"
                    accessibilityLabel={t("disease.chooseCropAccessibility", {
                      crop: cropDisplayName(cropId),
                    })}
                    onPress={() => selectCropAlternative(cropId)}
                  />
                ))}
              </View>
            ) : null}
            <AgButton
              title={t("disease.retakePhoto")}
              variant="ghost"
              onPress={changeCrop}
            />
          </View>
        )}
      </AgScreen>
    );
  }

  if (crop && !cropConfirmed) {
    return (
      <AgScreen
        scroll
        padded={false}
        backgroundColor={colors.bg}
        contentContainerStyle={confirmationStyles.screenContent}
      >
        <View style={confirmationStyles.content}>
          <AgPressable
            haptic={false}
            onPress={() => router.back()}
            accessibilityRole="button"
            accessibilityLabel={t("common.back")}
            style={confirmationStyles.backButton}
          >
            <ArrowLeft size={30} color={colors.text} />
          </AgPressable>
          {picked ? (
            <Image
              source={{ uri: picked.uri }}
              style={[confirmationStyles.image, { borderColor: colors.border }]}
              contentFit="cover"
            />
          ) : null}
          <View
            style={[
              confirmationStyles.suggestionCard,
              {
                backgroundColor: `${colors.primary}0B`,
                borderColor: `${colors.primary}35`,
              },
            ]}
          >
            <View
              style={[
                confirmationStyles.suggestionIcon,
                { backgroundColor: `${colors.primary}1A` },
              ]}
            >
              <Leaf size={34} color={colors.primary} />
            </View>
            <View style={confirmationStyles.suggestionCopy}>
              <AgText variant="headingS" weight="bold">
                {t("disease.aiSuggestion", {
                  crop: cropDisplayName(suggestedCrop ?? crop),
                })}
              </AgText>
              <View
                style={[
                  confirmationStyles.confidenceBadge,
                  { backgroundColor: `${colors.primary}12` },
                ]}
              >
                <ShieldCheck size={17} color={colors.primary} />
                <AgText variant="bodySmall" color="primary" weight="semibold">
                  {Number.isFinite(cropSuggestionConfidence)
                    ? t("disease.cropConfidence", {
                        confidence: Math.round(
                          (cropSuggestionConfidence as number) * 100,
                        ),
                      })
                    : t("disease.confidenceUnavailable")}
                </AgText>
              </View>
              {suggestedCrop &&
              Number.isFinite(cropProbabilities[suggestedCrop])
                ? (() => {
                    const runnerUp = Object.entries(cropProbabilities)
                      .filter(
                        ([candidate, probability]) =>
                          candidate !== suggestedCrop &&
                          Number.isFinite(probability),
                      )
                      .sort(([, left], [, right]) => right - left)[0];
                    return runnerUp &&
                      cropProbabilities[suggestedCrop] - runnerUp[1] <= 0.15 ? (
                      <AgText variant="caption" color="muted">
                        {t("disease.runnerUpCrop", {
                          crop: cropDisplayName(runnerUp[0]),
                          confidence: Math.round(runnerUp[1] * 100),
                        })}
                      </AgText>
                    ) : null;
                  })()
                : null}
              <AgText
                variant="bodySmall"
                color="muted"
                style={confirmationStyles.notice}
              >
                {t("disease.confirmationNotice")}
              </AgText>
            </View>
          </View>
          {submitError ? (
            <AgCard className="border border-danger/40 bg-danger/10">
              <AgText variant="bodySmall" color="danger">
                {submitError === "crop_confirmation_already_used"
                  ? t("disease.photoAlreadyConfirmed")
                  : t("disease.errorConfirmCrop")}
              </AgText>
            </AgCard>
          ) : null}
          <AgButton
            title={t("disease.confirmSuggestedCrop")}
            accessibilityLabel={t("disease.confirmCropAccessibility")}
            size="lg"
            leftIcon={<ShieldCheck size={22} color={colors.onPrimary} />}
            loading={confirmationSubmitting}
            disabled={confirmationSubmitting || cropConfirmed}
            onPress={() => {
              if (!cropIdentificationRequestId) {
                setSubmitError("crop_confirmation_required");
                return;
              }
              if (cropConfirmed || confirmationRequestInFlight.current) return;
              confirmationRequestInFlight.current = true;
              setConfirmationSubmitting(true);
              const confirmation = confirmInternalCrop({
                requestId: cropIdentificationRequestId,
                confirmedCrop: crop as SupportedCropId,
                correction: suggestedCrop !== crop,
              });
              void confirmation
                .then((receipt) => {
                  setCropConfirmationToken(receipt.confirmation_token);
                  setAnalysisComplete(false);
                  setCropConfirmed(true);
                  setSubmitError(null);
                })
                .catch((error: unknown) => {
                  setSubmitError(
                    error instanceof Error &&
                      error.message === "CROP_CONFIRMATION_ALREADY_USED"
                      ? "crop_confirmation_already_used"
                      : "crop_confirmation_required",
                  );
                })
                .finally(() => {
                  confirmationRequestInFlight.current = false;
                  setConfirmationSubmitting(false);
                });
            }}
          />
          <View style={confirmationStyles.choiceHeading}>
            <Sprout size={24} color={colors.primary} />
            <View style={confirmationStyles.choiceHeadingCopy}>
              <AgText variant="bodyLarge" weight="bold">
                {t("disease.cropChoicePrompt")}
              </AgText>
              <AgText variant="bodySmall" color="muted">
                {t("disease.cropChoiceSubtitle")}
              </AgText>
            </View>
          </View>
          <View
            style={[
              confirmationStyles.cropList,
              { backgroundColor: colors.card, borderColor: colors.border },
            ]}
          >
            {availableCrops.map((cropId, index) => (
              <AgPressable
                key={cropId}
                haptic={false}
                accessibilityLabel={t("disease.chooseCropAccessibility", {
                  crop: cropDisplayName(cropId),
                })}
                accessibilityRole="radio"
                accessibilityState={{ selected: cropId === crop }}
                onPress={() => selectCropAlternative(cropId)}
                style={[
                  confirmationStyles.cropRow,
                  {
                    borderBottomColor: colors.border,
                    borderBottomWidth:
                      index === availableCrops.length - 1
                        ? 0
                        : StyleSheet.hairlineWidth,
                  },
                  cropId === crop && {
                    backgroundColor: `${colors.primary}0D`,
                  },
                ]}
              >
                <View style={confirmationStyles.cropRowContent}>
                  <Sprout size={23} color={colors.primary} />
                  <AgText
                    variant="bodyLarge"
                    weight="semibold"
                    style={confirmationStyles.cropLabel}
                  >
                    {cropDisplayName(cropId)}
                  </AgText>
                  <View
                    style={[
                      confirmationStyles.radio,
                      {
                        borderColor:
                          cropId === crop
                            ? colors.primary
                            : colors.textDisabled,
                      },
                    ]}
                  >
                    {cropId === crop ? (
                      <View
                        style={[
                          confirmationStyles.radioDot,
                          { backgroundColor: colors.primary },
                        ]}
                      />
                    ) : null}
                  </View>
                </View>
              </AgPressable>
            ))}
          </View>
          <AgButton
            title={t("disease.takeAnotherImage")}
            variant="outline"
            size="lg"
            leftIcon={<Camera size={22} color={colors.primary} />}
            onPress={changeCrop}
          />
        </View>
      </AgScreen>
    );
  }

  const selectedCapability = findDiseaseCapability(capabilitySnapshot, crop);
  if (!selectedCapability?.selectable) {
    return (
      <AgScreen scroll>
        <AgCard className="mt-4 gap-2">
          <AgText weight="bold">{t("disease.availabilityTitle")}</AgText>
          <AgText color="muted">{t("disease.releaseNotAuthorized")}</AgText>
        </AgCard>
      </AgScreen>
    );
  }

  if (crop === "banana") {
    return (
      <BananaDiseaseDetectionScreen
        onChangeCrop={changeCrop}
        initialImage={picked}
        cropConfirmationToken={cropConfirmationToken}
        suggestedCropId={suggestedCrop}
        suggestedCropName={
          suggestedCrop ? cropDisplayName(suggestedCrop) : null
        }
        identificationConfidence={cropSuggestionConfidence}
        farmId={weatherFarm?.id}
      />
    );
  }
  const onPick = async (source: CaptureMethod) => {
    await identifyPhotoCrop(source);
  };

  const reset = () => {
    changeCrop();
  };

  const onAnalyze = async () => {
    if (analysisComplete) return;
    logger.info("disease.submit", "analyze_handler_entered");
    logger.info("disease.submit", "submission_context", {
      image_present: Boolean(picked),
      selected_crop_present: Boolean(crop),
      selected_crop: crop || null,
      consent_state: false,
      token_present: tokenPresent,
    });
    logger.info("disease.submit", "validation_started");

    const failure = validateDiseaseSubmission({
      imagePresent: Boolean(picked),
      crop,
      mimeType: picked?.mimeType ?? "",
      tokenPresent,
      requestRunning: submissionInFlight.current,
      capabilityAuthorized: selectedCapability.selectable,
    });
    if (failure) {
      setSubmitError(failure);
      logger.info("disease.submit", "validation_failed_reason", {
        category: failure,
      });
      logger.info("disease.submit", "submit_failed", { category: failure });
      logger.info("disease.submit", "submit_finished");
      return;
    }
    if (!cropConfirmed || !cropConfirmationToken) {
      setSubmitError("crop_confirmation_required");
      logger.info("disease.submit", "validation_failed_reason", {
        category: "crop_confirmation_required",
      });
      logger.info("disease.submit", "submit_finished");
      return;
    }

    submissionInFlight.current = true;
    setAnalysisSubmitting(true);
    setSubmitError(null);
    logger.info("disease.submit", "validation_passed");
    try {
      if (crop === "chilli" || crop === "redgram") {
        const result = await cropDiagnosisAdapter(
          crop,
          selectedCapability,
        ).predict({
          uri: picked!.uri,
          mimeType: picked!.mimeType,
          cropConfirmed: true,
          cropConfirmationToken,
          farmId: weatherFarm?.id,
          kvkSession: isKvkFieldTest && crop === "redgram",
          reviewConsent:
            isKvkFieldTest && crop === "redgram"
              ? (reviewConsent ?? false)
              : undefined,
        });
        if ("outcome" in result) {
          setJointResult(result);
          if (result.outcome === "blocked") {
            setCropConfirmationToken(null);
            setCropIdentificationRequestId(null);
            setRequiresFreshPhoto(true);
            setAnalysisComplete(true);
          }
          if (result.outcome === "accepted" || result.outcome === "uncertain") {
            setAnalysisComplete(true);
          }
          if (result.outcome === "accepted" && result.class_id) {
            const next = await loadRestrictedDiseaseRecommendation(
              crop,
              result.class_id,
            ).catch(() => null);
            setRecommendation(next);
          }
        }
        return;
      }
      if (crop === "paddy" || crop === "cotton" || crop === "groundnut") {
        const result = await cropDiagnosisAdapter(
          crop === "paddy" ? "rice" : crop,
          selectedCapability,
        ).predict({
          uri: picked!.uri,
          mimeType: picked!.mimeType,
          cropConfirmed: true,
          cropConfirmationToken,
          farmId: weatherFarm?.id,
        });
        if ("outcome" in result) {
          setJointResult(result);
          if (result.outcome === "blocked") {
            setCropConfirmationToken(null);
            setCropIdentificationRequestId(null);
            setRequiresFreshPhoto(true);
            setAnalysisComplete(true);
          }
          if (result.outcome === "accepted" || result.outcome === "uncertain") {
            setAnalysisComplete(true);
          }
          if (result.outcome === "accepted" && result.class_id) {
            const next = await loadDiseaseRecommendation(
              crop,
              result.class_id,
            ).catch(() => null);
            setRecommendation(next);
          }
        }
        return;
      }
      setSubmitError("unsupported_crop");
    } catch {
      setCropConfirmationToken(null);
      setCropIdentificationRequestId(null);
      setRequiresFreshPhoto(true);
      setAnalysisComplete(true);
      setSubmitError("image_read_failed");
      logger.info("disease.submit", "submit_failed", {
        category: "image_read_failed",
      });
      logger.info("disease.submit", "submit_finished");
    } finally {
      submissionInFlight.current = false;
      setAnalysisSubmitting(false);
    }
  };

  const submitKvkReview = async () => {
    if (
      !jointResult ||
      !("report_id" in jointResult) ||
      !jointResult.report_id ||
      reviewCorrect === null ||
      (!reviewCorrect && !correctedLabel)
    )
      return;
    setReviewSubmitting(true);
    try {
      await httpClient.post(`/disease/${jointResult.report_id}/kvk-review`, {
        correct: reviewCorrect,
        corrected_label: reviewCorrect ? null : correctedLabel,
      });
      setReviewSaved(true);
    } finally {
      setReviewSubmitting(false);
    }
  };

  const localError = submitError
    ? {
        image_missing: t("disease.qualityMissing"),
        crop_missing: t("disease.errorSelectCrop"),
        authentication_unavailable: t("disease.errorSignIn"),
        crop_confirmation_required: t("disease.errorConfirmCrop"),
        crop_confirmation_already_used: t("disease.photoAlreadyConfirmed"),
        unsupported_crop: t("disease.releaseNotAuthorized"),
        unsupported_image: t("disease.qualityUnsupported"),
        image_read_failed: t("disease.qualityCorrupted"),
        request_already_running: t("disease.analysisAlreadyRunning"),
      }[submitError]
    : null;

  return (
    <AgScreen scroll>
      <View className="mt-2 flex-row items-center justify-between">
        <View className="flex-row items-center gap-2">
          <AgPressable
            onPress={() => router.back()}
            accessibilityRole="button"
            accessibilityLabel={t("common.back")}
            className="-ml-2 h-10 w-10 items-center justify-center"
          >
            <ArrowLeft size={24} color={colors.text} />
          </AgPressable>
          <AgText variant="headingM" weight="bold">
            {`${cropDisplayName(crop)} ${t("disease.title")}`}
          </AgText>
        </View>
        <AgPressable
          onPress={() => router.push("/disease/history")}
          accessibilityRole="button"
          accessibilityLabel={t("disease.viewHistory")}
          className="h-10 w-10 items-center justify-center"
        >
          <History size={20} color={colors.text} />
        </AgPressable>
      </View>

      {!picked ? (
        <View className="mt-6 items-center">
          <View className="mb-4 h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <ScanLine size={30} color={colors.primary} />
          </View>
          <AgText variant="headingS" weight="bold" center>
            {t("disease.welcomeTitle")}
          </AgText>
          <AgText variant="body" color="muted" center className="mb-6 mt-2">
            {t("disease.welcomeMessage")}
          </AgText>
          <AgButton
            title={t("disease.takePhoto")}
            leftIcon={<Camera size={20} color={colors.onPrimary} />}
            onPress={() => onPick("camera")}
            size="lg"
            className="w-full"
          />
          <AgButton
            title={t("disease.chooseGallery")}
            variant="secondary"
            leftIcon={<Images size={20} color={colors.primary} />}
            onPress={() => onPick("gallery")}
            size="lg"
            className="mt-3 w-full"
          />
        </View>
      ) : (
        <View className="mt-4">
          <Image
            source={{ uri: picked.uri }}
            style={{ width: "100%", aspectRatio: 1, borderRadius: 16 }}
            contentFit="cover"
          />

          {issues.length ? (
            <AgCard className="mt-4 border border-warning/40 bg-warning/10">
              <View className="mb-1 flex-row items-center gap-2">
                <TriangleAlert size={18} color={colors.warning} />
                <AgText variant="body" weight="semibold">
                  {t("disease.qualityTitle")}
                </AgText>
              </View>
              {issues.map((code) => (
                <AgText key={code} variant="bodySmall" color="muted">
                  • {t(QUALITY_ISSUE_KEY[code] ?? "disease.qualityGeneric")}
                </AgText>
              ))}
              <AgText variant="caption" color="muted" className="mt-2">
                {t("disease.qualityHelp")}
              </AgText>
            </AgCard>
          ) : localError ? (
            <AgCard className="mt-4 border border-danger/40 bg-danger/10">
              <AgText variant="bodySmall" color="danger">
                {localError}
              </AgText>
            </AgCard>
          ) : null}

          {!issues.length ? (
            <CropPhotoConfirmation
              cropId={crop}
              cropName={cropDisplayName(crop)}
              suggestedCropId={suggestedCrop}
              suggestedCropName={
                suggestedCrop ? cropDisplayName(suggestedCrop) : null
              }
              identificationConfidence={cropSuggestionConfidence}
              confirmed={cropConfirmed}
              onConfirm={() => {
                setCropConfirmed(true);
                setSubmitError(null);
              }}
              onChangeCrop={changeCrop}
              onRetake={reset}
            />
          ) : null}

          {isKvkFieldTest &&
          crop === "redgram" &&
          cropConfirmed &&
          !jointResult ? (
            <AgCard className="mt-4 gap-3">
              <AgText weight="bold">{t("disease.kvkConsentTitle")}</AgText>
              <AgText color="muted">{t("disease.kvkConsentMessage")}</AgText>
              <View style={{ flexDirection: "row", gap: 12 }}>
                <View style={{ flex: 1 }}>
                  <AgButton
                    title={t("disease.kvkConsentYes")}
                    variant={reviewConsent === true ? "primary" : "secondary"}
                    onPress={() => setReviewConsent(true)}
                  />
                </View>
                <View style={{ flex: 1 }}>
                  <AgButton
                    title={t("disease.kvkConsentNo")}
                    variant={reviewConsent === false ? "primary" : "secondary"}
                    onPress={() => setReviewConsent(false)}
                  />
                </View>
              </View>
              <AgText variant="caption" color="muted">
                {t("disease.kvkConsentHelpUnaffected")}
              </AgText>
            </AgCard>
          ) : null}

          <>
            {!issues.length && !requiresFreshPhoto ? (
              <AgButton
                title={t("disease.analyze")}
                onPress={() => {
                  logger.info("disease.submit", "analyze_button_pressed");
                  void onAnalyze();
                }}
                loading={analysisSubmitting}
                disabled={
                  analysisSubmitting ||
                  analysisComplete ||
                  (isKvkFieldTest &&
                    crop === "redgram" &&
                    reviewConsent === null)
                }
                size="lg"
                className="mt-6"
              />
            ) : null}
            {jointResult &&
            "test_mode" in jointResult &&
            jointResult.test_mode ? (
              <AgCard className="mt-4 border-2 border-danger bg-danger/10">
                <AgText variant="body" weight="bold" color="danger" center>
                  {jointResult.test_mode.banner_text}
                </AgText>
              </AgCard>
            ) : null}
            {jointResult?.outcome === "accepted" && jointResult.class_id ? (
              <>
                <AcceptedDiagnosisCard
                  title={jointResult.class_id.replaceAll("_", " ")}
                  explanation={t("disease.acceptedPolicyExplanation")}
                  confidence={jointResult.calibrated_confidence}
                  onFeedback={() => {
                    void submitCropDiagnosisFeedback(crop, {
                      request_id: `mobile-${Date.now()}`,
                      outcome_helpful: true,
                    });
                  }}
                />
                {sprayAdvisory}
                <VerifiedDiseaseKnowledgeCard knowledge={null} />
                {recommendation ? (
                  <RecommendationResultCard
                    recommendation={recommendation}
                    language={language === "en" ? "en" : "ta"}
                  />
                ) : (
                  <AgCard
                    className="mt-3"
                    style={{ borderColor: colors.border }}
                  >
                    <AgText variant="bodySmall" color="muted">
                      {t("banana.ui.treatmentPendingVerification")}
                    </AgText>
                  </AgCard>
                )}
              </>
            ) : null}
            {isKvkFieldTest &&
            crop === "redgram" &&
            reviewConsent === true &&
            (jointResult?.outcome === "accepted" ||
              jointResult?.outcome === "uncertain") &&
            "report_id" in jointResult &&
            jointResult.report_id ? (
              <AgCard className="mt-4 gap-3">
                <AgText weight="bold">{t("disease.kvkReviewTitle")}</AgText>
                <AgText color="muted">{t("disease.kvkReviewQuestion")}</AgText>
                <View style={{ flexDirection: "row", gap: 12 }}>
                  <View style={{ flex: 1 }}>
                    <AgButton
                      title={t("common.yes")}
                      variant={reviewCorrect === true ? "primary" : "secondary"}
                      onPress={() => {
                        setReviewCorrect(true);
                        setCorrectedLabel(null);
                      }}
                    />
                  </View>
                  <View style={{ flex: 1 }}>
                    <AgButton
                      title={t("common.no")}
                      variant={
                        reviewCorrect === false ? "primary" : "secondary"
                      }
                      onPress={() => setReviewCorrect(false)}
                    />
                  </View>
                </View>
                {reviewCorrect === false ? (
                  <View style={{ gap: 8 }}>
                    {(
                      [
                        "redgram__healthy",
                        "redgram__leaf_spot",
                        "redgram__sterility_mosaic",
                      ] as const
                    ).map((label) => (
                      <AgButton
                        key={label}
                        title={t(`disease.kvkReviewLabels.${label}`)}
                        variant={
                          correctedLabel === label ? "primary" : "secondary"
                        }
                        onPress={() => setCorrectedLabel(label)}
                      />
                    ))}
                  </View>
                ) : null}
                <AgButton
                  title={
                    reviewSaved
                      ? t("disease.kvkReviewSaved")
                      : t("disease.kvkReviewSave")
                  }
                  loading={reviewSubmitting}
                  disabled={
                    reviewSaved ||
                    reviewCorrect === null ||
                    (reviewCorrect === false && !correctedLabel)
                  }
                  onPress={() => void submitKvkReview()}
                />
              </AgCard>
            ) : null}
            {jointResult?.outcome === "uncertain" ? (
              <UncertainDiagnosisCard
                onRetake={reset}
                onCheckNutrients={() =>
                  router.push({
                    pathname: "/nutrient",
                    params: { source: "disease_detection", crop },
                  })
                }
              />
            ) : null}
            {(jointResult?.outcome === "accepted" ||
              jointResult?.outcome === "uncertain") &&
            picked ? (
              <GuidedDiagnosisCard
                crop={crop}
                primaryImage={picked}
                onExpertReview={() => router.push("/experts")}
              />
            ) : null}
            {jointResult?.outcome === "blocked" ? (
              <AgCard className="mt-4 border border-warning/40 bg-warning/10">
                <AgText variant="body" weight="semibold">
                  {t(
                    jointResult.status === "crop_identity_uncertain"
                      ? "disease.cropIdentityUnverified"
                      : "disease.analysisSafelyBlocked",
                  )}
                </AgText>
                <AgText variant="bodySmall" color="muted" className="mt-2">
                  {t(`disease.errors.${jointResult.status}`, {
                    defaultValue:
                      jointResult.status === "confirmation_replayed"
                        ? t("disease.photoAlreadyAnalyzed")
                        : jointResult.message,
                  })}
                </AgText>
                <AgButton
                  title={t("disease.startFreshPhoto")}
                  variant="secondary"
                  onPress={reset}
                />
              </AgCard>
            ) : null}
          </>
        </View>
      )}
    </AgScreen>
  );
}

const confirmationStyles = StyleSheet.create({
  screenContent: { paddingBottom: 34 },
  content: { width: "100%", paddingHorizontal: 20, gap: 18 },
  backButton: {
    width: 48,
    height: 48,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 4,
    marginLeft: -8,
  },
  image: {
    width: "100%",
    aspectRatio: 3.2,
    minHeight: 150,
    maxHeight: 220,
    borderRadius: 22,
    borderWidth: StyleSheet.hairlineWidth,
  },
  suggestionCard: {
    width: "100%",
    borderWidth: 1,
    borderRadius: 22,
    padding: 18,
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 16,
  },
  suggestionIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: "center",
    justifyContent: "center",
  },
  suggestionCopy: { flex: 1, minWidth: 0, gap: 8 },
  confidenceBadge: {
    minHeight: 34,
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  notice: { marginTop: 4, lineHeight: 21 },
  choiceHeading: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
    marginTop: 4,
  },
  choiceHeadingCopy: { flex: 1, minWidth: 0, gap: 2 },
  cropList: {
    width: "100%",
    borderWidth: 1,
    borderRadius: 20,
    overflow: "hidden",
  },
  cropRow: {
    width: "100%",
    minHeight: 68,
  },
  cropRowContent: {
    minHeight: 68,
    width: "100%",
    paddingHorizontal: 18,
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
  },
  cropLabel: { flex: 1, minWidth: 0 },
  radio: {
    width: 28,
    height: 28,
    borderRadius: 14,
    borderWidth: 2,
    alignItems: "center",
    justifyContent: "center",
  },
  radioDot: { width: 14, height: 14, borderRadius: 7 },
});

const entryStyles = StyleSheet.create({
  screenContent: { paddingTop: 4, paddingBottom: 24, gap: 12 },
  header: { minHeight: 70, flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8 },
  headerButton: { width: 48, height: 48, borderWidth: 1, borderColor: ENTRY_BORDER, borderRadius: 12, backgroundColor: ENTRY_SURFACE, alignItems: "center", justifyContent: "center" },
  brand: { position: "absolute", left: 58, right: 94, alignItems: "center", justifyContent: "center" },
  brandText: { color: ENTRY_GREEN, marginTop: -3 },
  historyButton: { minHeight: 48, minWidth: 86, paddingHorizontal: 6, flexDirection: "row", alignItems: "center", justifyContent: "flex-end", gap: 6 },
  intro: { marginTop: 4, gap: 5 },
  eyebrow: { color: "#C87800", letterSpacing: 0.7, textTransform: "uppercase" },
  title: { color: ENTRY_GREEN, lineHeight: 40 },
  introMessage: { color: "#24372C", lineHeight: 23, maxWidth: 430 },
  primaryText: { color: ENTRY_TEXT },
  greenText: { color: ENTRY_GREEN },
  mutedText: { color: ENTRY_MUTED, lineHeight: 21 },
  flexCopy: { flex: 1, minWidth: 0 },
  scanCard: { minHeight: 256, borderRadius: 16, borderWidth: 1, borderColor: ENTRY_BORDER, backgroundColor: ENTRY_SURFACE, alignItems: "center", justifyContent: "center", overflow: "hidden" },
  leafStage: { flex: 1, width: "100%", minHeight: 180, alignItems: "center", justifyContent: "center" },
  lesion: { position: "absolute", width: 15, height: 15, borderRadius: 8, backgroundColor: "#D88A00", right: "39%", top: "43%", borderWidth: 3, borderColor: "#F4BF4F" },
  scanCorner: { position: "absolute", zIndex: 2, width: 28, height: 28, borderColor: ENTRY_GREEN },
  topLeft: { top: 14, left: 16, borderTopWidth: 2, borderLeftWidth: 2, borderTopLeftRadius: 8 },
  topRight: { top: 14, right: 16, borderTopWidth: 2, borderRightWidth: 2, borderTopRightRadius: 8 },
  bottomLeft: { bottom: 72, left: 16, borderBottomWidth: 2, borderLeftWidth: 2, borderBottomLeftRadius: 8 },
  bottomRight: { bottom: 72, right: 16, borderBottomWidth: 2, borderRightWidth: 2, borderBottomRightRadius: 8 },
  photoGuideRow: { width: "100%", minHeight: 66, borderTopWidth: 1, borderTopColor: "#E4DCCA", flexDirection: "row", alignItems: "center", justifyContent: "space-around", paddingVertical: 7 },
  photoGuideItem: { flex: 1, minWidth: 0, alignItems: "center", justifyContent: "center", gap: 3, paddingHorizontal: 4 },
  guideDivider: { width: 1, height: 40, backgroundColor: "#E4DCCA" },
  actionCard: { minHeight: 56, paddingHorizontal: 16, borderRadius: 9, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 15 },
  primaryAction: { borderWidth: 1, borderColor: "#C98B00", backgroundColor: "#F2B632" },
  primaryActionText: { color: ENTRY_TEXT },
  secondaryAction: { borderWidth: 1, borderColor: ENTRY_GREEN, backgroundColor: ENTRY_SURFACE },
  controlCard: { padding: 14, borderRadius: 12, borderWidth: 1, borderColor: "#E8C477", backgroundColor: "#FFF8E8", flexDirection: "row", alignItems: "flex-start", gap: 12 },
  controlIcon: { width: 44, height: 44, alignItems: "center", justifyContent: "center" },
  controlTitle: { color: "#8A5B00", marginBottom: 2 },
  controlCaution: { color: "#6E6250", lineHeight: 18, marginTop: 5 },
  tipCard: { minHeight: 58, paddingHorizontal: 14, paddingVertical: 10, borderRadius: 12, borderWidth: 1, borderColor: "#CFD8C5", backgroundColor: "#F0F4E9", flexDirection: "row", alignItems: "center", gap: 12 },
  disclaimer: { color: "#56645C", lineHeight: 18, paddingHorizontal: 12, marginTop: 2 },
  pressed: { opacity: 0.78 },
});
