import { Image } from "expo-image";
import {
  Camera,
  AlertCircle,
  ChevronRight,
  Images,
  Leaf,
  RefreshCw,
  ShieldAlert,
  TriangleAlert,
} from "lucide-react-native";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ActivityIndicator, Platform, Pressable, StyleSheet, View } from "react-native";

import { AgButton, AgCard, AgScreen, AgText } from "@/components/ui";
import {
  GROUNDNUT_SPEECH_RECORDING_OPTIONS,
  VoiceNoteRecorder,
} from "@/features/dailyFarmTask/components/VoiceNoteRecorder";
import type { CaptureMethod, PickedImage } from "@/features/disease/types";
import {
  captureFromCamera,
  pickFromGallery,
} from "@/features/disease/utils/pickDiseaseImage";
import { useAppTheme } from "@/hooks/useAppTheme";

import { GROUNDNUT_CLASS_INFORMATION } from "../diseaseInfo";
import {
  mapGroundnutError,
  mapGroundnutInputApiError,
  type GroundnutInputApiError,
  type GroundnutUiError,
} from "../errorMapping";
import {
  getGroundnutTextGuidance,
  mapGroundnutTranscript,
  predictGroundnut,
  submitGroundnutPestObservation,
  transcribeGroundnutSymptoms,
  validateGroundnutUpload,
} from "../groundnutApi";
import {
  GROUNDNUT_TEXT_SYMPTOMS,
  type GroundnutPredictionResponse,
  type GroundnutDamageExtent,
  type GroundnutSpreadSpeed,
  type GroundnutTextGuidanceResponse,
  type GroundnutTextSymptom,
  type GroundnutTranscriptMapResponse,
} from "../types";

const errorKey = (error: GroundnutUiError) => `groundnut.errors.${error}`;
const qualityKey = (reason: string) => `groundnut.qualityReasons.${reason}`;

// Farmer-reported observations only. This is not image-based severity estimation.
function GroundnutFieldUrgency({
  image,
  captureMethod,
}: {
  image: PickedImage;
  captureMethod: CaptureMethod;
}) {
  const { colors } = useAppTheme();
  const [extent, setExtent] = useState<GroundnutDamageExtent | null>(null);
  const [spread, setSpread] = useState<GroundnutSpreadSpeed>("unknown");
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState(false);
  const urgent = spread === "rapid" || extent === "widespread";
  const needsReview = extent === "several";

  const updateExtent = (value: GroundnutDamageExtent) => {
    setExtent(value);
    setSubmitted(false);
    setSubmitError(false);
  };
  const updateSpread = (value: GroundnutSpreadSpeed) => {
    setSpread(value);
    setSubmitted(false);
    setSubmitError(false);
  };
  const submit = async () => {
    if (!extent || !consent || submitting) return;
    setSubmitting(true);
    setSubmitError(false);
    try {
      await submitGroundnutPestObservation(image, {
        damageExtent: extent,
        spreadSpeed: spread,
        consent: true,
        captureMethod,
      });
      setSubmitted(true);
    } catch {
      setSubmitError(true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AgCard style={styles.cardGap} testID="groundnut-field-urgency">
      <View style={styles.row}>
        <AlertCircle size={20} color={colors.warning} />
        <AgText variant="headingS" weight="bold">Field severity check</AgText>
      </View>
      <AgText color="muted">
        Report what you see across the field, not just in this photo.
      </AgText>
      <AgText weight="semibold">How many plants look affected?</AgText>
      {([
        ["few", "Only a few plants"],
        ["several", "Several plants or patches"],
        ["widespread", "Many plants across the field"],
      ] as const).map(([value, label]) => (
        <AgButton
          key={value}
          title={`${extent === value ? "Selected: " : ""}${label}`}
          variant="outline"
          onPress={() => updateExtent(value)}
        />
      ))}
      <AgText weight="semibold">Is it spreading quickly?</AgText>
      {([
        ["unknown", "Not sure"],
        ["stable", "No rapid change noticed"],
        ["rapid", "Yes, spreading rapidly"],
      ] as const).map(([value, label]) => (
        <AgButton
          key={value}
          title={`${spread === value ? "Selected: " : ""}${label}`}
          variant="outline"
          onPress={() => updateSpread(value)}
        />
      ))}
      {extent !== null ? (
        <View style={styles.sectionGap} testID="groundnut-urgency-guidance">
          <AgText weight="bold" color={urgent ? "danger" : "muted"}>
            {urgent
              ? "Urgent: Contact a local agriculture expert promptly"
              : needsReview
                ? "Treat soon: Arrange a field assessment"
                : "Monitor: Check the field again soon"}
          </AgText>
          <AgText color="muted">
            {urgent
              ? "Rapid spread or widespread symptoms need prompt field assessment."
              : needsReview
                ? "Check affected patches and seek expert confirmation before treatment."
                : "Monitor nearby plants and photograph any changes."}
          </AgText>
          <AgText variant="caption" color="muted">
            Preliminary guidance based only on your answers. It does not
            measure affected area percentage or confirm a disease. Avoid
            pesticide decisions without local expert advice.
          </AgText>
        </View>
      ) : null}
      {extent !== null && !submitted ? (
        <View style={styles.sectionGap} testID="groundnut-pest-review-submit">
          <Pressable
            accessibilityRole="checkbox"
            accessibilityLabel="Consent to private photo expert review"
            accessibilityState={{ checked: consent }}
            onPress={() => setConsent((value) => !value)}
          >
            <AgText weight="semibold">
              {consent ? "Selected: " : ""}I consent to sending this photo and my field observations for private expert review.
            </AgText>
          </Pressable>
          <AgButton
            title={submitting ? "Submitting for review" : "Submit for expert review"}
            accessibilityLabel="Submit Groundnut pest observation for expert review"
            onPress={() => void submit()}
            disabled={!consent || submitting}
            loading={submitting}
          />
          {submitError ? (
            <AgText color="danger">The observation could not be submitted. Please try again.</AgText>
          ) : null}
        </View>
      ) : null}
      {submitted ? (
        <View style={styles.sectionGap} testID="groundnut-pest-review-pending">
          <AgText weight="bold">Submitted — pending expert review</AgText>
          <AgText color="muted">
            Your private photo and field observations were saved for review. No pest has been identified.
          </AgText>
        </View>
      ) : null}
    </AgCard>
  );
}


function percentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function GroundnutResult({ result }: { result: GroundnutPredictionResponse }) {
  const { colors } = useAppTheme();
  const { t } = useTranslation();
  const shownPrediction =
    result.status === "accepted"
      ? result.predicted_disease
      : result.candidate_prediction;
  const info = shownPrediction
    ? GROUNDNUT_CLASS_INFORMATION[shownPrediction.class_id]
    : null;

  return (
    <View style={styles.sectionGap} testID="groundnut-result">
      <AgCard style={styles.cardGap}>
        <View style={styles.row}>
          {result.status === "accepted" ? (
            <Leaf size={22} color={colors.primary} />
          ) : (
            <ShieldAlert size={22} color={colors.warning} />
          )}
          <AgText variant="headingS" weight="bold">
            {result.status === "accepted"
              ? t("groundnut.likelyClassification")
              : result.status === "review_required"
                ? t("groundnut.possibleClassification")
                : t("groundnut.photoRejected")}
          </AgText>
        </View>

        {shownPrediction ? (
          <>
            <AgText variant="headingM" weight="bold">
              {t(`groundnut.diseases.${shownPrediction.class_id}.name`, {
                defaultValue: shownPrediction.display_name,
              })}
            </AgText>
            <AgText weight="semibold">
              {t("groundnut.confidence")}:{" "}
              {percentage(shownPrediction.confidence)} ·{" "}
              {result.confidence_category}
            </AgText>
            <AgText color="muted">
              {t(
                `groundnut.confidenceCopy.${result.confidence_category ?? "LOW"}`,
              )}
            </AgText>
          </>
        ) : null}

        {result.rejection_reasons.map((reason) => (
          <AgText key={reason} color="muted">
            •{" "}
            {t(qualityKey(reason), {
              defaultValue: reason.replaceAll("_", " "),
            })}
          </AgText>
        ))}
      </AgCard>

      {result.top_three_predictions.length ? (
        <AgCard style={styles.cardGap}>
          <AgText variant="headingS" weight="bold">
            {t("groundnut.topThree")}
          </AgText>
          {result.top_three_predictions.map((prediction, index) => (
            <View key={prediction.class_id} style={styles.rankingRow}>
              <AgText weight="semibold">
                {index + 1}.{" "}
                {t(`groundnut.diseases.${prediction.class_id}.name`, {
                  defaultValue: prediction.display_name,
                })}
              </AgText>
              <AgText color="muted">{percentage(prediction.confidence)}</AgText>
            </View>
          ))}
        </AgCard>
      ) : null}

      <AgCard style={styles.cardGap}>
        <AgText variant="headingS" weight="bold">
          {t("groundnut.imageQuality")}
        </AgText>
        <AgText
          color={
            result.image_quality.status === "accepted" ? "success" : "danger"
          }
          weight="semibold"
        >
          {result.image_quality.status === "accepted"
            ? t("groundnut.accepted")
            : t("groundnut.rejected")}
        </AgText>
        {result.image_quality.reasons.map((reason) => (
          <AgText key={reason} color="muted">
            {t(qualityKey(reason), {
              defaultValue: reason.replaceAll("_", " "),
            })}
          </AgText>
        ))}
      </AgCard>

      {info ? (
        <AgCard style={styles.cardGap}>
          <AgText variant="headingS" weight="bold">
            {t("groundnut.about")}{" "}
            {t(`groundnut.diseases.${shownPrediction?.class_id}.name`, {
              defaultValue: info.title,
            })}
          </AgText>
          <AgText color="muted">
            {t(`groundnut.diseases.${shownPrediction?.class_id}.description`, {
              defaultValue: info.description,
            })}
          </AgText>
          <AgText variant="caption" color="muted">
            {t("groundnut.noTreatmentAdvice")}
          </AgText>
        </AgCard>
      ) : null}

      {result.expert_review_required ? (
        <AgCard style={styles.warningCard}>
          <ShieldAlert size={22} color={colors.warning} />
          <View style={styles.flex}>
            <AgText weight="bold">{t("groundnut.expertReviewTitle")}</AgText>
            <AgText color="muted">{t("groundnut.expertReviewBody")}</AgText>
          </View>
        </AgCard>
      ) : null}

      <AgText variant="caption" color="muted">
        {t("groundnut.model")}: {result.model_version}
      </AgText>
    </View>
  );
}

export function GroundnutDiseaseDetectionScreen({
  initialImage = null,
  onChangeCrop,
  onCheckGrowthStage,
}: {
  initialImage?: PickedImage | null;
  onChangeCrop?: () => void;
  onCheckGrowthStage?: () => void;
}) {
  const { colors } = useAppTheme();
  const { t, i18n } = useTranslation();
  const [picked, setPicked] = useState<PickedImage | null>(initialImage);
  const [result, setResult] = useState<GroundnutPredictionResponse | null>(
    null,
  );
  const [error, setError] = useState<GroundnutUiError | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [captureMethod, setCaptureMethod] = useState<CaptureMethod>("gallery");
  const [selectedSymptoms, setSelectedSymptoms] = useState<GroundnutTextSymptom[]>([]);
  const [symptomResult, setSymptomResult] = useState<GroundnutTextGuidanceResponse | null>(null);
  const [symptomSubmitting, setSymptomSubmitting] = useState(false);
  const [symptomError, setSymptomError] = useState<GroundnutInputApiError | null>(null);
  const [voiceTranscript, setVoiceTranscript] = useState<string | null>(null);
  const [voiceMapping, setVoiceMapping] = useState<GroundnutTranscriptMapResponse | null>(null);
  const [voiceConfirmed, setVoiceConfirmed] = useState(false);
  const [voiceError, setVoiceError] = useState<GroundnutInputApiError | null>(null);

  const speechLanguage =
    i18n.language === "ta" ? "ta-IN" : i18n.language === "ml" ? "ml-IN" : "en-IN";

  const processVoice = async (uri: string) => {
    setVoiceError(null);
    setVoiceTranscript(null);
    setVoiceMapping(null);
    setVoiceConfirmed(false);
    try {
      const transcribed = await transcribeGroundnutSymptoms(
        uri,
        Platform.OS === "web" ? "audio/webm" : "audio/amr",
        speechLanguage,
      );
      const mapped = await mapGroundnutTranscript(transcribed.transcript, speechLanguage);
      setVoiceTranscript(transcribed.transcript);
      setVoiceMapping(mapped);
    } catch (cause) {
      setVoiceError(mapGroundnutInputApiError(cause));
    }
  };

  const confirmVoiceSymptoms = () => {
    if (!voiceMapping) return;
    setSelectedSymptoms((current) =>
      [...new Set([...current, ...voiceMapping.matched_symptoms])].slice(0, 8),
    );
    setSymptomResult(null);
    setVoiceConfirmed(true);
  };

  const toggleSymptom = (symptom: GroundnutTextSymptom) => {
    setSelectedSymptoms((current) =>
      current.includes(symptom)
        ? current.filter((item) => item !== symptom)
        : current.length < 8
          ? [...current, symptom]
          : current,
    );
    setSymptomResult(null);
    setSymptomError(null);
  };

  const checkSymptoms = async () => {
    if (!selectedSymptoms.length || symptomSubmitting) return;
    setSymptomSubmitting(true);
    setSymptomError(null);
    setSymptomResult(null);
    try {
      setSymptomResult(await getGroundnutTextGuidance(selectedSymptoms));
    } catch (cause) {
      setSymptomError(mapGroundnutInputApiError(cause));
    } finally {
      setSymptomSubmitting(false);
    }
  };

  const pick = async (method: CaptureMethod) => {
    const image =
      method === "camera"
        ? await captureFromCamera({ base64: false })
        : await pickFromGallery({ base64: false });
    if (!image) return;
    const validationError = validateGroundnutUpload(image);
    if (validationError) {
      setError(validationError === "too_large" ? "too_large" : "invalid_type");
      setResult(null);
      return;
    }
    setPicked(image);
    setCaptureMethod(method);
    setResult(null);
    setError(null);
  };

  const analyze = async () => {
    if (!picked || submitting) return;
    const validationError = validateGroundnutUpload(picked);
    if (validationError) {
      setError(validationError === "too_large" ? "too_large" : "invalid_type");
      return;
    }
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      setResult(await predictGroundnut(picked));
    } catch (cause) {
      setError(mapGroundnutError(cause));
    } finally {
      setSubmitting(false);
    }
  };

  const clearImage = () => {
    setPicked(null);
    setResult(null);
    setError(null);
  };

  return (
    <AgScreen
      scroll
      contentContainerStyle={styles.screen}
      testID="groundnut-experimental-screen"
    >
      <View style={styles.header}>
        <View style={[styles.icon, { backgroundColor: `${colors.primary}18` }]}>
          <Leaf size={28} color={colors.primary} />
        </View>
        <View style={styles.flex}>
          <AgText variant="headingM" weight="bold">
            {t("groundnut.title")}
          </AgText>
          <AgText color="muted">{t("groundnut.subtitle")}</AgText>
        </View>
      </View>

      <Pressable
        onPress={onChangeCrop}
        disabled={!onChangeCrop}
        accessibilityRole="button"
        accessibilityLabel={t("groundnut.changeCrop")}
        style={[styles.cropRow, { borderColor: colors.border }]}
      >
        <Leaf size={22} color={colors.primary} />
        <View style={styles.flex}>
          <AgText variant="caption" color="muted">
            {t("groundnut.selectedCrop")}
          </AgText>
          <AgText weight="bold">{t("groundnut.cropName")}</AgText>
        </View>
        {onChangeCrop ? (
          <ChevronRight size={20} color={colors.textMuted} />
        ) : null}
      </Pressable>

      <AgCard style={styles.experimentalCard}>
        <TriangleAlert size={22} color={colors.warning} />
        <View style={styles.flex}>
          <AgText weight="bold">{t("groundnut.experimentalTitle")}</AgText>
          <AgText color="muted">{t("groundnut.experimentalBody")}</AgText>
        </View>
      </AgCard>

      <AgCard style={styles.cardGap} testID="groundnut-symptom-selector">
        <AgText variant="headingS" weight="bold">
          {t("groundnut.symptoms.title")}
        </AgText>
        <AgText color="muted">{t("groundnut.symptoms.subtitle")}</AgText>
        {GROUNDNUT_TEXT_SYMPTOMS.map((symptom) => {
          const selected = selectedSymptoms.includes(symptom);
          return (
            <Pressable
              key={symptom}
              accessibilityRole="checkbox"
              accessibilityState={{ checked: selected }}
              accessibilityLabel={t(`groundnut.symptoms.values.${symptom}`)}
              onPress={() => toggleSymptom(symptom)}
              style={[
                styles.symptomChoice,
                { borderColor: selected ? colors.primary : colors.border },
              ]}
            >
              <AgText weight={selected ? "bold" : "regular"}>
                {t(`groundnut.symptoms.values.${symptom}`)}
              </AgText>
            </Pressable>
          );
        })}
        <VoiceNoteRecorder
          onRecorded={processVoice}
          recordingOptions={GROUNDNUT_SPEECH_RECORDING_OPTIONS}
          labels={{
            title: t("groundnut.voice.title"),
            start: t("groundnut.voice.start"),
            stop: t("groundnut.voice.stop"),
            error: t("groundnut.voice.error"),
          }}
        />
        {voiceError ? (
          <AgText color="danger">{t(`groundnut.voice.apiErrors.${voiceError}`)}</AgText>
        ) : null}
        {voiceTranscript && voiceMapping ? (
          <View style={styles.sectionGap} testID="groundnut-voice-review">
            <AgText weight="bold">{t("groundnut.voice.transcript")}</AgText>
            <AgText>{voiceTranscript}</AgText>
            <AgText weight="bold">{t("groundnut.voice.suggestions")}</AgText>
            {voiceMapping.matched_symptoms.length ? (
              voiceMapping.matched_symptoms.map((symptom) => (
                <AgText key={symptom}>• {t(`groundnut.symptoms.values.${symptom}`)}</AgText>
              ))
            ) : (
              <AgText color="muted">{t("groundnut.voice.noSuggestions")}</AgText>
            )}
            {voiceMapping.unmatched_text.length ? (
              <View>
                <AgText weight="bold">{t("groundnut.voice.unmatched")}</AgText>
                {voiceMapping.unmatched_text.map((text) => <AgText key={text}>• {text}</AgText>)}
              </View>
            ) : null}
            {voiceMapping.ambiguous_text.length ? (
              <View>
                <AgText weight="bold">{t("groundnut.voice.ambiguous")}</AgText>
                {voiceMapping.ambiguous_text.map((text) => <AgText key={text}>• {text}</AgText>)}
              </View>
            ) : null}
            {voiceMapping.matched_symptoms.length ? (
              <AgButton
                title={
                  voiceConfirmed
                    ? t("groundnut.voice.confirmed")
                    : t("groundnut.voice.confirm")
                }
                accessibilityLabel={t("groundnut.voice.confirm")}
                variant="outline"
                disabled={voiceConfirmed}
                onPress={confirmVoiceSymptoms}
              />
            ) : null}
            <AgText color="muted">{t("groundnut.voice.reviewWarning")}</AgText>
          </View>
        ) : null}
        <AgButton
          title={
            symptomSubmitting
              ? t("groundnut.symptoms.checking")
              : t("groundnut.symptoms.check")
          }
          accessibilityLabel={t("groundnut.symptoms.check")}
          variant="outline"
          disabled={!selectedSymptoms.length || symptomSubmitting}
          loading={symptomSubmitting}
          onPress={() => void checkSymptoms()}
        />
        {symptomError ? (
          <AgText color="danger">{t(`groundnut.symptoms.apiErrors.${symptomError}`)}</AgText>
        ) : null}
        {symptomResult ? (
          <View style={styles.sectionGap} testID="groundnut-symptom-guidance">
            <AgText weight="bold">{t("groundnut.symptoms.preliminary")}</AgText>
            <AgText>{symptomResult.guidance}</AgText>
            <View style={styles.row}>
              <ShieldAlert size={20} color={colors.warning} />
              <AgText color="muted" style={styles.flex}>
                {t("groundnut.symptoms.expertReview")}
              </AgText>
            </View>
          </View>
        ) : null}
      </AgCard>

      {picked && onCheckGrowthStage ? (
        <AgButton
          title={t("groundnut.checkGrowthStage")}
          variant="outline"
          onPress={onCheckGrowthStage}
          accessibilityLabel={t("groundnut.checkGrowthStage")}
        />
      ) : null}

      {picked ? (
        <View style={styles.sectionGap}>
          <Image
            source={{ uri: picked.uri }}
            style={styles.preview}
            contentFit="cover"
            accessibilityLabel={t("groundnut.selectedImage")}
          />
          <AgButton
            title={t("groundnut.replaceImage")}
            variant="outline"
            leftIcon={<RefreshCw size={19} color={colors.primary} />}
            onPress={clearImage}
            disabled={submitting}
          />
        </View>
      ) : (
        <AgCard style={styles.cardGap}>
          <AgText variant="headingS" weight="bold">
            {t("groundnut.uploadTitle")}
          </AgText>
          <AgText color="muted">{t("groundnut.uploadRequirements")}</AgText>
          <AgButton
            title={t("groundnut.camera")}
            leftIcon={<Camera size={20} color={colors.onPrimary} />}
            onPress={() => void pick("camera")}
          />
          <AgButton
            title={t("groundnut.gallery")}
            variant="secondary"
            leftIcon={<Images size={20} color={colors.primary} />}
            onPress={() => void pick("gallery")}
          />
        </AgCard>
      )}

      {error ? (
        <AgCard style={styles.errorCard} testID="groundnut-error">
          <TriangleAlert size={21} color={colors.danger} />
          <View style={styles.flex}>
            <AgText weight="bold" color="danger">
              {t("groundnut.errorTitle")}
            </AgText>
            <AgText color="muted">{t(errorKey(error))}</AgText>
          </View>
        </AgCard>
      ) : null}

      {picked && !result ? (
        <AgButton
          title={submitting ? t("groundnut.analyzing") : t("groundnut.analyze")}
          onPress={() => void analyze()}
          disabled={submitting}
          loading={submitting}
          accessibilityLabel={t("groundnut.analyzeAccessibility")}
        />
      ) : null}

      {submitting ? (
        <View style={styles.processing} accessibilityRole="progressbar">
          <ActivityIndicator color={colors.primary} />
          <AgText color="muted">{t("groundnut.processing")}</AgText>
        </View>
      ) : null}

      {result ? <GroundnutResult result={result} /> : null}

      {result && picked && result.image_quality.status === "accepted" ? (
        <GroundnutFieldUrgency
          key={picked?.uri ?? "field"}
          image={picked}
          captureMethod={captureMethod}
        />
      ) : null}

      {result ? (
        <AgButton
          title={t("groundnut.retry")}
          variant="secondary"
          onPress={clearImage}
        />
      ) : null}
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  screen: { paddingBottom: 36, gap: 16 },
  header: { flexDirection: "row", alignItems: "center", gap: 12 },
  icon: {
    width: 52,
    height: 52,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
  },
  flex: { flex: 1 },
  row: { flexDirection: "row", alignItems: "center", gap: 9 },
  cropRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderWidth: 1,
    borderRadius: 16,
    padding: 14,
  },
  experimentalCard: { flexDirection: "row", gap: 12, alignItems: "flex-start" },
  warningCard: { flexDirection: "row", gap: 12, alignItems: "flex-start" },
  errorCard: { flexDirection: "row", gap: 12, alignItems: "flex-start" },
  cardGap: { gap: 10 },
  sectionGap: { gap: 12 },
  symptomChoice: { borderWidth: 1, borderRadius: 12, padding: 12 },
  preview: { width: "100%", aspectRatio: 1, borderRadius: 18 },
  rankingRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  processing: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    paddingVertical: 8,
  },
});
