import { useMemo, useState } from "react";
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
  BarChart3,
  Check,
  ClipboardCheck,
  Info,
  Leaf,
} from "lucide-react-native";
import { useTranslation } from "react-i18next";

import { AgErrorState, AgScreen, AgSkeleton, AgText } from "@/components/ui";
import { useLanguage } from "@/hooks/useLanguage";

import {
  useOrganicReadinessQuestions,
  useSubmitOrganicReadiness,
} from "../hooks/useOrganicReadiness";
import type {
  ReadinessQuestion,
  ReadinessResult,
} from "../services/organicReadinessApi";

const C = {
  bg: "#F7FAF3",
  card: "#FFFFFF",
  green: "#19813F",
  greenDark: "#0B3E30",
  greenSoft: "#EDF8EA",
  greenLine: "#B8DFAE",
  text: "#14263D",
  muted: "#677187",
  border: "#DDE6E0",
  orange: "#C46A18",
  orangeSoft: "#FFF0DA",
} as const;

const landscapeImage = require("../../../assets/images/organic-dashboard-landscape.png");
const QUESTION_ART = ["🌱", "🧴", "🪴", "💧", "🌾", "🧑‍🌾", "🌿", "🏪", "📜"];

function ReadinessHero({ onBack }: { onBack: () => void }) {
  const { t } = useTranslation();
  return (
    <View style={styles.hero}>
      <Image
        source={landscapeImage}
        contentFit="cover"
        style={styles.heroImage}
      />
      <View style={styles.heroWash} />
      <TouchableOpacity
        onPress={onBack}
        activeOpacity={0.75}
        accessibilityRole="button"
        accessibilityLabel={t("common.back")}
        style={styles.backButton}
      >
        <ArrowLeft size={27} color={C.greenDark} strokeWidth={2.5} />
      </TouchableOpacity>
      <AgText weight="bold" style={styles.heroTitle}>
        {t("organic.readinessTitle")}
      </AgText>
      <AgText style={styles.heroSubtitle}>{t("organic.readinessIntro")}</AgText>
    </View>
  );
}

function ReadinessResultHero({ onBack }: { onBack: () => void }) {
  const { t } = useTranslation();
  return (
    <View style={[styles.hero, styles.resultHero]}>
      <Image
        source={landscapeImage}
        contentFit="cover"
        style={styles.resultHeroImage}
      />
      <View style={styles.heroWash} />
      <TouchableOpacity
        onPress={onBack}
        activeOpacity={0.75}
        accessibilityRole="button"
        accessibilityLabel={t("common.back")}
        style={styles.backButton}
      >
        <ArrowLeft size={27} color={C.greenDark} strokeWidth={2.5} />
      </TouchableOpacity>
      <AgText weight="bold" style={styles.heroTitle}>
        {t("organic.readinessResultTitle")}
      </AgText>
      <AgText style={styles.heroSubtitle}>
        {t("organic.readinessResultSubtitle")}
      </AgText>
    </View>
  );
}

function ProgressSummary({
  answered,
  total,
}: {
  answered: number;
  total: number;
}) {
  const completion = total ? Math.round((answered / total) * 100) : 0;
  return (
    <View
      style={styles.progressSection}
      accessibilityRole="progressbar"
      accessibilityValue={{ min: 0, max: total, now: answered }}
    >
      <View style={styles.progressMeta}>
        <AgText weight="semibold" style={styles.progressCount}>
          {answered} / {total}
        </AgText>
        <View style={styles.progressPill}>
          <AgText weight="semibold" style={styles.progressPercent}>
            {completion}%
          </AgText>
        </View>
      </View>
      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { width: `${completion}%` }]} />
      </View>
    </View>
  );
}

function QuestionCard({
  question,
  index,
  selectedKey,
  onSelect,
  pick,
}: {
  question: ReadinessQuestion;
  index: number;
  selectedKey?: string;
  onSelect: (key: string) => void;
  pick: (ta: string, en?: string | null) => string;
}) {
  const options = Object.entries(question.options);
  return (
    <View style={styles.questionCard}>
      <View style={styles.questionHeading}>
        <View style={styles.questionNumber}>
          <AgText weight="bold" style={styles.questionNumberText}>
            {index + 1}
          </AgText>
        </View>
        <AgText style={styles.questionEmoji}>
          {QUESTION_ART[index % QUESTION_ART.length]}
        </AgText>
        <AgText weight="semibold" style={styles.questionTitle}>
          {pick(question.title_ta, question.title_en)}
        </AgText>
      </View>

      <View style={styles.optionsRow} accessibilityRole="radiogroup">
        {options.map(([key, option]) => {
          const selected = selectedKey === key;
          const label = pick(option.label_ta ?? key, option.label_en);
          return (
            <Pressable
              key={key}
              onPress={() => onSelect(key)}
              accessibilityRole="radio"
              accessibilityState={{ checked: selected }}
              accessibilityLabel={label}
              style={[styles.option, selected && styles.selectedOption]}
            >
              <View style={[styles.radio, selected && styles.radioSelected]}>
                {selected ? <View style={styles.radioDot} /> : null}
              </View>
              <AgText style={styles.optionLabel}>{label}</AgText>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

function PrimaryButton({
  title,
  onPress,
  disabled,
  loading,
}: {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
}) {
  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.82}
      disabled={disabled || loading}
      accessibilityRole="button"
      accessibilityState={{ disabled: disabled || loading }}
      style={[styles.primaryButton, (disabled || loading) && styles.disabled]}
    >
      {loading ? (
        <ActivityIndicator color="#FFFFFF" />
      ) : (
        <>
          <AgText weight="bold" style={styles.primaryButtonText}>
            {title}
          </AgText>
          <ArrowRight size={25} color="#FFFFFF" strokeWidth={2.5} />
        </>
      )}
    </TouchableOpacity>
  );
}

/** Server-driven organic readiness assessment; no questions or scoring are invented locally. */
export function OrganicReadinessScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const { language } = useLanguage();
  const pick = (ta: string, en?: string | null) =>
    language === "ta" ? ta : (en ?? ta);
  const questionsQuery = useOrganicReadinessQuestions();
  const submit = useSubmitOrganicReadiness(farmId);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<ReadinessResult | null>(null);
  const questions = questionsQuery.data?.questions ?? [];
  const answeredCount = questions.filter(
    (question) => answers[question.id],
  ).length;
  const allAnswered = useMemo(
    () =>
      questions.length > 0 &&
      questions.every((question) => answers[question.id]),
    [questions, answers],
  );

  if (questionsQuery.isLoading) {
    return (
      <AgScreen
        scroll
        padded={false}
        backgroundColor={C.bg}
        contentContainerStyle={styles.screen}
      >
        <ReadinessHero onBack={() => router.back()} />
        <View style={styles.content}>
          <AgSkeleton style={styles.progressSkeleton} />
          <AgSkeleton style={styles.questionSkeleton} />
          <AgSkeleton style={styles.questionSkeleton} />
        </View>
      </AgScreen>
    );
  }

  if (questionsQuery.isError) {
    return (
      <AgScreen
        scroll
        padded={false}
        backgroundColor={C.bg}
        contentContainerStyle={styles.screen}
      >
        <ReadinessHero onBack={() => router.back()} />
        <View style={[styles.stateCard, styles.contentCard]}>
          <AgErrorState
            light
            message={t("organic.readinessLoadError")}
            onRetry={() => void questionsQuery.refetch()}
          />
        </View>
      </AgScreen>
    );
  }

  if (questions.length === 0) {
    return (
      <AgScreen
        scroll
        padded={false}
        backgroundColor={C.bg}
        contentContainerStyle={styles.screen}
      >
        <ReadinessHero onBack={() => router.back()} />
        <View style={[styles.stateCard, styles.emptyCard]}>
          <View style={styles.emptyIcon}>
            <ClipboardCheck size={42} color={C.green} strokeWidth={1.9} />
          </View>
          <AgText weight="bold" style={styles.emptyTitle}>
            {t("organic.readinessNotSetUpTitle")}
          </AgText>
          <AgText style={styles.emptyMessage}>
            {t("organic.readinessNotSetUpMessage")}
          </AgText>
        </View>
      </AgScreen>
    );
  }

  if (result) {
    return (
      <AgScreen
        scroll
        padded={false}
        backgroundColor={C.bg}
        contentContainerStyle={styles.screen}
      >
        <ReadinessResultHero onBack={() => router.back()} />
        <View style={styles.content}>
          <View style={[styles.stateCard, styles.resultCard]}>
            <View style={styles.resultScoreRow}>
              <View style={styles.scoreSummary}>
                <View style={styles.scoreLabelRow}>
                  <View style={styles.scoreLeafIcon}>
                    <Leaf
                      size={27}
                      color={C.green}
                      fill="#6DBB51"
                      strokeWidth={1.7}
                    />
                  </View>
                  <AgText weight="semibold" style={styles.scoreLabel}>
                    {t("organic.readinessScoreHeading")}
                  </AgText>
                </View>
                <View style={styles.scoreNumberRow}>
                  <AgText weight="bold" style={styles.scoreValue}>
                    {result.score}
                  </AgText>
                  <AgText style={styles.scoreUnit}>/100</AgText>
                </View>
              </View>
              <View
                style={styles.scoreRing}
                accessibilityRole="progressbar"
                accessibilityValue={{ min: 0, max: 100, now: result.score }}
              >
                <View style={styles.scoreRingInner}>
                  <AgText weight="bold" style={styles.scorePercent}>
                    {result.score}%
                  </AgText>
                </View>
              </View>
            </View>

            <View style={styles.recommendationPanel}>
              <View style={styles.recommendationRow}>
                <View style={styles.recommendationIcon}>
                  <Leaf
                    size={25}
                    color={C.green}
                    fill="#74BE54"
                    strokeWidth={1.7}
                  />
                </View>
                <AgText weight="bold" style={styles.recommendation}>
                  {pick(result.recommendation_ta, result.recommendation_en)}
                </AgText>
              </View>
              {result.risk_flags.map((flag) => (
                <View key={flag} style={styles.factorPill}>
                  <View style={styles.factorIcon}>
                    <BarChart3 size={19} color="#FFFFFF" strokeWidth={2.5} />
                  </View>
                  <AgText style={styles.factorText}>
                    {t("organic.readinessKeyFactor", { factor: flag })}
                  </AgText>
                </View>
              ))}
            </View>
          </View>
          <View style={styles.noticeCard}>
            <View style={styles.noticeIcon}>
              <Info size={24} color="#FFFFFF" strokeWidth={2.5} />
            </View>
            <AgText style={styles.noticeText}>
              {result.certification_notice}
            </AgText>
          </View>
          <PrimaryButton
            title={t("common.done")}
            onPress={() => router.back()}
          />
          <TouchableOpacity
            onPress={() => {
              setResult(null);
              setAnswers({});
            }}
            activeOpacity={0.8}
            accessibilityRole="button"
            style={styles.retakeButton}
          >
            <AgText weight="semibold" style={styles.retakeText}>
              {t("organic.readinessRetake")}
            </AgText>
          </TouchableOpacity>
          <Image
            source={landscapeImage}
            contentFit="cover"
            style={styles.footerLandscape}
          />
        </View>
      </AgScreen>
    );
  }

  return (
    <AgScreen
      scroll
      padded={false}
      backgroundColor={C.bg}
      contentContainerStyle={styles.screen}
    >
      <ReadinessHero onBack={() => router.back()} />
      <View style={styles.content}>
        <ProgressSummary answered={answeredCount} total={questions.length} />
        <View style={styles.questions}>
          {questions.map((question, index) => (
            <QuestionCard
              key={question.id}
              question={question}
              index={index}
              selectedKey={answers[question.id]}
              onSelect={(key) =>
                setAnswers((current) => ({ ...current, [question.id]: key }))
              }
              pick={pick}
            />
          ))}
        </View>

        {submit.isError ? (
          <View style={styles.submitError}>
            <AgErrorState light message={t("organic.readinessSubmitError")} />
          </View>
        ) : null}

        <PrimaryButton
          title={t("organic.readinessSubmit")}
          disabled={!allAnswered}
          loading={submit.isPending}
          onPress={() =>
            submit.mutate(answers, { onSuccess: (data) => setResult(data) })
          }
        />
        <Image
          source={landscapeImage}
          contentFit="cover"
          style={styles.footerLandscape}
        />
      </View>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  screen: { paddingBottom: 0 },
  hero: {
    minHeight: 242,
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 24,
    overflow: "hidden",
  },
  heroImage: {
    position: "absolute",
    top: 0,
    right: 0,
    width: "67%",
    height: "100%",
    opacity: 0.84,
  },
  resultHero: { minHeight: 285 },
  resultHeroImage: {
    position: "absolute",
    top: 20,
    right: 0,
    width: "66%",
    height: "88%",
    opacity: 0.9,
  },
  heroWash: {
    position: "absolute",
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    backgroundColor: "rgba(249,252,247,0.58)",
  },
  backButton: {
    width: 50,
    height: 50,
    borderRadius: 25,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(233,246,229,0.95)",
  },
  heroTitle: {
    maxWidth: 520,
    marginTop: 18,
    color: C.greenDark,
    fontSize: 33,
    lineHeight: 40,
    letterSpacing: -0.7,
  },
  heroSubtitle: {
    maxWidth: 430,
    marginTop: 7,
    color: C.muted,
    fontSize: 16,
    lineHeight: 23,
  },
  content: { marginTop: -20, paddingHorizontal: 14, paddingBottom: 0 },
  progressSection: {
    borderRadius: 20,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: "#FFFFFF",
    padding: 15,
    shadowColor: "#244A32",
    shadowOpacity: 0.07,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 5 },
    elevation: 2,
  },
  progressMeta: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  progressCount: { color: C.green, fontSize: 15, lineHeight: 20 },
  progressPill: {
    borderRadius: 999,
    paddingHorizontal: 15,
    paddingVertical: 7,
    backgroundColor: C.orangeSoft,
  },
  progressPercent: { color: C.orange, fontSize: 14, lineHeight: 18 },
  progressTrack: {
    height: 8,
    marginTop: 12,
    borderRadius: 4,
    overflow: "hidden",
    backgroundColor: "#E4E8E6",
  },
  progressFill: { height: "100%", borderRadius: 4, backgroundColor: "#4EA943" },
  questions: { marginTop: 14, gap: 12 },
  questionCard: {
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#E5EBE7",
    backgroundColor: "#FFFFFF",
    padding: 13,
    shadowColor: "#284C36",
    shadowOpacity: 0.055,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 5 },
    elevation: 2,
  },
  questionHeading: {
    minHeight: 58,
    flexDirection: "row",
    alignItems: "center",
  },
  questionNumber: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: C.greenSoft,
  },
  questionNumberText: { color: C.green, fontSize: 17, lineHeight: 22 },
  questionEmoji: {
    width: 52,
    marginLeft: 5,
    fontSize: 34,
    lineHeight: 43,
    textAlign: "center",
  },
  questionTitle: {
    flex: 1,
    marginLeft: 8,
    color: C.text,
    fontSize: 16,
    lineHeight: 22,
  },
  optionsRow: {
    marginTop: 10,
    flexDirection: "row",
    alignItems: "stretch",
    gap: 8,
  },
  option: {
    flex: 1,
    minHeight: 88,
    borderRadius: 14,
    borderWidth: 1.25,
    borderColor: C.border,
    backgroundColor: "#FFFFFF",
    paddingHorizontal: 10,
    paddingVertical: 12,
    flexDirection: "row",
    alignItems: "flex-start",
  },
  selectedOption: { borderColor: C.greenLine, backgroundColor: C.greenSoft },
  radio: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: "#C8D0D4",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#FFFFFF",
  },
  radioSelected: { borderColor: C.green, backgroundColor: C.green },
  radioDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: "#FFFFFF",
  },
  optionLabel: {
    flex: 1,
    marginLeft: 8,
    color: C.text,
    fontSize: 13,
    lineHeight: 18,
    textAlign: "center",
  },
  primaryButton: {
    minHeight: 62,
    marginTop: 18,
    borderRadius: 18,
    paddingHorizontal: 24,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 13,
    backgroundColor: C.green,
  },
  primaryButtonText: { color: "#FFFFFF", fontSize: 19, lineHeight: 25 },
  disabled: { opacity: 0.45 },
  footerLandscape: {
    height: 118,
    marginHorizontal: -14,
    marginTop: 10,
    opacity: 0.9,
  },
  stateCard: {
    marginHorizontal: 14,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: "#FFFFFF",
    shadowColor: "#254936",
    shadowOpacity: 0.08,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 7 },
    elevation: 3,
  },
  contentCard: { minHeight: 300, marginTop: -18 },
  emptyCard: {
    minHeight: 300,
    marginTop: -18,
    padding: 28,
    alignItems: "center",
    justifyContent: "center",
  },
  emptyIcon: {
    width: 84,
    height: 84,
    borderRadius: 28,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: C.greenSoft,
  },
  emptyTitle: {
    marginTop: 18,
    color: C.greenDark,
    fontSize: 22,
    lineHeight: 29,
    textAlign: "center",
  },
  emptyMessage: {
    maxWidth: 330,
    marginTop: 8,
    color: C.muted,
    fontSize: 15,
    lineHeight: 23,
    textAlign: "center",
  },
  resultCard: { marginHorizontal: 0, padding: 18 },
  resultScoreRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  scoreSummary: { flex: 1, minWidth: 0 },
  scoreLabelRow: { flexDirection: "row", alignItems: "center" },
  scoreLeafIcon: {
    width: 52,
    height: 52,
    borderRadius: 26,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: C.greenSoft,
  },
  scoreLabel: {
    flex: 1,
    marginLeft: 12,
    color: C.muted,
    fontSize: 17,
    lineHeight: 23,
  },
  scoreNumberRow: {
    marginTop: 5,
    paddingLeft: 4,
    flexDirection: "row",
    alignItems: "flex-end",
  },
  scoreRing: {
    width: 118,
    height: 118,
    marginLeft: 10,
    borderRadius: 59,
    borderWidth: 11,
    borderColor: "#55AA45",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#E4F3DF",
  },
  scoreRingInner: {
    width: 82,
    height: 82,
    borderRadius: 41,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#FFFFFF",
  },
  scorePercent: { color: C.greenDark, fontSize: 24, lineHeight: 30 },
  scoreValue: { color: C.greenDark, fontSize: 50, lineHeight: 56 },
  scoreUnit: {
    marginBottom: 5,
    color: C.muted,
    fontSize: 27,
    lineHeight: 34,
  },
  recommendationPanel: {
    marginTop: 20,
    borderRadius: 20,
    padding: 15,
    backgroundColor: "#F0F8ED",
  },
  recommendationRow: { flexDirection: "row", alignItems: "flex-start" },
  recommendationIcon: {
    width: 46,
    height: 46,
    borderRadius: 23,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#E3F3DF",
  },
  recommendation: {
    flex: 1,
    marginLeft: 12,
    color: C.text,
    fontSize: 19,
    lineHeight: 27,
  },
  factorPill: {
    marginTop: 14,
    alignSelf: "stretch",
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 9,
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: C.orangeSoft,
  },
  factorIcon: {
    width: 31,
    height: 31,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#EC7A12",
  },
  factorText: {
    flex: 1,
    marginLeft: 10,
    color: "#A9470F",
    fontSize: 14,
    lineHeight: 20,
  },
  noticeCard: {
    marginTop: 14,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#D7E7F6",
    padding: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 11,
    backgroundColor: "#F3F8FD",
  },
  noticeIcon: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#2D86D4",
  },
  noticeText: { flex: 1, color: "#29445A", fontSize: 15, lineHeight: 22 },
  retakeButton: {
    minHeight: 54,
    marginTop: 10,
    borderRadius: 17,
    borderWidth: 1.5,
    borderColor: C.green,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#FFFFFF",
  },
  retakeText: { color: C.green, fontSize: 16, lineHeight: 22 },
  submitError: {
    minHeight: 220,
    marginTop: 14,
    borderRadius: 20,
    overflow: "hidden",
    backgroundColor: "#FFFFFF",
  },
  progressSkeleton: { width: "100%", height: 82, borderRadius: 20 },
  questionSkeleton: {
    width: "100%",
    height: 180,
    marginTop: 12,
    borderRadius: 20,
  },
});
