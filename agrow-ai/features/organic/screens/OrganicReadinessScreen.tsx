import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';
import { ArrowLeft, Check } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';

import {
  AgBadge,
  AgButton,
  AgCard,
  AgEmptyState,
  AgErrorState,
  AgPressable,
  AgScreen,
  AgSkeleton,
  AgText,
} from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useLanguage } from '@/hooks/useLanguage';

import {
  useOrganicReadinessQuestions,
  useSubmitOrganicReadiness,
} from '../hooks/useOrganicReadiness';
import type { ReadinessResult } from '../services/organicReadinessApi';

/**
 * Organic Readiness Check (blueprint Phase 1). Deliberately separate from
 * OrganicProfileScreen (owner decision, 2026-09-23 -- Option A): this is a
 * new first-run assessment on top of organic_mvp's admin-reviewed question
 * set, not a replacement for the existing 3-mode profile picker.
 *
 * Questions/scoring/recommendation text are 100% server-driven -- nothing
 * here is hardcoded, matching this app's existing pattern for verified
 * agronomic content (crop calendar, disease-risk rule packs, etc). If no
 * admin-approved question set exists yet, this honestly says so rather than
 * inventing a fallback.
 */
export function OrganicReadinessScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const { language } = useLanguage();
  const pick = (ta: string, en?: string | null) =>
    language === 'ta' ? ta : (en ?? ta);

  const questionsQuery = useOrganicReadinessQuestions();
  const submit = useSubmitOrganicReadiness(farmId);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<ReadinessResult | null>(null);

  const questions = questionsQuery.data?.questions ?? [];
  const allAnswered = useMemo(
    () => questions.length > 0 && questions.every((q) => answers[q.id]),
    [questions, answers],
  );

  if (questionsQuery.isLoading) {
    return (
      <AgScreen>
        <AgSkeleton className="h-10 w-full" />
        <AgSkeleton className="mt-4 h-64 w-full" />
      </AgScreen>
    );
  }

  if (questionsQuery.isError) {
    return (
      <AgScreen>
        <AgErrorState
          message={t('organic.readinessLoadError')}
          onRetry={() => void questionsQuery.refetch()}
        />
      </AgScreen>
    );
  }

  if (questions.length === 0) {
    return (
      <AgScreen>
        <View className="flex-row items-center gap-2">
          <AgPressable
            onPress={() => router.back()}
            accessibilityRole="button"
            accessibilityLabel={t('common.back')}
            className="h-10 w-10 items-center justify-center"
          >
            <ArrowLeft size={24} color={colors.text} />
          </AgPressable>
          <AgText variant="headingM" weight="bold">
            {t('organic.readinessTitle')}
          </AgText>
        </View>
        <View className="mt-8">
          <AgEmptyState
            title={t('organic.readinessNotSetUpTitle')}
            message={t('organic.readinessNotSetUpMessage')}
          />
        </View>
      </AgScreen>
    );
  }

  if (result) {
    return (
      <AgScreen scroll>
        <AgText variant="headingM" weight="bold">
          {t('organic.readinessResultTitle')}
        </AgText>
        <AgCard className="mt-4">
          <AgText variant="label" color="muted">
            {t('organic.readinessScoreLabel', { score: result.score })}
          </AgText>
          <AgText variant="bodyLarge" weight="bold" className="mt-2">
            {pick(result.recommendation_ta, result.recommendation_en)}
          </AgText>
          {result.risk_flags.length > 0 ? (
            <View className="mt-3 flex-row flex-wrap gap-2">
              {result.risk_flags.map((flag) => (
                <AgBadge key={flag} label={flag} tone="warning" />
              ))}
            </View>
          ) : null}
        </AgCard>
        <AgCard className="mt-3">
          <AgText variant="bodySmall" color="muted">
            {result.certification_notice}
          </AgText>
        </AgCard>
        <AgButton
          className="mt-6"
          title={t('common.done')}
          onPress={() => router.back()}
        />
        <AgButton
          className="mt-3"
          variant="secondary"
          title={t('organic.readinessRetake')}
          onPress={() => {
            setResult(null);
            setAnswers({});
          }}
        />
      </AgScreen>
    );
  }

  return (
    <AgScreen scroll>
      <View className="flex-row items-center gap-2">
        <AgPressable
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={t('common.back')}
          className="h-10 w-10 items-center justify-center"
        >
          <ArrowLeft size={24} color={colors.text} />
        </AgPressable>
        <AgText variant="headingM" weight="bold">
          {t('organic.readinessTitle')}
        </AgText>
      </View>
      <AgText color="muted" className="mt-2">
        {t('organic.readinessIntro')}
      </AgText>

      {questions.map((question) => (
        <AgCard key={question.id} className="mt-4">
          <AgText variant="label" weight="bold">
            {pick(question.title_ta, question.title_en)}
          </AgText>
          {Object.entries(question.options).map(([key, option]) => {
            const selected = answers[question.id] === key;
            return (
              <Pressable
                key={key}
                onPress={() =>
                  setAnswers((prev) => ({ ...prev, [question.id]: key }))
                }
                accessibilityRole="radio"
                accessibilityState={{ checked: selected }}
                style={[styles.option, selected && styles.selectedOption]}
              >
                <View
                  style={[
                    styles.indicator,
                    { backgroundColor: selected ? colors.primary : colors.surface },
                  ]}
                >
                  {selected ? <Check size={16} color="#fff" /> : null}
                </View>
                <AgText style={{ color: colors.text, flex: 1 }}>
                  {pick(option.label_ta ?? key, option.label_en)}
                </AgText>
              </Pressable>
            );
          })}
        </AgCard>
      ))}

      {submit.isError ? (
        <View className="mt-4">
          <AgErrorState message={t('organic.readinessSubmitError')} />
        </View>
      ) : null}

      <AgButton
        className="mt-6"
        title={t('organic.readinessSubmit')}
        disabled={!allAnswered}
        loading={submit.isPending}
        onPress={() =>
          submit.mutate(answers, { onSuccess: (data) => setResult(data) })
        }
      />
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  option: {
    marginTop: 12,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#D8DDD9',
    borderRadius: 12,
    padding: 12,
    backgroundColor: '#FFFFFF',
  },
  selectedOption: { borderColor: '#19763A', backgroundColor: '#F4FAF1' },
  indicator: {
    width: 24,
    height: 24,
    borderRadius: 12,
    marginRight: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
