import { Image } from "expo-image";
import { useRouter } from "expo-router";
import {
  ArrowLeft,
  Camera,
  ChevronRight,
  Images,
  Leaf,
  Trash2,
} from "lucide-react-native";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { ActivityIndicator, Pressable, StyleSheet, View } from "react-native";

import { AgCard, AgScreen, AgText } from "@/components/ui";
import { CropPhotoConfirmation } from "@/features/multiCropDiagnosis";
import { GuidedDiagnosisCard } from "@/features/multiCropDiagnosis/components/GuidedDiagnosisCard";
import { classifyCropDiagnosisFailure } from "@/features/multiCropDiagnosis/responseParser";
import { VerifiedDiseaseKnowledgeCard } from "@/features/multiCropDiagnosis/components/VerifiedDiseaseKnowledgeCard";
import {
  RecommendationResultCard,
  type DiseaseRecommendation,
} from "@/features/disease/components/RecommendationResultCard";
import { loadDiseaseRecommendation } from "@/features/disease/services/recommendationApi";
import type { CaptureMethod, PickedImage } from "@/features/disease/types";
import {
  captureFromCamera,
  pickFromGallery,
} from "@/features/disease/utils/pickDiseaseImage";
import { useAppTheme } from "@/hooks/useAppTheme";
import { useLanguage } from "@/hooks/useLanguage";
import { logger } from "@/lib/logger";

import { predictBanana, submitBananaFeedback } from "../bananaV3Api";
import { BananaFeedbackSheet } from "../components/BananaFeedbackSheet";
import { BananaPredictionResult } from "../components/BananaPredictionResult";
import { BananaUncertainResult } from "../components/BananaUncertainResult";
import { safeMessageKey } from "../responseMapping";
import { createSubmissionGuard } from "../submissionGuard";
import type { BananaFeedbackChoice, BananaPredictionResponse } from "../types";

export function bananaFailureMessageKey(error: unknown): string {
  const result = classifyCropDiagnosisFailure(error);
  return result.outcome === "blocked"
    ? `disease.errors.${result.status}`
    : "banana.error.runtime_failure";
}

const FARMER_READABLE_ERROR_KEYS = new Set([
  "banana.error.unreadable_image",
  "banana.error.invalid_image",
  "banana.error.crop_confirmation_required",
  "banana.error.runtime_failure",
]);

function farmerReadableResponseKey(response: BananaPredictionResponse): string {
  const key = safeMessageKey(response);
  return FARMER_READABLE_ERROR_KEYS.has(key)
    ? key
    : "banana.error.runtime_failure";
}

export function BananaDiseaseDetectionScreen({
  onChangeCrop,
  initialImage = null,
  cropConfirmationToken,
  suggestedCropId,
  suggestedCropName,
  identificationConfidence,
  farmId,
}: {
  onChangeCrop?: () => void;
  initialImage?: PickedImage | null;
  cropConfirmationToken: string | null;
  suggestedCropId?: string | null;
  suggestedCropName?: string | null;
  identificationConfidence?: number | null;
  farmId?: string;
}) {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const router = useRouter();
  const { colors } = useAppTheme();
  const [picked, setPicked] = useState<PickedImage | null>(initialImage);
  const [response, setResponse] = useState<BananaPredictionResponse | null>(
    null,
  );
  const [recommendation, setRecommendation] =
    useState<DiseaseRecommendation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [cropPhotoConfirmed, setCropPhotoConfirmed] = useState(
    Boolean(cropConfirmationToken),
  );
  const [freshPhotoRequired, setFreshPhotoRequired] = useState(false);
  const guard = useRef(createSubmissionGuard());
  const autoSubmittedToken = useRef<string | null>(null);
  const syncedInitialImage = useRef<PickedImage | null>(initialImage);

  useEffect(() => {
    if (initialImage === syncedInitialImage.current) return;
    syncedInitialImage.current = initialImage;
    if (initialImage) setPicked(initialImage);
  }, [initialImage]);

  const reset = () => {
    setPicked(null);
    setResponse(null);
    setRecommendation(null);
    setError(null);
    setCropPhotoConfirmed(false);
    autoSubmittedToken.current = null;
    setFreshPhotoRequired(false);
  };
  const startFreshWorkflow = () => {
    reset();
    onChangeCrop?.();
  };
  const pick = async (method: CaptureMethod) => {
    if (cropConfirmationToken || onChangeCrop) {
      startFreshWorkflow();
      return;
    }
    const image =
      method === "camera"
        ? await captureFromCamera({ base64: false })
        : await pickFromGallery({ base64: false });
    if (image) {
      setPicked(image);
      setResponse(null);
      setRecommendation(null);
      setError(null);
      setCropPhotoConfirmed(false);
      autoSubmittedToken.current = null;
      setFreshPhotoRequired(false);
    }
  };
  const analyze = useCallback(
    async (submission?: { image: PickedImage; token: string }) => {
      const image = submission?.image ?? picked;
      const token = submission?.token ?? cropConfirmationToken;
      if (!image) {
        setError("banana.error.invalid_image");
        return;
      }
      if (!cropPhotoConfirmed || !token) {
        setError("banana.error.crop_confirmation_required");
        return;
      }
      if (!guard.current.tryAcquire()) return;
      setSubmitting(true);
      setError(null);
      try {
        logger.info("banana.v3", "prediction_started", {
          token_present: true,
          image_present: true,
        });
        const result = await predictBanana(
          { uri: image.uri, mimeType: image.mimeType },
          token,
          farmId,
        );
        setResponse(result);
        if (result.status === "error") setFreshPhotoRequired(true);
        if (result.status === "accepted" && result.result.class_id) {
          const next = await loadDiseaseRecommendation(
            "banana",
            result.result.class_id,
          ).catch(() => null);
          setRecommendation(next);
        } else {
          setRecommendation(null);
        }
        if (__DEV__)
          logger.debug("banana.v3", "prediction_complete", {
            runtime: result.runtime_backend,
            processing_time_ms: result.processing_time_ms,
            model_version: result.model_version,
            decision_code: result.decision_code,
          });
      } catch (cause) {
        setError(bananaFailureMessageKey(cause));
        setCropPhotoConfirmed(false);
        setFreshPhotoRequired(true);
      } finally {
        guard.current.release();
        setSubmitting(false);
      }
    },
    [cropConfirmationToken, cropPhotoConfirmed, farmId, picked],
  );

  useEffect(() => {
    if (cropConfirmationToken) setCropPhotoConfirmed(true);
  }, [cropConfirmationToken]);

  useEffect(() => {
    const image = initialImage ?? picked;
    if (
      !image ||
      !cropPhotoConfirmed ||
      !cropConfirmationToken ||
      submitting ||
      autoSubmittedToken.current === cropConfirmationToken
    )
      return;

    autoSubmittedToken.current = cropConfirmationToken;
    void analyze({ image, token: cropConfirmationToken });
  }, [
    analyze,
    cropConfirmationToken,
    cropPhotoConfirmed,
    initialImage,
    picked,
    submitting,
  ]);
  const sendFeedback = async (choice: BananaFeedbackChoice, notes?: string) => {
    if (!response?.request_id) return;
    setFeedbackSubmitting(true);
    try {
      await submitBananaFeedback({
        prediction_request_id: response.request_id,
        farmer_selected_outcome: choice,
        notes,
        consent: true,
        source_context: "agrowai_mobile_app",
      });
      setFeedbackOpen(false);
    } catch {
      setError("banana.error.runtime_failure");
    } finally {
      setFeedbackSubmitting(false);
    }
  };

  return (
    <AgScreen scroll contentContainerStyle={styles.screenContent}>
      <View style={styles.header}>
        <Pressable
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={t("common.back")}
          style={({ pressed }) => [
            styles.backButton,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
              opacity: pressed ? 0.7 : 1,
            },
          ]}
        >
          <ArrowLeft size={24} color={colors.text} />
        </Pressable>
        <View style={styles.headerCopy}>
          <AgText variant="headingM" weight="bold">
            {t("banana.ui.title")}
          </AgText>
          <AgText variant="bodySmall" color="muted">
            {t("banana.ui.subtitle")}
          </AgText>
        </View>
        <View
          style={[styles.headerIcon, { borderColor: `${colors.primary}70` }]}
        >
          <Leaf size={24} color={colors.primaryLight} />
        </View>
      </View>

      <Pressable
        onPress={onChangeCrop}
        disabled={!onChangeCrop}
        accessibilityRole="button"
        accessibilityLabel={t("banana.ui.changeCrop")}
        style={({ pressed }) => [
          styles.cropCard,
          {
            backgroundColor: colors.card,
            borderColor: colors.border,
            opacity: pressed ? 0.72 : 1,
          },
        ]}
      >
        <Leaf size={25} color={colors.primaryLight} />
        <View style={styles.cropCopy}>
          <AgText variant="caption" color="muted">
            {t("disease.selectedCrop")}
          </AgText>
          <AgText variant="bodyLarge" weight="semibold">
            {t("banana.ui.banana")}
          </AgText>
        </View>
        {onChangeCrop ? (
          <View style={styles.changeCrop}>
            <AgText variant="bodySmall" weight="semibold" color="primary">
              {t("banana.ui.changeCrop")}
            </AgText>
            <ChevronRight size={18} color={colors.primaryLight} />
          </View>
        ) : null}
      </Pressable>

      {!picked ? (
        <View style={styles.photoActions}>
          <ActionButton
            label={t("disease.takePhoto")}
            icon={Camera}
            onPress={() => void pick("camera")}
            primary
          />
          <ActionButton
            label={t("disease.chooseGallery")}
            icon={Images}
            onPress={() => void pick("gallery")}
          />
          {error ? <AgText color="danger">{t(error)}</AgText> : null}
        </View>
      ) : (
        <View style={styles.content}>
          <View
            style={[
              styles.photoCard,
              { backgroundColor: colors.card, borderColor: colors.border },
            ]}
          >
            <View style={styles.cardHeading}>
              <Camera size={22} color={colors.primaryLight} />
              <AgText variant="bodyLarge" weight="semibold">
                {t("disease.capturedPhoto")}
              </AgText>
            </View>
            <Image
              source={{ uri: picked.uri }}
              style={styles.photo}
              contentFit="cover"
            />
            <View style={styles.replaceRow}>
              <ActionButton
                label={t("banana.ui.replacePhoto")}
                icon={Images}
                onPress={() => void pick("gallery")}
                compact
              />
              <ActionButton
                label={t("banana.ui.removePhoto")}
                icon={Trash2}
                onPress={startFreshWorkflow}
                destructive
                compact
              />
            </View>
          </View>

          <CropPhotoConfirmation
            cropId="banana"
            cropName={t("banana.ui.banana")}
            suggestedCropId={suggestedCropId}
            suggestedCropName={suggestedCropName}
            identificationConfidence={identificationConfidence}
            confirmed={cropPhotoConfirmed}
            onConfirm={() => {
              setCropPhotoConfirmed(true);
              setError(null);
            }}
            onChangeCrop={onChangeCrop}
            onRetake={startFreshWorkflow}
          />

          {error ? (
            <View
              style={[
                styles.errorCard,
                {
                  backgroundColor: `${colors.danger}12`,
                  borderColor: `${colors.danger}45`,
                },
              ]}
            >
              <AgText color="danger">{t(error)}</AgText>
              <ActionButton
                label={t("banana.ui.startFreshPhoto")}
                onPress={startFreshWorkflow}
              />
            </View>
          ) : null}

          {!response && !error && cropPhotoConfirmed && !freshPhotoRequired ? (
            <ActionButton
              label={t("disease.analyze")}
              onPress={() => void analyze()}
              primary
              disabled={submitting}
              loading={submitting}
            />
          ) : null}

          {response?.status === "accepted" ? (
            <>
              <BananaPredictionResult
                response={response}
                onRetake={startFreshWorkflow}
                onFeedback={() => setFeedbackOpen(true)}
              />
              <VerifiedDiseaseKnowledgeCard knowledge={null} />
              {recommendation ? (
                <RecommendationResultCard
                  recommendation={recommendation}
                  language={language === "en" ? "en" : "ta"}
                />
              ) : (
                <AgCard className="mt-3" style={{ borderColor: colors.border }}>
                  <AgText variant="bodySmall" color="muted">
                    {t("banana.ui.treatmentPendingVerification")}
                  </AgText>
                </AgCard>
              )}
            </>
          ) : response?.status === "uncertain" ? (
            <>
              <BananaUncertainResult onRetake={startFreshWorkflow} />
              <ActionButton
                label={t("banana.ui.checkNutrientSymptoms")}
                onPress={() =>
                  router.push({
                    pathname: "/nutrient",
                    params: { source: "disease_detection", crop: "banana" },
                  })
                }
              />
            </>
          ) : response?.status === "error" ? (
            <View
              style={[
                styles.errorCard,
                { backgroundColor: colors.card, borderColor: colors.border },
              ]}
            >
              <AgText color="danger">
                {t(farmerReadableResponseKey(response))}
              </AgText>
              <ActionButton
                label={t("banana.ui.startFreshPhoto")}
                onPress={startFreshWorkflow}
                primary
              />
            </View>
          ) : null}
          {(response?.status === "accepted" ||
            response?.status === "uncertain") &&
          picked ? (
            <GuidedDiagnosisCard
              crop="banana"
              primaryImage={picked}
              onExpertReview={() => router.push("/experts")}
            />
          ) : null}
        </View>
      )}
      <BananaFeedbackSheet
        visible={feedbackOpen}
        submitting={feedbackSubmitting}
        onClose={() => setFeedbackOpen(false)}
        onSubmit={(choice, notes) => void sendFeedback(choice, notes)}
      />
    </AgScreen>
  );
}

function ActionButton({
  label,
  icon: Icon,
  onPress,
  primary = false,
  destructive = false,
  compact = false,
  disabled = false,
  loading = false,
}: {
  label: string;
  icon?: typeof Camera;
  onPress: () => void;
  primary?: boolean;
  destructive?: boolean;
  compact?: boolean;
  disabled?: boolean;
  loading?: boolean;
}) {
  const { colors } = useAppTheme();
  const foreground = destructive
    ? colors.danger
    : primary
      ? colors.onPrimary
      : colors.text;
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled, busy: loading }}
      style={({ pressed }) => [
        styles.actionButton,
        compact && styles.compactButton,
        {
          backgroundColor: primary ? colors.primary : colors.surface,
          borderColor: destructive
            ? `${colors.danger}55`
            : primary
              ? colors.primary
              : colors.border,
          opacity: disabled ? 0.55 : pressed ? 0.75 : 1,
        },
      ]}
    >
      {loading ? (
        <ActivityIndicator size="small" color={foreground} />
      ) : Icon ? (
        <Icon size={19} color={foreground} />
      ) : null}
      <AgText
        variant="bodySmall"
        weight="semibold"
        style={{ color: foreground, textAlign: "center" }}
      >
        {label}
      </AgText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  screenContent: { paddingTop: 8, paddingBottom: 48 },
  header: { flexDirection: "row", alignItems: "flex-start", gap: 12 },
  backButton: {
    width: 46,
    height: 46,
    borderRadius: 23,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  headerCopy: { flex: 1, gap: 3 },
  headerIcon: {
    width: 46,
    height: 46,
    borderRadius: 23,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  cropCard: {
    minHeight: 82,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderWidth: 1,
    borderRadius: 20,
    padding: 16,
    marginTop: 20,
  },
  cropCopy: { flex: 1, gap: 1 },
  changeCrop: {
    flexDirection: "row",
    alignItems: "center",
    gap: 3,
    maxWidth: "42%",
  },
  photoActions: { gap: 12, marginTop: 22 },
  content: { gap: 0, marginTop: 16 },
  photoCard: { borderWidth: 1, borderRadius: 22, padding: 14, gap: 12 },
  cardHeading: { flexDirection: "row", alignItems: "center", gap: 9 },
  photo: { width: "100%", aspectRatio: 1.35, borderRadius: 16 },
  replaceRow: { flexDirection: "row", gap: 10 },
  actionButton: {
    minHeight: 52,
    flex: 1,
    borderWidth: 1,
    borderRadius: 16,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  compactButton: { minHeight: 48 },
  errorCard: {
    borderWidth: 1,
    borderRadius: 18,
    padding: 14,
    gap: 10,
    marginTop: 14,
  },
});
