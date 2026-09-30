import { Image } from "expo-image";
import { useRouter } from "expo-router";
import {
  ArrowLeft,
  Camera,
  Images,
  RotateCcw,
  Sprout,
  TriangleAlert,
} from "lucide-react-native";
import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ActivityIndicator,
  Alert,
  Pressable as AgPressable,
  FlatList,
  RefreshControl,
  StyleSheet,
  View,
} from "react-native";

import {
  AgButton,
  AgCard,
  AgEmptyState,
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";
import {
  captureFromCamera,
  checkImageQuality,
  pickFromGallery,
  QUALITY_ISSUE_KEY,
  type CaptureMethod,
  type PickedImage,
} from "@/features/disease";
import { useSelectedFarm } from "@/features/weather";
import { useAppTheme } from "@/hooks/useAppTheme";
import { useLanguage } from "@/hooks/useLanguage";
import { ApiError } from "@/types";

import { useChemicalPolicy } from "@/features/organic/chemicalPolicy";
import { GrowthBoostCard } from "../components/GrowthBoostCard";
import { GrowthCard } from "../components/GrowthCard";
import { GrowthComparison } from "../components/GrowthComparison";
import { ImageViewer } from "../components/ImageViewer";
import { TimelineItem } from "../components/TimelineItem";
import {
  useDeleteGrowthImage,
  useGrowthHistory,
  useGrowthTimeline,
  useUploadGrowth,
  useStageState,
} from "../hooks/useGrowth";
import type { GrowthImage, TimelineEntry } from "../types";

type View3 = "timeline" | "history" | "compare";
const VIEWS: View3[] = ["timeline", "history", "compare"];
const VIEW_KEY: Record<View3, string> = {
  timeline: "growth.tabTimeline",
  history: "growth.tabHistory",
  compare: "growth.tabCompare",
};

const GROWTH_COLORS = {
  background: "#FBF8F0",
  card: "#FFFFFF",
  ink: "#101713",
  body: "#26332B",
  muted: "#536158",
  primary: "#176B36",
  border: "#D7DDCF",
  pale: "#E8F3E5",
  action: "#58C95D",
  gold: "#B87517",
} as const;

export function GrowthMonitorScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const { language } = useLanguage();
  const farmQuery = useSelectedFarm();
  const { selected: farm } = farmQuery;
  const chemicalPolicy = useChemicalPolicy(farm?.id);
  const pickLock = useRef(false);
  const mutationLock = useRef(false);
  const refreshLock = useRef(false);
  const [picking, setPicking] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const [view, setView] = useState<View3>("timeline");
  const [picked, setPicked] = useState<PickedImage | null>(null);
  const [method, setMethod] = useState<CaptureMethod>("camera");
  const [issues, setIssues] = useState<string[]>([]);
  const [viewer, setViewer] = useState<{
    uri: string;
    caption?: string | null;
  } | null>(null);

  const timelineQuery = useGrowthTimeline(
    null,
    farm?.id ?? null,
    Boolean(farm),
  );
  const historyQuery = useGrowthHistory(null, farm?.id ?? null, Boolean(farm));
  const upload = useUploadGrowth();
  const del = useDeleteGrowthImage();

  const timeline = timelineQuery.data?.timeline ?? [];
  const latestWeek = timeline.length
    ? timeline[timeline.length - 1].weekNumber
    : null;
  const sessionId = timelineQuery.data?.session.id ?? null;
  const stageQuery = useStageState(farm?.id, sessionId);
  const images = useMemo(() => historyQuery.data ?? [], [historyQuery.data]);

  const sessionImages = useMemo(() => {
    const forSession = sessionId
      ? images.filter((i) => i.sessionId === sessionId)
      : images;
    return [...forSession].sort(
      (a, b) =>
        a.weekNumber - b.weekNumber || a.capturedAt.localeCompare(b.capturedAt),
    );
  }, [images, sessionId]);
  const latestAnalysis = useMemo(
    () =>
      [...sessionImages].reverse().find((image) => image.analysis)?.analysis ??
      null,
    [sessionImages],
  );

  const onPick = async (source: CaptureMethod) => {
    if (!farm || pickLock.current || mutationLock.current) return;
    pickLock.current = true;
    setPicking(true);
    try {
      const image =
        source === "camera"
          ? await captureFromCamera()
          : await pickFromGallery();
      if (!image) return;
      setMethod(source);
      setPicked(image);
      setIssues(checkImageQuality(image).issues);
      upload.reset();
    } catch {
      Alert.alert(t("common.somethingWrong"), t("growth.captureFailed"));
    } finally {
      pickLock.current = false;
      setPicking(false);
    }
  };

  const resetUpload = () => {
    setPicked(null);
    setIssues([]);
    upload.reset();
  };

  const onUpload = () => {
    if (
      !picked ||
      !farm ||
      issues.length ||
      mutationLock.current ||
      pickLock.current
    )
      return;
    mutationLock.current = true;
    upload.mutate(
      {
        imageBase64: picked.base64,
        mimeType: picked.mimeType,
        imageUri: picked.uri,
        farmId: farm.id,
        crop: farm.crop ?? null,
        language,
        captureMethod: method,
        latitude: farm.latitude,
        longitude: farm.longitude,
      },
      {
        onSuccess: () => {
          resetUpload();
          setView("timeline");
        },
        onSettled: () => {
          mutationLock.current = false;
        },
      },
    );
  };

  const onDelete = (image: GrowthImage) => {
    if (mutationLock.current || pickLock.current) return;
    mutationLock.current = true;
    del.mutate(image.id, {
      onError: () =>
        Alert.alert(t("common.somethingWrong"), t("growth.deleteFailed")),
      onSettled: () => {
        mutationLock.current = false;
      },
    });
  };
  const openViewer = (uri: string | null, caption?: string | null) => {
    if (uri) setViewer({ uri, caption });
  };

  const uploadError = upload.isError
    ? upload.error instanceof ApiError
      ? upload.error.errorCode === "ai_daily_quota_exceeded"
        ? t("growth.quotaExceeded")
        : upload.error.errorCode === "poor_image_quality"
          ? t("growth.poorQuality")
          : upload.error.errorCode === "no_plant_detected"
            ? t("growth.noPlant")
            : upload.error.errorCode === "storage_provider_unavailable"
              ? t("growth.storageUnavailable")
              : t("growth.uploadError")
      : t("growth.uploadError")
    : null;

  if (farmQuery.isLoading || farmQuery.isError) {
    return (
      <AgScreen backgroundColor={GROWTH_COLORS.background}>
        <Header onBack={() => router.back()} title={t("growth.title")} />
        {farmQuery.isLoading ? (
          <GrowthSkeleton />
        ) : (
          <GrowthErrorState
            onRetry={() => {
              void farmQuery.refetch();
            }}
          />
        )}
      </AgScreen>
    );
  }

  // --- No farm: prompt to register one (upload needs a farm). ---
  if (!farm) {
    return (
      <AgScreen backgroundColor={GROWTH_COLORS.background}>
        <Header onBack={() => router.back()} title={t("growth.title")} />
        <AgEmptyState
          light
          icon={Sprout}
          title={t("growth.noFarmTitle")}
          message={t("growth.noFarmMessage")}
          actionLabel={t("farm.addFarm")}
          onAction={() => router.push("/farm/new")}
        />
      </AgScreen>
    );
  }

  const refresh = async () => {
    if (refreshLock.current) return;
    refreshLock.current = true;
    setRefreshing(true);
    try {
      await Promise.allSettled([
        farmQuery.refetch(),
        timelineQuery.refetch(),
        historyQuery.refetch(),
        ...(sessionId ? [stageQuery.refetch()] : []),
      ]);
    } finally {
      refreshLock.current = false;
      setRefreshing(false);
    }
  };

  const timelineSessionNotFound =
    timelineQuery.error instanceof ApiError &&
    timelineQuery.error.status === 404 &&
    timelineQuery.error.errorCode === "growth_session_not_found";
  const loading =
    view === "history"
      ? historyQuery.isLoading
      : timelineQuery.isLoading ||
        (view === "compare" && historyQuery.isLoading);
  const errored =
    view === "history"
      ? historyQuery.isError
      : (timelineQuery.isError && !timelineSessionNotFound) ||
        (view === "compare" && historyQuery.isError);

  const busy = upload.isPending;
  const listData: (TimelineEntry | GrowthImage)[] =
    errored || loading || (view === "timeline" && timelineSessionNotFound)
      ? []
      : view === "timeline"
        ? timeline
        : view === "history"
          ? images
          : [];

  const header = (
    <View style={styles.headerContent}>
      <Header
        onBack={() => router.back()}
        title={t("growth.title")}
        subtitle={t("growth.subtitle")}
      />
      <View style={styles.farmContext}>
        <Sprout size={18} color={GROWTH_COLORS.primary} />
        <AgText
          variant="bodySmall"
          weight="semibold"
          style={styles.bodyText}
          numberOfLines={2}
        >
          {[farm.name, farm.crop].filter(Boolean).join(" · ")}
        </AgText>
      </View>
      <AgPressable
        onPress={() => router.push("/growth/stage" as never)}
        accessibilityRole="button"
        accessibilityLabel={t("growth.stageTracking.openWorkflow")}
        style={styles.stageCard}
      >
        <View style={styles.stageIcon}>
          <Sprout size={25} color={GROWTH_COLORS.primary} />
        </View>
        <View style={styles.stageCopy}>
          <AgText variant="body" weight="bold" style={styles.inkText}>
            {!stageQuery.isError && stageQuery.data?.confirmedStage
              ? [
                  t(`growth.stage.${stageQuery.data.confirmedStage}`),
                  latestWeek
                    ? t("growth.weekLabel", { count: latestWeek })
                    : null,
                ]
                  .filter(Boolean)
                  .join(" · ")
              : t("growth.stageTracking.title")}
          </AgText>
          <AgText variant="caption" style={styles.mutedText} numberOfLines={2}>
            {stageQuery.isError
              ? t("growth.loadErrorMessage")
              : stageQuery.isLoading
                ? t("common.loading")
                : stageQuery.data
                  ? t(`growth.stageTracking.${stageQuery.data.state}`)
                  : t("growth.stageTracking.notConfirmed")}
          </AgText>
        </View>
        <View style={styles.stageAction}>
          <AgText
            variant="caption"
            weight="semibold"
            style={styles.primaryText}
          >
            {t("growth.stageTracking.updateStage")}
          </AgText>
        </View>
      </AgPressable>
      {stageQuery.isError ? (
        <AgButton
          title={t("common.retry")}
          onPress={refresh}
          disabled={refreshing}
        />
      ) : null}

      {/* Upload area */}
      {picked ? (
        <AgCard style={styles.uploadCard}>
          <Image
            source={{ uri: picked.uri }}
            style={{ width: "100%", aspectRatio: 1, borderRadius: 14 }}
            contentFit="cover"
          />
          {issues.length ? (
            <View className="mt-3 rounded-card border border-warning/40 bg-warning/10 p-3">
              <View className="mb-1 flex-row items-center gap-2">
                <TriangleAlert size={16} color={colors.warning} />
                <AgText
                  variant="bodySmall"
                  weight="semibold"
                  style={styles.inkText}
                >
                  {t("growth.qualityTitle")}
                </AgText>
              </View>
              {issues.map((code) => (
                <AgText key={code} variant="caption" style={styles.mutedText}>
                  • {t(QUALITY_ISSUE_KEY[code] ?? "growth.qualityGeneric")}
                </AgText>
              ))}
            </View>
          ) : uploadError ? (
            <AgText
              variant="bodySmall"
              color="danger"
              className="mt-3"
              style={styles.errorText}
            >
              {uploadError}
            </AgText>
          ) : null}

          {busy ? (
            <View className="mt-4 flex-row items-center justify-center gap-2">
              <ActivityIndicator color={colors.primary} />
              <AgText variant="body" style={styles.mutedText}>
                {t("growth.analyzing")}
              </AgText>
            </View>
          ) : (
            <View className="mt-4 gap-2">
              {!issues.length ? (
                <AgButton title={t("growth.addPhoto")} onPress={onUpload} />
              ) : null}
              <AgButton
                title={t("growth.retake")}
                variant="ghost"
                onPress={resetUpload}
              />
            </View>
          )}
        </AgCard>
      ) : (
        <View style={styles.capturePanel}>
          <AgText variant="body" weight="bold" style={styles.inkText}>
            {t("growth.captureTitle")}
          </AgText>
          <View style={styles.capturePreview}>
            <Image
              source={require("../../../assets/images/growth-capture-field.png")}
              style={StyleSheet.absoluteFill}
              contentFit="cover"
              accessibilityLabel={t("growth.captureGuideAlt")}
            />
            <View style={[styles.guideCorner, styles.guideTopLeft]} />
            <View style={[styles.guideCorner, styles.guideTopRight]} />
            <View style={[styles.guideCorner, styles.guideBottomLeft]} />
            <View style={[styles.guideCorner, styles.guideBottomRight]} />
          </View>
          <AgPressable
            onPress={() => onPick("camera")}
            disabled={picking || del.isPending}
            accessibilityState={{
              disabled: picking || del.isPending,
              busy: picking,
            }}
            accessibilityRole="button"
            accessibilityLabel={t("growth.takeGrowthPhoto")}
            style={styles.primaryCaptureButton}
          >
            <Camera size={22} color={GROWTH_COLORS.ink} />
            <AgText variant="body" weight="bold" style={styles.inkText}>
              {t("growth.takeGrowthPhoto")}
            </AgText>
          </AgPressable>
          <AgPressable
            onPress={() => onPick("gallery")}
            disabled={picking || del.isPending}
            accessibilityState={{
              disabled: picking || del.isPending,
              busy: picking,
            }}
            accessibilityRole="button"
            accessibilityLabel={t("growth.chooseGallery")}
            style={styles.secondaryCaptureButton}
          >
            <Images size={21} color={GROWTH_COLORS.primary} />
            <AgText variant="body" weight="semibold" style={styles.primaryText}>
              {t("growth.chooseGallery")}
            </AgText>
          </AgPressable>
        </View>
      )}

      {latestAnalysis ? <GrowthBoostCard analysis={latestAnalysis} chemicalPolicy={chemicalPolicy} /> : null}

      <View style={styles.tabs} accessibilityRole="tablist">
        {VIEWS.map((v) => {
          const selected = view === v;
          return (
            <AgPressable
              key={v}
              onPress={() => setView(v)}
              accessibilityRole="tab"
              accessibilityState={{ selected }}
              style={[styles.tab, selected && styles.tabSelected]}
            >
              <AgText
                variant="bodySmall"
                weight="semibold"
                style={styles.tabText}
              >
                {t(VIEW_KEY[v])}
              </AgText>
            </AgPressable>
          );
        })}
      </View>

      {/* Compare view content lives in the header (list stays empty). */}
      {view === "compare" &&
      !loading &&
      !errored &&
      sessionImages.length >= 2 ? (
        <GrowthComparison
          first={sessionImages[0]}
          latest={sessionImages[sessionImages.length - 1]}
        />
      ) : null}
      {view !== "compare" ? (
        <View style={styles.sectionHeading}>
          <AgText variant="headingS" weight="bold" style={[styles.inkText, { flex: 1, minWidth: 0 }]}>
            {view === "timeline"
              ? t("growth.timelineHeading")
              : t("growth.historyHeading")}
          </AgText>
          <AgText variant="caption" style={styles.mutedText}>
            {t("growth.photoCount", { count: listData.length })}
          </AgText>
        </View>
      ) : null}
    </View>
  );

  return (
    <AgScreen padded={false} backgroundColor={GROWTH_COLORS.background}>
      <View style={styles.screenBody}>
        <FlatList
          data={listData}
          keyExtractor={(item) => item.id}
          ListHeaderComponent={header}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={
                refreshing ||
                timelineQuery.isRefetching ||
                historyQuery.isRefetching
              }
              onRefresh={refresh}
              tintColor={colors.primary}
            />
          }
          renderItem={({ item, index }) =>
            view === "timeline" ? (
              <TimelineItem
                entry={item as TimelineEntry}
                isLast={index === timeline.length - 1}
                onPressImage={(e) => openViewer(e.imageUrl, e.summary)}
              />
            ) : (
              <GrowthCard
                image={item as GrowthImage}
                onPress={(img) =>
                  openViewer(img.imageUrl, img.analysis?.growthSummaryTamil)
                }
                onDelete={onDelete}
                busy={del.isPending}
              />
            )
          }
          ListEmptyComponent={
            loading ? (
              <GrowthSkeleton />
            ) : errored ? (
              <GrowthErrorState onRetry={refresh} />
            ) : view === "compare" &&
              sessionImages.length >= 2 ? null : view === "compare" ? (
              <AgEmptyState
                light
                icon={Sprout}
                title={t("growth.compareEmptyTitle")}
                message={t("growth.compareEmptyMessage")}
              />
            ) : (
              <AgEmptyState
                light
                icon={Sprout}
                title={t("growth.emptyTitle")}
                message={t("growth.emptyMessage")}
              />
            )
          }
          ListFooterComponent={
            view !== "compare" && listData.length ? (
              <View style={styles.disclaimer}>
                <Sprout size={17} color={GROWTH_COLORS.primary} />
                <AgText variant="caption" style={styles.mutedText}>
                  {t("growth.observationDisclaimer")}
                </AgText>
              </View>
            ) : null
          }
        />
      </View>

      <ImageViewer
        uri={viewer?.uri ?? null}
        caption={viewer?.caption}
        visible={Boolean(viewer)}
        onClose={() => setViewer(null)}
      />
    </AgScreen>
  );
}

function Header({
  onBack,
  title,
  subtitle,
}: {
  onBack: () => void;
  title: string;
  subtitle?: string;
}) {
  const { t } = useTranslation();
  const { language, setLanguage } = useLanguage();
  return (
    <View style={styles.pageHeader}>
      <View style={styles.brandBar}>
        <AgPressable
          onPress={onBack}
          accessibilityRole="button"
          accessibilityLabel={t("common.back")}
          style={styles.backButton}
        >
          <ArrowLeft size={25} color={GROWTH_COLORS.ink} />
        </AgPressable>
        <View style={styles.brand} accessibilityLabel="AgrowNex">
          <Sprout size={27} color={GROWTH_COLORS.primary} />
          <AgText variant="headingS" weight="bold" style={styles.primaryText}>
            AgrowNex
          </AgText>
        </View>
        <AgPressable
          onPress={() => setLanguage(language === "en" ? "ta" : "en")}
          accessibilityRole="button"
          accessibilityLabel={t("profile.changeLanguage")}
          style={styles.languageButton}
        >
          <AgText variant="caption" weight="semibold" style={styles.inkText}>
            {language === "en" ? "தமிழ்" : "English"}
          </AgText>
        </AgPressable>
      </View>
      <View style={styles.headerCopy}>
        <AgText variant="label" weight="bold" style={styles.eyebrow}>
          {t("growth.journalEyebrow")}
        </AgText>
        <AgText variant="headingL" weight="bold" style={styles.inkText}>
          {title}
        </AgText>
        {subtitle ? (
          <AgText variant="body" style={styles.bodyText}>
            {subtitle}
          </AgText>
        ) : null}
      </View>
    </View>
  );
}

function GrowthErrorState({ onRetry }: { onRetry: () => void }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  return (
    <View style={styles.errorState}>
      <View style={[styles.errorIcon, { backgroundColor: colors.card }]}>
        <TriangleAlert size={58} color={colors.danger} />
      </View>
      <AgText variant="headingL" weight="bold" center style={styles.inkText}>
        {t("common.somethingWrong")}
      </AgText>
      <AgText variant="body" center style={styles.bodyText}>
        {t("growth.loadErrorMessage")}
      </AgText>
      <AgPressable
        onPress={onRetry}
        accessibilityRole="button"
        accessibilityLabel={t("common.retry")}
        style={[
          styles.retryButton,
          { backgroundColor: colors.card, borderColor: colors.border },
        ]}
      >
        <View style={styles.retryContent}>
          <RotateCcw size={25} color={colors.primary} />
          <AgText variant="headingS" weight="bold" style={styles.primaryText}>
            {t("common.retry")}
          </AgText>
        </View>
      </AgPressable>
    </View>
  );
}

function GrowthSkeleton() {
  return (
    <View style={{ marginTop: 8, gap: 12 }}>
      {[0, 1, 2].map((i) => (
        <AgSkeleton
          key={i}
          style={{
            height: 112,
            width: "100%",
            borderRadius: 12,
            backgroundColor: GROWTH_COLORS.border,
          }}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  screenBody: { flex: 1, paddingHorizontal: 20 },
  listContent: { gap: 12, paddingBottom: 40 },
  headerContent: { gap: 14, paddingBottom: 4 },
  pageHeader: { marginTop: 8, gap: 8 },
  brandBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
  },
  brand: { flexDirection: "row", alignItems: "center", gap: 6 },
  backButton: {
    width: 48,
    height: 48,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: GROWTH_COLORS.border,
    backgroundColor: GROWTH_COLORS.card,
    alignItems: "center",
    justifyContent: "center",
  },
  languageButton: {
    minWidth: 58,
    minHeight: 44,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: GROWTH_COLORS.border,
    backgroundColor: GROWTH_COLORS.card,
    paddingHorizontal: 10,
  },
  headerCopy: { gap: 2 },
  eyebrow: { color: GROWTH_COLORS.gold },
  inkText: { color: GROWTH_COLORS.ink },
  primaryText: { color: GROWTH_COLORS.primary },
  bodyText: { color: GROWTH_COLORS.body },
  mutedText: { color: GROWTH_COLORS.muted },
  errorText: { color: "#A52222" },
  farmContext: {
    minHeight: 44,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: GROWTH_COLORS.border,
    backgroundColor: GROWTH_COLORS.card,
  },
  stageCard: {
    minHeight: 72,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    padding: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: GROWTH_COLORS.border,
    backgroundColor: GROWTH_COLORS.card,
  },
  stageIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: GROWTH_COLORS.pale,
  },
  stageCopy: { minWidth: 0, flex: 1, gap: 2 },
  stageAction: {
    minHeight: 40,
    maxWidth: 105,
    justifyContent: "center",
    alignItems: "center",
    borderRadius: 9,
    borderWidth: 1,
    borderColor: GROWTH_COLORS.primary,
    paddingHorizontal: 9,
  },
  uploadCard: {
    backgroundColor: GROWTH_COLORS.card,
    borderColor: GROWTH_COLORS.border,
  },
  capturePanel: {
    gap: 9,
    borderWidth: 1,
    borderColor: GROWTH_COLORS.border,
    borderRadius: 12,
    backgroundColor: GROWTH_COLORS.card,
    padding: 10,
  },
  capturePreview: {
    width: "100%",
    aspectRatio: 2.7,
    overflow: "hidden",
    borderRadius: 10,
    backgroundColor: GROWTH_COLORS.pale,
  },
  guideCorner: {
    position: "absolute",
    width: 24,
    height: 24,
    borderColor: "#FFFFFF",
    borderWidth: 3,
  },
  guideTopLeft: {
    left: 12,
    top: 12,
    borderRightWidth: 0,
    borderBottomWidth: 0,
  },
  guideTopRight: {
    right: 12,
    top: 12,
    borderLeftWidth: 0,
    borderBottomWidth: 0,
  },
  guideBottomLeft: {
    left: 12,
    bottom: 12,
    borderRightWidth: 0,
    borderTopWidth: 0,
  },
  guideBottomRight: {
    right: 12,
    bottom: 12,
    borderLeftWidth: 0,
    borderTopWidth: 0,
  },
  primaryCaptureButton: {
    minHeight: 48,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 9,
    borderRadius: 9,
    borderWidth: 1,
    borderColor: GROWTH_COLORS.ink,
    backgroundColor: GROWTH_COLORS.action,
  },
  secondaryCaptureButton: {
    minHeight: 48,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 9,
    borderRadius: 9,
    borderWidth: 1,
    borderColor: GROWTH_COLORS.primary,
    backgroundColor: GROWTH_COLORS.card,
  },
  tabs: {
    flexDirection: "row",
    gap: 8,
    backgroundColor: GROWTH_COLORS.background,
  },
  tab: {
    minHeight: 46,
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 6,
    borderRadius: 9,
    borderWidth: 1,
    borderColor: GROWTH_COLORS.primary,
    backgroundColor: GROWTH_COLORS.card,
  },
  tabSelected: {
    borderWidth: 2,
    backgroundColor: GROWTH_COLORS.pale,
  },
  tabText: { color: GROWTH_COLORS.ink, textAlign: "center" },
  sectionHeading: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    paddingTop: 2,
  },
  disclaimer: {
    minHeight: 48,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 4,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: GROWTH_COLORS.pale,
  },
  errorState: {
    alignItems: "center",
    gap: 16,
    paddingTop: 54,
    paddingBottom: 28,
  },
  errorIcon: {
    width: 112,
    height: 112,
    borderRadius: 56,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 10,
  },
  retryButton: {
    width: "100%",
    minHeight: 56,
    borderRadius: 12,
    borderWidth: 1,
    justifyContent: "center",
    marginTop: 20,
  },
  retryContent: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 14,
  },
});
