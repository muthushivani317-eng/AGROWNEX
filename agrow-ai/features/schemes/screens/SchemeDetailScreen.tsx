import * as WebBrowser from "expo-web-browser";
import { useRouter } from "expo-router";
import {
  ArrowLeft,
  Bookmark,
  Building2,
  CalendarClock,
  CheckCircle2,
  Circle,
  CircleAlert,
  CircleHelp,
  ExternalLink,
  FileText,
  ListChecks,
  ShieldCheck,
  Gift,
  Leaf,
  MapPin,
  ArrowRight,
  Info,
} from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { Alert, RefreshControl, StyleSheet, View } from "react-native";
import Svg, { Circle as SvgCircle, Path } from "react-native-svg";
import { useRef, useState } from "react";

import {
  AgBadge,
  AgCard,
  AgErrorState,
  AgPressable,
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";
import { useSelectedFarm } from "@/features/weather";
import { splitSchemeBenefits } from "../utils/splitSchemeBenefits";

import { DocumentReadinessProgress } from "../components/DocumentReadinessProgress";
import {
  CATEGORY_LABEL_KEY,
  CRITERION_LABEL_KEY,
  STATUS_LABEL_KEY,
} from "../constants";
import {
  useAddBookmark,
  useRemoveBookmark,
  useSchemeDetail,
  useSchemeQuery,
} from "../hooks/useSchemes";
import type { Eligibility } from "../types";
import { deadlineInfo, isClosingSoon } from "../utils/format";

export function SchemeDetailScreen({ schemeId }: { schemeId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const colors = DETAIL_COLORS;
  const farms = useSelectedFarm();
  const { selected } = farms;
  const { query } = useSchemeQuery(selected);

  const {
    data: scheme,
    isLoading,
    isError,
    refetch,
  } = useSchemeDetail(schemeId, query);
  const addBookmark = useAddBookmark();
  const removeBookmark = useRemoveBookmark();
  const busy = addBookmark.isPending || removeBookmark.isPending;
  const lock = useRef(false);
  const refreshLock = useRef(false);
  const [refreshing, setRefreshing] = useState(false);
  const [showEligibility, setShowEligibility] = useState(false);
  const refresh = async () => {
    if (refreshLock.current) return;
    refreshLock.current = true;
    setRefreshing(true);
    try {
      await Promise.allSettled([farms.refetch(), refetch()]);
    } finally {
      refreshLock.current = false;
      setRefreshing(false);
    }
  };

  if (isLoading || farms.isLoading) {
    return (
      <AgScreen
        scroll
        backgroundColor={DETAIL_COLORS.bg}
        contentContainerStyle={styles.page}
      >
        <BackRow
          onBack={() => router.back()}
          label={t("schemes.detailTitle")}
        />
        <AgSkeleton
          style={{
            height: 240,
            borderRadius: 16,
            backgroundColor: colors.border,
          }}
        />
        <AgSkeleton style={styles.smallSkeleton} />
        <AgSkeleton style={styles.summarySkeleton} />
        <AgSkeleton style={styles.sectionSkeleton} />
        <AgSkeleton style={styles.sectionSkeleton} />
      </AgScreen>
    );
  }

  if (isError || farms.isError || !scheme) {
    return (
      <AgScreen
        scroll
        backgroundColor={DETAIL_COLORS.bg}
        contentContainerStyle={styles.page}
      >
        <BackRow
          onBack={() => router.back()}
          label={t("schemes.detailTitle")}
        />
        <AgErrorState light onRetry={refresh} />
      </AgScreen>
    );
  }

  const category = t(CATEGORY_LABEL_KEY[scheme.category], {
    defaultValue: scheme.category,
  });
  const deadline = deadlineInfo(scheme.lastDate);
  const closingSoon = isClosingSoon(scheme.lastDate);
  const deadlineLabel =
    deadline.key === "none"
      ? t("schemes.deadlineOpen")
      : deadline.key === "daysLeft"
        ? t("schemes.deadlineDaysLeft", { count: deadline.days })
        : t(`schemes.deadline_${deadline.key}`);

  const toggleBookmark = () => {
    if (lock.current) return;
    lock.current = true;
    (scheme.bookmarked ? removeBookmark : addBookmark).mutate(scheme.id, {
      onError: () =>
        Alert.alert(t("common.somethingWrong"), t("schemes.saveFailed")),
      onSettled: () => {
        lock.current = false;
      },
    });
  };

  const openOfficial = async () => {
    if (!scheme.officialUrl) return;
    try {
      await WebBrowser.openBrowserAsync(scheme.officialUrl);
    } catch {
      Alert.alert(t("common.somethingWrong"), t("common.retry"));
    }
  };

  return (
    <AgScreen
      scroll
      backgroundColor={DETAIL_COLORS.bg}
      contentContainerStyle={styles.page}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={refresh} />
      }
    >
      <BackRow
        onBack={() => router.back()}
        label={t("schemes.detailTitle")}
        right={
          <AgPressable
            onPress={toggleBookmark}
            disabled={busy}
            hitSlop={8}
            accessibilityRole="button"
            accessibilityState={{ selected: scheme.bookmarked, busy }}
            accessibilityLabel={
              scheme.bookmarked
                ? t("schemes.removeBookmark")
                : t("schemes.addBookmark")
            }
            style={styles.bookmarkButton}
          >
            <Bookmark
              size={22}
              color={scheme.bookmarked ? colors.primary : colors.textMuted}
              fill={scheme.bookmarked ? colors.primary : "transparent"}
            />
          </AgPressable>
        }
      />

      <View style={styles.hero}>
        <View style={styles.heroBadges}>
          <View style={styles.heroChip}>
            <Leaf size={16} color={colors.primary} />
            <AgText variant="bodySmall" color="inherit" style={styles.chipText}>
              {category}
            </AgText>
          </View>
          {scheme.state && scheme.state.toLowerCase() !== "all" ? (
            <View style={styles.heroChip}>
              <MapPin size={16} color={colors.primary} />
              <AgText
                variant="bodySmall"
                color="inherit"
                style={styles.chipText}
              >
                {scheme.state}
              </AgText>
            </View>
          ) : null}
          {scheme.status === "closed" ? (
            <AgBadge light label={t("schemes.statusClosed")} tone="danger" />
          ) : null}
        </View>

        <AgText
          variant="headingM"
          weight="bold"
          style={styles.heroTitle}
          color="inherit"
        >
          {scheme.title}
        </AgText>
        <AgText variant="body" style={styles.heroDescription} color="inherit">
          {scheme.description}
        </AgText>

        <View
          pointerEvents="none"
          accessibilityElementsHidden
          importantForAccessibility="no-hide-descendants"
        >
          <Svg width="100%" height={76} viewBox="0 0 360 90">
            <SvgCircle cx="305" cy="20" r="17" fill="#F7D896" />
            <Path
              d="M0 70 Q70 10 135 56 Q230 0 360 55 L360 90 H0Z"
              fill="#D2E8C9"
            />
            <Path d="M0 84 Q145 27 360 75 L360 90 H0Z" fill="#A9CF9C" />
            <Path
              d="M20 90 Q147 46 330 75 M90 90 Q176 57 350 79 M170 90 Q240 69 360 84"
              stroke="#ECF5DF"
              strokeWidth="5"
              fill="none"
            />
            <Path
              d="M58 73 V34 M46 41 Q58 18 72 40 M43 33 Q58 27 77 32"
              stroke="#85B77B"
              strokeWidth="5"
              strokeLinecap="round"
              fill="none"
            />
          </Svg>
        </View>
      </View>

      {/* Eligibility meter (docs: Scheme Detail → Eligibility Meter) */}
      {scheme.eligibility ? (
        <AgCard style={styles.sectionCard}>
          <View style={styles.sectionHeading}>
            <ShieldCheck size={16} color={colors.primary} />
            <AgText
              variant="headingS"
              weight="bold"
              color="inherit"
              style={styles.ringText}
            >
              {t("schemes.yourEligibility")}
            </AgText>
          </View>
          <EligibilityOverview eligibility={scheme.eligibility} />
          <CriteriaBreakdown eligibility={scheme.eligibility} />
          <AgPressable
            onPress={() => setShowEligibility((value) => !value)}
            style={styles.outlineAction}
            accessibilityRole="button"
            accessibilityState={{ expanded: showEligibility }}
          >
            <AgText weight="semibold" style={styles.linkText} color="inherit">
              {t("schemes.fullEligibility")}
            </AgText>
            <ArrowRight size={20} color={colors.primary} />
          </AgPressable>
          {showEligibility ? (
            <AgText style={styles.bodyText} color="inherit">
              {scheme.eligibilitySummary || t("schemes.eligibilityContext")}
            </AgText>
          ) : null}
        </AgCard>
      ) : null}

      {/* Benefits */}
      {scheme.benefits ? (
        <Section icon={Gift} title={t("schemes.benefits")}>
          <View style={styles.benefitGrid}>
            {splitSchemeBenefits(scheme.benefits).map((benefit, index) => (
              <View key={index} style={styles.benefitTile}>
                <Gift size={20} color={colors.primary} />
                <AgText style={styles.benefitText} color="inherit">
                  {benefit}
                </AgText>
              </View>
            ))}
          </View>
          <View style={styles.sourceNote}>
            <Info size={18} color={colors.textMuted} />
            <AgText variant="bodySmall" style={styles.noteText} color="inherit">
              {t("schemes.amountCaution")}
            </AgText>
          </View>
        </Section>
      ) : null}

      {/* Who is eligible (summary) */}
      {scheme.eligibilitySummary ? (
        <Section icon={CheckCircle2} title={t("schemes.eligibilitySummary")}>
          <AgText variant="body" color="inherit" style={styles.bodyText}>
            {scheme.eligibilitySummary}
          </AgText>
        </Section>
      ) : null}

      {/* Deadline */}
      <Section icon={CalendarClock} title={t("schemes.deadline")}>
        <AgText
          variant="body"
          weight={closingSoon ? "semibold" : "regular"}
          style={{ color: closingSoon ? colors.warning : colors.text }}
          color="inherit"
        >
          {deadlineLabel}
        </AgText>
      </Section>

      {/* Documents checklist (docs: Scheme Detail → Documents) */}
      {scheme.documents.length > 0 ? (
        <Section icon={FileText} title={t("schemes.documents")}>
          <View style={styles.documentList}>
            <DocumentReadinessProgress
              light
              ready={scheme.documentReadiness.readyCount}
              total={scheme.documentReadiness.totalCount}
            />
            {scheme.documents.map((doc, index) => (
              <View key={`${doc.name}-${index}`} style={styles.documentRow}>
                {doc.hasDocument ? (
                  <CheckCircle2
                    size={17}
                    color={colors.success}
                    style={styles.iconOffset}
                  />
                ) : (
                  <Circle
                    size={17}
                    color={colors.textMuted}
                    style={styles.iconOffset}
                  />
                )}
                <AgText variant="body" style={styles.detailCopy} color="inherit">
                  {doc.name}
                  {!doc.required ? ` ${t("schemes.optionalSuffix")}` : ""}
                </AgText>
              </View>
            ))}
          </View>
        </Section>
      ) : null}

      {/* Application steps (docs: Scheme Detail → Application Steps) */}
      {scheme.applicationSteps.length > 0 ? (
        <Section icon={ListChecks} title={t("schemes.applicationSteps")}>
          <View style={styles.stepList}>
            {scheme.applicationSteps.map((step, index) => (
              <View key={index} style={styles.stepRow}>
                <View style={styles.stepBadge}>
                  <AgText
                    variant="caption"
                    weight="bold"
                    color="inherit"
                    style={styles.bodyText}
                  >
                    {index + 1}
                  </AgText>
                </View>
                <AgText variant="body" style={styles.detailCopy} color="inherit">
                  {step}
                </AgText>
              </View>
            ))}
          </View>
        </Section>
      ) : null}

      {/* Department */}
      {scheme.departments.length > 0 ? (
        <Section icon={Building2} title={t("schemes.department")}>
          <AgText variant="body" color="inherit" style={styles.bodyText}>
            {scheme.departments.join(", ")}
          </AgText>
        </Section>
      ) : null}

      {scheme.officialUrl ? (
        <View style={styles.footer}>
          <AgPressable
            onPress={openOfficial}
            style={styles.applyAction}
            accessibilityRole="link"
          >
            <AgText weight="bold" style={styles.applyText} color="inherit">
              {t("schemes.applyOfficial")}
            </AgText>
            <ArrowRight size={22} color="#FFFFFF" />
          </AgPressable>
          <AgPressable
            onPress={openOfficial}
            style={styles.sourceAction}
            accessibilityRole="link"
          >
            <AgText weight="semibold" style={styles.linkText} color="inherit">
              {t("schemes.viewOfficialSource")}
            </AgText>
            <ExternalLink size={18} color={colors.primary} />
          </AgPressable>
        </View>
      ) : null}

      {/* Verified source footer (docs/PRODUCT_RULES.md rule 4). Always the
          localized "official" label, never the raw internal source slug
          (`scheme.source` is a backend-internal marker like "mock" or
          "curated_verified" -- rendering it directly leaked that string to
          farmers as "Verified source · curated_verified", found in the
          2026-08 pre-release audit follow-up). */}
      <View style={styles.sourceFooter}>
        <ShieldCheck size={13} color={colors.success} />
        <AgText variant="caption" color="inherit" style={styles.bodyText}>
          {t("schemes.verifiedSource", { source: t("schemes.officialSource") })}
        </AgText>
      </View>
    </AgScreen>
  );
}

/** Matched / to-confirm / unmet criteria breakdown — the engine, made transparent. */
function CriteriaBreakdown({ eligibility }: { eligibility: Eligibility }) {
  const { t } = useTranslation();
  const colors = DETAIL_COLORS;

  const row = (
    codes: string[],
    Icon: typeof CheckCircle2,
    color: string,
    labelKey: string,
  ) => {
    if (codes.length === 0) return null;
    const names = codes
      .map((c) => t(CRITERION_LABEL_KEY[c] ?? "", { defaultValue: c }))
      .join(", ");
    return (
      <View style={styles.criterionRow}>
        <Icon size={15} color={color} style={styles.iconOffset} />
        <AgText variant="bodySmall" style={styles.detailCopy} color="inherit">
          <AgText
            variant="bodySmall"
            weight="semibold"
            color="inherit"
            style={styles.bodyText}
          >
            {t(labelKey)}:{" "}
          </AgText>
          {names}
        </AgText>
      </View>
    );
  };

  return (
    <View style={styles.criteriaGroup}>
      {row(
        eligibility.matched,
        CheckCircle2,
        colors.success,
        "schemes.criteriaMatched",
      )}
      {row(
        eligibility.unknown,
        CircleHelp,
        colors.warning,
        "schemes.criteriaUnknown",
      )}
      {row(
        eligibility.unmet,
        CircleAlert,
        colors.danger,
        "schemes.criteriaUnmet",
      )}
    </View>
  );
}

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: typeof ShieldCheck;
  title: string;
  children: React.ReactNode;
}) {
  const colors = DETAIL_COLORS;
  return (
    <AgCard style={styles.sectionCard}>
      <View style={styles.sectionHeading}>
        <Icon size={16} color={colors.primary} />
        <AgText
          variant="headingS"
          weight="bold"
          color="inherit"
          style={styles.ringText}
        >
          {title}
        </AgText>
      </View>
      {children}
    </AgCard>
  );
}

function BackRow({
  onBack,
  label,
  right,
}: {
  onBack: () => void;
  label: string;
  right?: React.ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <View style={styles.header}>
      <AgPressable
        onPress={onBack}
        accessibilityRole="button"
        accessibilityLabel={t("common.back")}
        style={styles.iconButton}
      >
        <ArrowLeft size={24} color={DETAIL_COLORS.primary} />
      </AgPressable>
      <AgText
        variant="headingS"
        weight="bold"
        color="inherit"
        style={styles.headerTitle}
      >
        {label}
      </AgText>
      {right ?? <View style={styles.iconButton} />}
    </View>
  );
}

function EligibilityOverview({ eligibility }: { eligibility: Eligibility }) {
  const { t } = useTranslation();
  const pct = Number.isFinite(eligibility.score)
    ? Math.round(Math.max(0, Math.min(100, eligibility.score)))
    : 0;
  const ringColor =
    eligibility.status === "not_eligible"
      ? DETAIL_COLORS.danger
      : eligibility.status === "likely_eligible"
        ? DETAIL_COLORS.warning
        : DETAIL_COLORS.success;
  const circumference = 2 * Math.PI * 39;
  return (
    <View style={styles.eligibilityRow}>
      <View
        style={styles.ring}
        accessibilityRole="progressbar"
        accessibilityLabel={t("schemes.matchScore", { score: pct })}
        accessibilityValue={{ min: 0, max: 100, now: pct }}
      >
        <Svg width={96} height={96} viewBox="0 0 96 96">
          <SvgCircle
            cx="48"
            cy="48"
            r="39"
            stroke="#DDEFD7"
            strokeWidth="9"
            fill="none"
          />
          <SvgCircle
            cx="48"
            cy="48"
            r="39"
            stroke={ringColor}
            strokeWidth="9"
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={circumference * (1 - pct / 100)}
            strokeLinecap="round"
            rotation={-90}
            origin="48,48"
          />
        </Svg>
        <View style={styles.ringLabel}>
          <AgText
            variant="headingS"
            weight="bold"
            color="inherit"
            style={styles.ringText}
          >
            {pct}%
          </AgText>
        </View>
      </View>
      <View style={styles.eligibilityCopy}>
        <AgBadge
          light
          label={t(STATUS_LABEL_KEY[eligibility.status])}
          tone={
            eligibility.status === "eligible"
              ? "success"
              : eligibility.status === "not_eligible"
                ? "danger"
                : "warning"
          }
        />
        <AgText variant="bodySmall" color="inherit" style={styles.bodyText}>
          {t("schemes.eligibilityContext")}
        </AgText>
      </View>
    </View>
  );
}

const DETAIL_COLORS = {
  bg: "#FAF9F2",
  text: "#123D35",
  textMuted: "#4F605C",
  primary: "#176B3C",
  success: "#238546",
  warning: "#A66100",
  danger: "#AD3333",
  border: "#DFE5D9",
  onPrimary: "#FFFFFF",
};
const styles = StyleSheet.create({
  heroChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: "#DDEED5",
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 18,
    maxWidth: "100%",
  },
  chipText: { color: "#123D35", flexShrink: 1 },
  page: {
    paddingHorizontal: 16,
    paddingBottom: 32,
  },
  hero: {
    padding: 18,
    paddingBottom: 0,
    borderRadius: 22,
    backgroundColor: "#F0F7E9",
    borderWidth: 1,
    borderColor: "#DCE8D4",
    overflow: "hidden",
  },
  bodyText: {
    color: "#4F605C",
  },
  iconButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "#EAF3E4",
    alignItems: "center",
    justifyContent: "center",
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingVertical: 10,
    marginBottom: 8,
  },
  headerTitle: {
    flex: 1,
    textAlign: "center",
    color: "#123D35",
  },
  outlineAction: {
    marginTop: 12,
    minHeight: 48,
    borderWidth: 1,
    borderColor: "#176B3C",
    borderRadius: 14,
    padding: 10,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 10,
  },
  linkText: {
    color: "#176B3C",
    flexShrink: 1,
  },
  benefitGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  benefitTile: {
    flexBasis: 140,
    flexGrow: 1,
    minWidth: 0,
    padding: 12,
    borderRadius: 14,
    backgroundColor: "#F0F5ED",
    gap: 8,
  },
  benefitText: {
    fontSize: 14,
    lineHeight: 22,
    color: "#123D35",
  },
  sourceNote: {
    marginTop: 12,
    backgroundColor: "#EEF3F5",
    borderRadius: 12,
    padding: 12,
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
  },
  noteText: {
    flex: 1,
    color: "#4F605C",
  },
  footer: {
    marginTop: 18,
    gap: 8,
  },
  applyAction: {
    minHeight: 54,
    padding: 14,
    borderRadius: 16,
    backgroundColor: "#176B3C",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },
  applyText: {
    color: "#FFFFFF",
    flexShrink: 1,
  },
  sourceAction: {
    minHeight: 44,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  ring: {
    width: 96,
    height: 96,
  },
  ringLabel: {
    position: "absolute",
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    alignItems: "center",
    justifyContent: "center",
  },
  ringText: {
    color: "#123D35",
  },
  eligibilityRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    gap: 16,
  },
  eligibilityCopy: {
    flex: 1,
    minWidth: 150,
    gap: 8,
  },
  smallSkeleton: {
    height: 32,
    width: 160,
    borderRadius: 8,
  },
  summarySkeleton: {
    marginTop: 14,
    height: 96,
    width: "100%",
    borderRadius: 22,
  },
  sectionSkeleton: {
    marginTop: 14,
    height: 160,
    width: "100%",
    borderRadius: 22,
  },
  bookmarkButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "#EAF3E4",
    alignItems: "center",
    justifyContent: "center",
  },
  heroBadges: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    gap: 8,
    marginBottom: 10,
  },
  heroTitle: {
    marginTop: 8,
    color: "#123D35",
  },
  heroDescription: {
    marginTop: 6,
    color: "#4F605C",
  },
  sectionCard: {
    marginTop: 14,
    backgroundColor: "#FFFDF8",
    borderColor: "#DFE5D9",
    borderRadius: 22,
    padding: 16,
    gap: 12,
  },
  sectionHeading: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginBottom: 8,
  },
  documentList: {
    gap: 10,
  },
  documentRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
  },
  iconOffset: {
    marginTop: 2,
  },
  detailCopy: {
    flex: 1,
    minWidth: 0,
    color: "#4F605C",
  },
  stepList: {
    gap: 12,
  },
  stepRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
  },
  stepBadge: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: "#EAF3E4",
    alignItems: "center",
    justifyContent: "center",
  },
  sourceFooter: {
    marginTop: 14,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
  },
  criterionRow: {
    marginTop: 8,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingVertical: 8,
  },
  criteriaGroup: {
    marginTop: 10,
    borderTopWidth: 1,
    borderTopColor: "#DFE5D9",
    paddingTop: 8,
  },
  layout19: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  layout20: {
    height: 44,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
});
