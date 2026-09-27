import { Image } from "expo-image";
import { useLocalSearchParams, useRouter } from "expo-router";
import {
  ArrowLeft,
  Camera,
  CheckCircle2,
  History,
  Images,
  Leaf,
  Lightbulb,
  ScanLine,
  TriangleAlert,
} from "lucide-react-native";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ActivityIndicator,
  Alert,
  StyleSheet,
  TouchableOpacity,
  View,
} from "react-native";

import {
  AgButton,
  AgCard,
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";
import {
  captureFromCamera,
  checkImageQuality,
  pickFromGallery,
  type CaptureMethod,
  type PickedImage,
} from "@/features/disease";
import { useSelectedFarm } from "@/features/weather";
import { FarmSelector } from "@/features/weather/components/FarmSelector";
import { useAppTheme } from "@/hooks/useAppTheme";
import { useLanguage } from "@/hooks/useLanguage";
import { ApiError } from "@/types";

import { QUALITY_ISSUE_KEY } from "../constants";
import { useAnalyzeNutrient } from "../hooks/useNutrient";
import {
  nutrientCropMismatchMessage,
  cropLabel,
  nutrientErrorMessageKey,
} from "../services/nutrientErrorMessage";
import { NutrientError } from "../services/nutrientProvider";
import { useNutrientSync } from "../hooks/useNutrientSync";
import { NUTRIENT_SHADOW, NUTRIENT_UI } from "../design";

export function NutrientEntryState({
  onCamera,
  onGallery,
}: {
  onCamera: () => void;
  onGallery: () => void;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const tips = [
    t("nutrient.tipNaturalLight"),
    t("nutrient.tipWholeLeaf"),
    t("nutrient.tipFocus"),
  ];

  return (
    <View testID="nutrient-entry-state" style={styles.entry}>
      <View
        style={[
          styles.smartCard,
          {
            backgroundColor: NUTRIENT_UI.surface,
            borderColor: NUTRIENT_UI.border,
          },
        ]}
      >
        <View
          style={[styles.smartIcon, { backgroundColor: `${colors.primary}18` }]}
        >
          <ScanLine size={26} color={colors.primary} />
        </View>
        <View style={styles.flex}>
          <AgText variant="bodyLarge" weight="semibold" style={styles.accentText}>
            {t("nutrient.smartAnalysis")}
          </AgText>
          <AgText variant="bodySmall" style={[styles.smartCopy, styles.mutedText]}>
            {t("nutrient.subtitle")}
          </AgText>
        </View>
      </View>

      <View
        style={[
          styles.guidanceCard,
          {
            backgroundColor: NUTRIENT_UI.surface,
            borderColor: NUTRIENT_UI.border,
          },
        ]}
      >
        <View style={styles.guidanceHeading}>
          <View
            style={[
              styles.headingIcon,
              { backgroundColor: `${colors.primary}18` },
            ]}
          >
            <Leaf size={28} color={colors.primary} />
          </View>
          <AgText variant="headingS" weight="bold" style={[styles.flex, styles.primaryText]}>
            {t("nutrient.welcomeTitle")}
          </AgText>
        </View>
        <View
          style={[styles.accentLine, { backgroundColor: colors.primary }]}
        />
        <AgText variant="body" style={[styles.guidanceCopy, styles.mutedText]}>
          {t("nutrient.welcomeMessage")}
        </AgText>

        <View
          accessibilityElementsHidden
          style={[
            styles.scanVisual,
            {
              backgroundColor: `${colors.primary}0D`,
              borderColor: `${colors.primary}35`,
            },
          ]}
        >
          <View
            style={[styles.scanRing, { borderColor: `${colors.primary}55` }]}
          >
            <Leaf size={88} color={colors.primary} strokeWidth={1.25} />
          </View>
          <View
            style={[
              styles.scanBeam,
              { backgroundColor: `${colors.primary}80` },
            ]}
          />
        </View>

        <View
          style={[
            styles.tipsCard,
            { backgroundColor: NUTRIENT_UI.surfaceSoft, borderColor: NUTRIENT_UI.border },
          ]}
        >
          <View style={styles.tipsHeading}>
            <View
              style={[
                styles.tipIcon,
                { backgroundColor: `${colors.primary}18` },
              ]}
            >
              <Lightbulb size={20} color={colors.primary} />
            </View>
            <AgText variant="bodyLarge" weight="semibold" style={styles.primaryText}>
              {t("nutrient.tipsTitle")}
            </AgText>
          </View>
          {tips.map((tip) => (
            <View key={tip} style={styles.tipRow}>
              <CheckCircle2 size={20} color={colors.primary} />
              <AgText variant="bodySmall" style={[styles.flex, styles.mutedText]}>
                {tip}
              </AgText>
            </View>
          ))}
        </View>
      </View>

      <TouchableOpacity
        testID="nutrient-take-photo"
        accessibilityRole="button"
        accessibilityLabel={t("nutrient.takePhoto")}
        onPress={onCamera}
        activeOpacity={0.78}
        style={[
          styles.primaryAction,
          { backgroundColor: NUTRIENT_UI.chlorophyll },
        ]}
      >
        <Camera size={24} color={NUTRIENT_UI.white} />
        <AgText variant="bodyLarge" weight="bold" style={styles.actionText}>
          {t("nutrient.takePhoto")}
        </AgText>
      </TouchableOpacity>
      <TouchableOpacity
        testID="nutrient-choose-gallery"
        accessibilityRole="button"
        accessibilityLabel={t("nutrient.chooseGallery")}
        onPress={onGallery}
        activeOpacity={0.76}
        style={[
          styles.secondaryAction,
          {
            backgroundColor: NUTRIENT_UI.surface,
            borderColor: NUTRIENT_UI.border,
          },
        ]}
      >
        <Images size={24} color={NUTRIENT_UI.leaf} />
        <AgText variant="bodyLarge" weight="semibold" style={styles.primaryText}>
          {t("nutrient.chooseGallery")}
        </AgText>
      </TouchableOpacity>
    </View>
  );
}

/** Camera/gallery upload → nutrient-deficiency analysis (corroborated verdict). */
export function NutrientAnalysisScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const routeContext = useLocalSearchParams<{
    source?: string;
    crop?: string;
    symptoms?: string;
    growthStage?: string;
    imageReference?: string;
    imageReuseConsent?: string;
  }>();
  const { colors } = useAppTheme();
  const { language } = useLanguage();
  useNutrientSync();

  const {
    farms,
    selected,
    select,
    isLoading: farmsLoading,
  } = useSelectedFarm();
  const analyze = useAnalyzeNutrient();

  const [picked, setPicked] = useState<PickedImage | null>(null);
  const [method, setMethod] = useState<CaptureMethod>("camera");
  const [issues, setIssues] = useState<string[]>([]);

  const onPick = async (source: CaptureMethod) => {
    const image =
      source === "camera" ? await captureFromCamera() : await pickFromGallery();
    if (!image) return;
    setMethod(source);
    setPicked(image);
    setIssues(checkImageQuality(image).issues);
    analyze.reset();
  };

  const reset = () => {
    setPicked(null);
    setIssues([]);
    analyze.reset();
  };

  const onAnalyze = () => {
    if (!picked || !selected) return;
    analyze.mutate(
      {
        imageBase64: picked.base64,
        mimeType: picked.mimeType,
        imageUri: picked.uri,
        language,
        captureMethod: method,
        farmId: selected.id,
        crop: selected.crop ?? null,
        latitude: selected.latitude,
        longitude: selected.longitude,
      },
      {
        onSuccess: (result) => {
          reset();
          if (result.offline || !result.report) {
            Alert.alert(t("nutrient.queuedOffline"));
            return;
          }
          router.push(`/nutrient/${result.report.id}`);
        },
      },
    );
  };

  const errorCode =
    analyze.error instanceof ApiError
      ? analyze.error.errorCode
      : analyze.error instanceof NutrientError
        ? analyze.error.code
        : undefined;
  // A crop mismatch gets a specific message naming both crops when the
  // backend supplied them (e.g. "Your farm is registered for Paddy, not
  // Banana") -- falls back to the generic "doesn't match" copy for an
  // older backend response or a locally-queued offline error.
  const cropMismatchDetail =
    errorCode === "nutrient_crop_mismatch" && analyze.error instanceof ApiError
      ? nutrientCropMismatchMessage(t, analyze.error.details)
      : null;
  const backendError = analyze.error
    ? (cropMismatchDetail ?? t(nutrientErrorMessageKey(errorCode)))
    : null;

  return (
    <AgScreen
      scroll
      backgroundColor={NUTRIENT_UI.canvas}
      contentContainerStyle={styles.screenContent}
    >
      <View style={styles.topActions}>
        <TouchableOpacity
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={t("common.back")}
          activeOpacity={0.7}
          style={[
            styles.roundButton,
            { backgroundColor: NUTRIENT_UI.surface },
          ]}
        >
          <ArrowLeft size={25} color={NUTRIENT_UI.text} />
        </TouchableOpacity>
        <TouchableOpacity
          onPress={() => router.push("/nutrient/history")}
          accessibilityRole="button"
          accessibilityLabel={t("nutrient.viewHistory")}
          activeOpacity={0.7}
          style={[
            styles.roundButton,
            { backgroundColor: NUTRIENT_UI.surface },
          ]}
        >
          <History size={22} color={colors.primary} />
        </TouchableOpacity>
      </View>
      <View style={styles.titleRow}>
        <View style={styles.flex}>
          <AgText variant="headingXL" weight="bold" style={styles.primaryText}>
            {t("nutrient.title")}
          </AgText>
          <AgText variant="bodyLarge" style={[styles.subtitle, styles.mutedText]}>
            {t("nutrient.screenSubtitle")}
          </AgText>
        </View>
        <View style={[styles.titleIcon, { borderColor: colors.primary }]}>
          <Leaf size={32} color={colors.primary} />
        </View>
      </View>

      {routeContext.source === "disease_detection" ? (
        <AgCard style={styles.surfaceCard} className="mt-3 gap-1">
          <AgText variant="body" weight="semibold" style={styles.primaryText}>
            {language === "en"
              ? "Separate nutrient assessment"
              : "தனியான ஊட்டச்சத்து மதிப்பீடு"}
          </AgText>
          <AgText variant="bodySmall" style={styles.mutedText}>
            {language === "en"
              ? "The disease result is not reused as truth. Answer this check’s questions and select an image."
              : "நோய் முடிவு உண்மையாக மீண்டும் பயன்படுத்தப்படாது. இந்தப் பரிசோதனையின் கேள்விகளுக்குப் பதிலளித்து படத்தைத் தேர்ந்தெடுக்கவும்."}
          </AgText>
        </AgCard>
      ) : null}

      {farmsLoading ? (
        <View testID="nutrient-farms-loading" className="mt-3 gap-4">
          <AgSkeleton className="h-16 w-full rounded-card" />
          <AgSkeleton className="h-28 w-full rounded-card" />
          <AgSkeleton className="h-72 w-full rounded-card" />
        </View>
      ) : farms.length === 0 ? (
        <AgCard style={styles.surfaceCard} className="mt-8 items-center gap-2 py-8">
          <Leaf size={30} color={colors.primary} />
          <AgText variant="body" weight="semibold" style={styles.primaryText}>
            {t("nutrient.noFarmTitle")}
          </AgText>
          <AgButton
            light
            className="mt-2"
            title={t("home.actionAddFarm")}
            onPress={() => router.push("/farm/new")}
          />
        </AgCard>
      ) : (
        <>
          <View className="mt-3">
            <FarmSelector
              farms={farms}
              selectedId={selected?.id ?? null}
              onSelect={select}
              light
            />
            {selected?.crop ? (
              <AgText testID="nutrient-farm-crop" variant="caption" style={{ marginTop: 6, color: NUTRIENT_UI.muted }}>
                {t("nutrient.analysingCrop", { crop: cropLabel(t, selected.crop) })}
              </AgText>
            ) : null}
          </View>

          {!picked ? (
            <NutrientEntryState
              onCamera={() => void onPick("camera")}
              onGallery={() => void onPick("gallery")}
            />
          ) : (
            <View className="mt-4">
              <Image
                source={{ uri: picked.uri }}
                style={{ width: "100%", aspectRatio: 1, borderRadius: 16 }}
                contentFit="cover"
              />

              {issues.length ? (
                <AgCard style={styles.warningCard} className="mt-4">
                  <View className="mb-1 flex-row items-center gap-2">
                    <TriangleAlert size={18} color={colors.warning} />
                    <AgText variant="body" weight="semibold" style={styles.primaryText}>
                      {t("nutrient.qualityTitle")}
                    </AgText>
                  </View>
                  {issues.map((code) => (
                    <AgText key={code} variant="bodySmall" style={styles.mutedText}>
                      •{" "}
                      {t(QUALITY_ISSUE_KEY[code] ?? "nutrient.qualityGeneric")}
                    </AgText>
                  ))}
                  <AgText variant="caption" style={styles.mutedText} className="mt-2">
                    {t("nutrient.qualityHelp")}
                  </AgText>
                </AgCard>
              ) : backendError ? (
                <AgCard style={styles.errorCard} className="mt-4">
                  <AgText variant="bodySmall" style={styles.errorText}>
                    {backendError}
                  </AgText>
                </AgCard>
              ) : null}

              {analyze.isPending ? (
                <View className="mt-6 flex-row items-center justify-center gap-2">
                  <ActivityIndicator color={colors.primary} />
                  <AgText variant="body" style={styles.mutedText}>
                    {t("nutrient.analyzing")}
                  </AgText>
                </View>
              ) : (
                <>
                  {!issues.length ? (
                    <AgButton
                      light
                      title={t("nutrient.analyze")}
                      onPress={onAnalyze}
                      size="lg"
                      className="mt-6"
                      disabled={!selected}
                    />
                  ) : null}
                  <AgButton
                    light
                    title={t("nutrient.retake")}
                    variant="ghost"
                    onPress={reset}
                    className="mt-2"
                  />
                </>
              )}
            </View>
          )}
        </>
      )}
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  screenContent: { paddingTop: 8, paddingBottom: 48 },
  flex: { flex: 1, minWidth: 0 },
  topActions: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 20,
  },
  roundButton: {
    width: 50,
    height: 50,
    borderRadius: 25,
    alignItems: "center",
    justifyContent: "center",
    ...NUTRIENT_SHADOW,
  },
  titleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 16,
    marginBottom: 18,
  },
  subtitle: { marginTop: 5, lineHeight: 27 },
  titleIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    borderWidth: 2,
    alignItems: "center",
    justifyContent: "center",
  },
  entry: { width: "100%", gap: 14, marginTop: 10 },
  smartCard: {
    borderWidth: 1,
    borderRadius: 22,
    padding: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    ...NUTRIENT_SHADOW,
  },
  smartIcon: {
    width: 54,
    height: 54,
    borderRadius: 27,
    alignItems: "center",
    justifyContent: "center",
  },
  smartCopy: { marginTop: 3, lineHeight: 21 },
  guidanceCard: {
    borderWidth: 1,
    borderRadius: 26,
    padding: 18,
    ...NUTRIENT_SHADOW,
  },
  guidanceHeading: { flexDirection: "row", alignItems: "center", gap: 12 },
  headingIcon: {
    width: 52,
    height: 52,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
  },
  accentLine: {
    width: 64,
    height: 3,
    borderRadius: 2,
    marginLeft: 64,
    marginTop: 4,
  },
  guidanceCopy: { marginTop: 18, lineHeight: 25 },
  scanVisual: {
    height: 190,
    marginTop: 18,
    borderWidth: 1,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  scanRing: {
    width: 142,
    height: 142,
    borderRadius: 71,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    transform: [{ rotate: "-18deg" }],
  },
  scanBeam: { position: "absolute", left: 26, right: 26, top: 94, height: 2 },
  tipsCard: {
    marginTop: 18,
    borderWidth: 1,
    borderRadius: 20,
    padding: 16,
    gap: 12,
  },
  tipsHeading: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginBottom: 2,
  },
  tipIcon: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: "center",
    justifyContent: "center",
  },
  tipRow: { flexDirection: "row", alignItems: "flex-start", gap: 10 },
  primaryAction: {
    minHeight: 62,
    borderRadius: 20,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    paddingHorizontal: 18,
  },
  secondaryAction: {
    minHeight: 62,
    borderRadius: 20,
    borderWidth: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    paddingHorizontal: 18,
  },
  primaryText: { color: NUTRIENT_UI.text },
  mutedText: { color: NUTRIENT_UI.muted },
  accentText: { color: NUTRIENT_UI.leaf },
  actionText: { color: NUTRIENT_UI.white },
  surfaceCard: {
    backgroundColor: NUTRIENT_UI.surface,
    borderColor: NUTRIENT_UI.border,
  },
  warningCard: {
    backgroundColor: "#FFF8E7",
    borderColor: NUTRIENT_UI.amber,
  },
  errorCard: {
    backgroundColor: "#FBECE9",
    borderColor: NUTRIENT_UI.danger,
  },
  errorText: { color: NUTRIENT_UI.danger },
});
