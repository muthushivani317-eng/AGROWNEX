import { Activity } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { AgCard, AgErrorState, AgScreen, AgSkeleton, AgText } from '@/components/ui';

import { AccessDenied } from '../components/AccessDenied';
import { AdminHeader } from '../components/AdminHeader';
import { formatCount } from '../components/adminMeta';
import { DistributionBars } from '../components/DistributionBars';
import { SampleNotice } from '../components/SampleNotice';
import { useAdminAi } from '../hooks/useAdmin';
import { isAccessError } from '../services/adminProvider';
import type { AiMonitoring } from '../types';

const TILES: { key: keyof AiMonitoring; labelKey: string }[] = [
  { key: 'todayRequests', labelKey: 'admin.ai.todayRequests' },
  { key: 'totalMessages', labelKey: 'admin.ai.totalMessages' },
  { key: 'diseaseDetections', labelKey: 'admin.ai.diseaseDetections' },
  { key: 'nutrientAnalyses', labelKey: 'admin.ai.nutrientAnalyses' },
  { key: 'satelliteAnalyses', labelKey: 'admin.ai.satelliteAnalyses' },
  { key: 'memoryGenerated', labelKey: 'admin.ai.memoryGenerated' },
  { key: 'intelligenceReports', labelKey: 'admin.ai.intelligenceReports' },
  { key: 'averageConfidence', labelKey: 'admin.ai.averageConfidence' },
];

/**
 * AI monitoring — usage across ChatGPT (chat) and Gemini (vision/OCR). Metrics that are
 * not instrumented in V1 (model latency, API failures) are surfaced honestly as “not
 * tracked”, never fabricated (docs/PRODUCT_RULES.md).
 */
export function AiMonitoringScreen() {
  const { t } = useTranslation();
  const query = useAdminAi();

  if (isAccessError(query.error)) return <AccessDenied message={query.error.message} />;

  const data = query.data;

  return (
    <AgScreen scroll>
      <AdminHeader
        icon={Activity}
        title={t('admin.nav.ai')}
        subtitle={t('admin.aiSubtitle')}
        back
      />

      {query.isLoading ? (
        <View className="mt-4 flex-row flex-wrap gap-3">
          {[0, 1, 2, 3].map((i) => (
            <AgSkeleton key={i} className="h-24 min-w-[46%] flex-1 rounded-card" />
          ))}
        </View>
      ) : query.isError || !data ? (
        <AgErrorState onRetry={() => void query.refetch()} />
      ) : (
        <View className="mt-4 gap-3">
          <SampleNotice visible={Boolean(data.isSample)} />

          <View className="flex-row flex-wrap gap-3">
            {TILES.map(({ key, labelKey }) => (
              <AgCard key={String(key)} variant="compact" className="min-w-[46%] flex-1 gap-1">
                <AgText variant="headingS" weight="bold">
                  {key === 'averageConfidence' && data.averageConfidence != null
                    ? `${data.averageConfidence}%`
                    : formatCount(data[key] as number | null)}
                </AgText>
                <AgText variant="caption" color="muted">
                  {t(labelKey)}
                </AgText>
              </AgCard>
            ))}
          </View>

          <DistributionBars
            title={t('admin.ai.dailyRequests')}
            items={data.dailyRequests.map((p) => ({ label: p.label, count: p.count }))}
          />

          <AgCard className="gap-2 border border-warning/30 bg-warning/5">
            <AgText variant="label" weight="semibold">
              {t('admin.ai.notTrackedTitle')}
            </AgText>
            <View className="flex-row items-center justify-between">
              <AgText variant="caption" color="muted">
                {t('admin.ai.modelLatency')}
              </AgText>
              <AgText variant="caption" weight="semibold" color="muted">
                {data.modelLatencyMs == null ? t('admin.notTracked') : `${data.modelLatencyMs} ms`}
              </AgText>
            </View>
            <View className="flex-row items-center justify-between">
              <AgText variant="caption" color="muted">
                {t('admin.ai.apiFailures')}
              </AgText>
              <AgText variant="caption" weight="semibold" color="muted">
                {data.apiFailures == null ? t('admin.notTracked') : `${data.apiFailures}`}
              </AgText>
            </View>
          </AgCard>
        </View>
      )}
    </AgScreen>
  );
}
