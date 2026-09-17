import { LayoutDashboard } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { RefreshControl, ScrollView, View } from 'react-native';

import {
  AgCard,
  AgErrorState,
  AgOfflineBanner,
  AgScreen,
  AgSkeleton,
  AgText,
} from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import { AdminHeader } from '../components/AdminHeader';
import { AdminConsoleNavigation } from '../components/AdminConsoleNavigation';
import { MetricCard } from '../components/MetricCard';
import { SampleNotice } from '../components/SampleNotice';
import { PROCUREMENT_LABEL_KEY, PROCUREMENT_STATUSES } from '../constants';
import { useAdminDashboard, useBusinessDashboard } from '../hooks/useAdmin';
import { isAccessError } from '../services/adminProvider';
import { AccessDenied } from '../components/AccessDenied';

/**
 * Admin dashboard — the AgrowAI team's operational overview. Headline metrics across
 * every module plus quick navigation to farmer management, procurement, analytics, AI
 * monitoring, broadcasts and the audit trail. Read-only; untracked metrics show “—”.
 */
export function AdminDashboardScreen() {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const query = useAdminDashboard();
  const business = useBusinessDashboard();

  if (isAccessError(query.error)) {
    return <AccessDenied message={query.error.message} />;
  }

  const data = query.data;

  return (
    <AgScreen padded={false}>
      <AgOfflineBanner />
      <ScrollView
        className="flex-1 px-5"
        contentContainerClassName="pb-28 gap-3"
        refreshControl={
          <RefreshControl
            refreshing={query.isRefetching || business.isRefetching}
            onRefresh={() => { void query.refetch(); void business.refetch(); }}
            tintColor={colors.primary}
          />
        }
      >
        <AdminHeader
          icon={LayoutDashboard}
          title={t('admin.title')}
          subtitle={t('admin.subtitle')}
        />

        {query.isLoading ? (
          <View className="flex-row flex-wrap gap-3">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <AgSkeleton key={i} className="h-24 min-w-[46%] flex-1 rounded-card" />
            ))}
          </View>
        ) : query.isError ? (
          <AgErrorState onRetry={() => void query.refetch()} />
        ) : data ? (
          <>
            <SampleNotice visible={Boolean(data.isSample)} />

            <View className="flex-row flex-wrap gap-3">
              {data.cards.map((card) => (
                <MetricCard key={card.key} card={card} />
              ))}
            </View>

            <AdminConsoleNavigation />

            {business.data ? (
              <>
                <AgText variant="label" weight="semibold" color="muted" className="mt-2">
                  Daily business dashboard
                </AgText>
                <View className="flex-row flex-wrap gap-3">
                  {[
                    ['Farmers', business.data.total_farmers],
                    ['New today', business.data.new_farmers_today],
                    ['Active today', business.data.active_farmers_today],
                    ['Active 7 days', business.data.active_farmers_7d],
                    ['Listings today', business.data.produce_listings_today],
                    ['Transactions', business.data.transactions],
                    ['GMV', `₹${business.data.gmv}`],
                    ['Outstanding', `₹${business.data.payment_outstanding}`],
                    ['Earned commission', `₹${business.data.earned_commission}`],
                  ].map(([label, value]) => (
                    <AgCard key={String(label)} variant="compact" className="min-w-[46%] flex-1 gap-1">
                      <AgText variant="headingS" weight="bold">{String(value)}</AgText>
                      <AgText variant="caption" color="muted">{String(label)}</AgText>
                    </AgCard>
                  ))}
                </View>
              </>
            ) : null}

            <AgText variant="label" weight="semibold" color="muted" className="mt-2">
              {t('admin.procurementPipeline')}
            </AgText>
            <AgCard className="flex-row flex-wrap gap-x-4 gap-y-2">
              {PROCUREMENT_STATUSES.map((status) => (
                <View key={status} className="flex-row items-center gap-1">
                  <AgText variant="caption" weight="bold">
                    {data.procurementStatusCounts[status] ?? 0}
                  </AgText>
                  <AgText variant="caption" color="muted">
                    {t(PROCUREMENT_LABEL_KEY[status])}
                  </AgText>
                </View>
              ))}
            </AgCard>

          </>
        ) : null}
      </ScrollView>
    </AgScreen>
  );
}
