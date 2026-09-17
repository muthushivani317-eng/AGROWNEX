import { BarChart3 } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { AgErrorState, AgScreen, AgSkeleton } from '@/components/ui';

import { AccessDenied } from '../components/AccessDenied';
import { AdminHeader } from '../components/AdminHeader';
import { DistributionBars } from '../components/DistributionBars';
import { SampleNotice } from '../components/SampleNotice';
import { useAdminAnalytics } from '../hooks/useAdmin';
import { isAccessError } from '../services/adminProvider';

/**
 * Platform analytics — real distributions across crops, diseases, nutrient deficiencies,
 * soil categories, expert consultations and produce, plus farmer growth over time. Every
 * figure is a genuine group-by; an empty category shows “no data”, never a fake chart.
 */
export function AnalyticsScreen() {
  const { t } = useTranslation();
  const query = useAdminAnalytics();

  if (isAccessError(query.error)) return <AccessDenied message={query.error.message} />;

  const data = query.data;

  return (
    <AgScreen scroll>
      <AdminHeader
        icon={BarChart3}
        title={t('admin.nav.analytics')}
        subtitle={t('admin.analyticsSubtitle')}
        back
      />

      {query.isLoading ? (
        <View className="mt-4 gap-3">
          {[0, 1, 2].map((i) => (
            <AgSkeleton key={i} className="h-40 w-full rounded-card" />
          ))}
        </View>
      ) : query.isError || !data ? (
        <AgErrorState onRetry={() => void query.refetch()} />
      ) : (
        <View className="mt-4 gap-3">
          <SampleNotice visible={Boolean(data.isSample)} />
          <DistributionBars title={t('admin.analytics.farmerGrowth')} items={data.farmerGrowth} />
          <DistributionBars title={t('admin.analytics.crops')} items={data.cropDistribution} />
          <DistributionBars title={t('admin.analytics.diseases')} items={data.diseaseDistribution} />
          <DistributionBars
            title={t('admin.analytics.nutrients')}
            items={data.nutrientDeficiencies}
          />
          <DistributionBars title={t('admin.analytics.soil')} items={data.soilCategories} />
          <DistributionBars title={t('admin.analytics.experts')} items={data.expertTrends} />
          <DistributionBars title={t('admin.analytics.produce')} items={data.produceByCrop} />
        </View>
      )}
    </AgScreen>
  );
}
