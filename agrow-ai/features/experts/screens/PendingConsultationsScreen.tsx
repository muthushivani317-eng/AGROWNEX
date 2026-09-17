import { useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { AgOfflineBanner, AgScreen } from '@/components/ui';

import { ConsultationListView } from '../components/ConsultationListView';
import { ExpertBackHeader } from '../components/ExpertBackHeader';
import { usePendingConsultations } from '../hooks/useConsultations';
import { useExpertSync } from '../hooks/useExpertSync';
import type { Consultation } from '../types';

/** Dedicated view of the farmer's open (pending) consultations. */
export function PendingConsultationsScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  useExpertSync();
  const query = usePendingConsultations();

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
          header={<ExpertBackHeader title={t('experts.pendingTitle')} />}
          emptyTitle={t('experts.pendingEmptyTitle')}
          emptyMessage={t('experts.pendingEmptyMessage')}
        />
      </View>
    </AgScreen>
  );
}
