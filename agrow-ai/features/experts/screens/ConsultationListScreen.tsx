import { useRouter } from 'expo-router';
import { ArrowLeft, MessageSquarePlus, Users } from 'lucide-react-native';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import {
  AgChip,
  AgOfflineBanner,
  AgPressable,
  AgScreen,
  AgText,
} from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import { ConsultationListView } from '../components/ConsultationListView';
import { CONSULTATION_VIEWS, VIEW_LABEL_KEY } from '../constants';
import {
  useConsultationHistory,
  useConsultationList,
  usePendingConsultations,
} from '../hooks/useConsultations';
import { useExpertSync } from '../hooks/useExpertSync';
import type { Consultation, ConsultationView } from '../types';

/** Expert Connect hub: the farmer's consultations (All / Pending / History) + ask. */
export function ConsultationListScreen() {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const router = useRouter();
  useExpertSync();

  const [view, setView] = useState<ConsultationView>('all');
  const listQuery = useConsultationList({ pageSize: 50 }, view === 'all');
  const pendingQuery = usePendingConsultations(view === 'pending');
  const historyQuery = useConsultationHistory(view === 'history');

  const active = useMemo(() => {
    if (view === 'pending') return pendingQuery;
    if (view === 'history') return historyQuery;
    return listQuery;
  }, [view, listQuery, pendingQuery, historyQuery]);

  const open = (c: Consultation) =>
    router.push({ pathname: '/consultations/[id]', params: { id: c.id } });

  const header = (
    <View className="gap-3 pb-1">
      {/* Reached from Home's "Experts" quick action with no back affordance
          at all -- every other pushed screen in the app has one (2026-08
          pre-release UI pass). */}
      <AgPressable
        onPress={() => router.back()}
        accessibilityRole="button"
        accessibilityLabel={t('common.back')}
        hitSlop={8}
        className="mt-2 self-start"
      >
        <ArrowLeft size={26} color={colors.text} />
      </AgPressable>
      <View className="flex-row items-center justify-between">
        <AgText variant="headingL" weight="bold">
          {t('experts.title')}
        </AgText>
        <AgPressable
          onPress={() => router.push('/experts')}
          accessibilityRole="button"
          accessibilityLabel={t('experts.browseExperts')}
          className="h-10 flex-row items-center gap-1 rounded-full bg-primary/12 px-3"
        >
          <Users size={16} color={colors.primary} />
          <AgText variant="caption" weight="semibold" color="primary">
            {t('experts.experts')}
          </AgText>
        </AgPressable>
      </View>
      <AgText variant="bodySmall" color="muted">
        {t('experts.subtitle')}
      </AgText>
      <View className="flex-row gap-2">
        {CONSULTATION_VIEWS.map((v) => (
          <AgChip
            key={v}
            label={t(VIEW_LABEL_KEY[v])}
            selected={view === v}
            onPress={() => setView(v)}
          />
        ))}
      </View>
    </View>
  );

  return (
    <AgScreen padded={false}>
      <AgOfflineBanner />
      <View className="flex-1 px-5">
        <ConsultationListView
          items={active.data?.items ?? []}
          isLoading={active.isLoading}
          isError={active.isError}
          isRefetching={active.isRefetching}
          onRefresh={() => void active.refetch()}
          onRetry={() => void active.refetch()}
          onPressItem={open}
          header={header}
          emptyTitle={t('experts.emptyTitle')}
          emptyMessage={t('experts.emptyMessage')}
        />
      </View>

      <AgPressable
        onPress={() => router.push('/consultations/new')}
        accessibilityRole="button"
        accessibilityLabel={t('experts.ask')}
        className="absolute bottom-6 right-6 h-16 w-16 items-center justify-center rounded-full bg-primary shadow-lg shadow-black/25"
      >
        <MessageSquarePlus size={28} color={colors.onPrimary} />
      </AgPressable>
    </AgScreen>
  );
}
