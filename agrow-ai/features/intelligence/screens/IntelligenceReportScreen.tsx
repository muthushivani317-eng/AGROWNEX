import { useTranslation } from 'react-i18next';
import { useRouter } from 'expo-router';
import { RefreshControl, ScrollView, View } from 'react-native';

import {
  AgErrorState,
  AgScreen,
  AgSkeleton,
  AgText,
} from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import { HealthScoreCard } from '../components/HealthScoreCard';
import { IntelligenceBackHeader } from '../components/IntelligenceBackHeader';
import { PriorityIssueList } from '../components/PriorityIssueList';
import { RecommendationTimeline } from '../components/RecommendationTimeline';
import { useIntelligenceReport } from '../hooks/useIntelligence';
import type { HealthModule, Recommendation } from '../types';

const MODULE_ROUTES: Record<HealthModule, string> = {
  disease: '/disease', nutrient: '/nutrient', soil: '/soil',
  satellite: '/satellite', weather: '/weather', growth: '/growth',
};

/** A full, saved intelligence report (health, issues, recommendations). */
export function IntelligenceReportScreen({ reportId }: { reportId: string }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const router = useRouter();
  const query = useIntelligenceReport(reportId);
  const report = query.data;
  const openModule = (module: HealthModule) => router.push(MODULE_ROUTES[module] as never);
  const openRecommendation = (recommendation: Recommendation) => {
    const module = recommendation.modules.find((item): item is HealthModule => item in MODULE_ROUTES);
    if (module) return openModule(module);
    router.push((recommendation.category === 'expert' ? '/experts' : '/calendar') as never);
  };

  return (
    <AgScreen padded={false}>
      <ScrollView
        className="flex-1 px-5"
        contentContainerClassName="pb-24 gap-3"
        refreshControl={
          <RefreshControl
            refreshing={query.isRefetching}
            onRefresh={() => void query.refetch()}
            tintColor={colors.primary}
          />
        }
      >
        <View className="pb-1 pt-1">
          <IntelligenceBackHeader title={t('intelligence.reportTitle')} />
        </View>

        {query.isLoading ? (
          <View className="gap-3">
            {[0, 1, 2].map((i) => (
              <AgSkeleton key={i} className="h-32 w-full rounded-card" />
            ))}
          </View>
        ) : query.isError || !report ? (
          <AgErrorState onRetry={() => void query.refetch()} />
        ) : (
          <>
            <AgText variant="caption" color="muted">
              {t('intelligence.generatedAt', { date: report.generatedAt.slice(0, 10) })}
            </AgText>
            <HealthScoreCard
              health={report.health}
              overall={report.overallHealthScore}
              risk={report.overallRisk}
              confidence={report.confidence}
              onModulePress={openModule}
            />
            <PriorityIssueList issues={report.priorityIssues} />
            <RecommendationTimeline
              recommendations={report.recommendations}
              onRecommendationPress={openRecommendation}
            />
            <AgText variant="caption" color="muted" className="mt-2 px-1">
              {t('intelligence.disclaimer')}
            </AgText>
          </>
        )}
      </ScrollView>
    </AgScreen>
  );
}
