import { useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { AgOfflineBanner, AgScreen } from '@/components/ui';

import { ConsultationListView } from '../components/ConsultationListView';
import { ExpertBackHeader } from '../components/ExpertBackHeader';
import { useConsultationHistory } from '../hooks/useConsultations';
import { useExpertSync } from '../hooks/useExpertSync';
import type { Consultation } from '../types';

/** Dedicated view of concluded (resolved / closed / cancelled) consultations. */
export function ConsultationHistoryScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  useExpertSync();
  const query = useConsultationHistory();

  const open = (c: Consultation) =>
    router.push({ pathname: '/consultations/[id]', params: { id: c.id } });

  return (
    <AgScreen padded={false}>
      <AgOfflineBanner />
      <View className="flex-1 px-5">
        <ConsultationListView
          items={query.data?.items ?? []}
          isLoading={query.isLoading}
          isError={query.isError}
          isRefetching={query.isRefetching}
          onRefresh={() => void query.refetch()}
          onRetry={() => void query.refetch()}
          onPressItem={open}
          header={<ExpertBackHeader title={t('experts.historyTitle')} />}
          emptyTitle={t('experts.historyEmptyTitle')}
          emptyMessage={t('experts.historyEmptyMessage')}
        />
      </View>
    </AgScreen>
  );
}
