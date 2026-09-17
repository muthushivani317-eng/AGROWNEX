import { Warehouse } from 'lucide-react-native';
import { useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, View } from 'react-native';

import {
  AgButton,
  AgCard,
  AgEmptyState,
  AgErrorState,
  AgScreen,
  AgSkeleton,
  AgText,
  AgInput,
} from '@/components/ui';

import { AccessDenied } from '../components/AccessDenied';
import { AdminHeader } from '../components/AdminHeader';
import { formatKg } from '../components/adminMeta';
import { DistributionBars } from '../components/DistributionBars';
import { ProcurementCard } from '../components/ProcurementCard';
import { SampleNotice } from '../components/SampleNotice';
import { useAdminMe, useAdminProcurement, useRevealBuyerContact, useUpdateProcurementCase, useUpdateProcurementStatus } from '../hooks/useAdmin';
import { isAccessError } from '../services/adminProvider';
import type { ProcurementStatus } from '../types';

/**
 * Procurement dashboard — future-harvest offers plus village/crop/season analytics.
 * This is procurement planning, NOT a marketplace: advancing an offer's pipeline status
 * is audited and never mutates the farmer's own listing.
 */
export function ProcurementScreen() {
  const { t } = useTranslation();
  const { view } = useLocalSearchParams<{ view?: string }>();
  const [page, setPage] = useState(1);
  const [term, setTerm] = useState('');
  const [search, setSearch] = useState('');
  const query = useAdminProcurement({ search: search || undefined }, page);
  const update = useUpdateProcurementStatus();
  const updateCase = useUpdateProcurementCase();
  const reveal = useRevealBuyerContact();
  const admin = useAdminMe();
  const [revealedContacts, setRevealedContacts] = useState<Record<string, string>>({});

  if (isAccessError(query.error)) return <AccessDenied message={query.error.message} />;

  const onChange = (offerId: string, status: ProcurementStatus) => {
    update.mutate(
      { offerId, status },
      { onError: () => Alert.alert(t('admin.statusUpdateFailed')) },
    );
  };

  const data = query.data;
  const analytics = data?.analytics;
  const visibleItems = data?.page.items.filter((row) => {
    if (!view) return true;
    if (view === 'new') return row.adminStatus === 'new';
    if (view === 'buyer-search') {
      return ['finding_buyers', 'buyer_interested'].includes(row.adminStatus);
    }
    if (view === 'negotiations') {
      return ['offer_received', 'farmer_approval_pending'].includes(row.adminStatus);
    }
    if (view === 'completed') return row.adminStatus === 'farmer_accepted';
    return true;
  }) ?? [];
  const viewTitle = {
    new: 'New listings',
    'buyer-search': 'Buyer search',
    negotiations: 'Negotiations',
    completed: 'Completed deals',
  }[view ?? ''];

  return (
    <AgScreen scroll>
      <AdminHeader
        icon={Warehouse}
        title={viewTitle ?? t('admin.nav.procurement')}
        subtitle={t('admin.procurementSubtitle')}
        back
      />

      <View className="mt-4 flex-row gap-2">
        <View className="flex-1">
          <AgInput
            placeholder="Search AGP/AGF reference or crop"
            value={term}
            onChangeText={setTerm}
            onSubmitEditing={() => { setPage(1); setSearch(term.trim()); }}
            returnKeyType="search"
          />
        </View>
        <AgButton
          title={t('common.search')}
          fullWidth={false}
          onPress={() => { setPage(1); setSearch(term.trim()); }}
        />
      </View>

      {query.isLoading ? (
        <View className="mt-4 gap-3">
          {[0, 1, 2].map((i) => (
            <AgSkeleton key={i} className="h-32 w-full rounded-card" />
          ))}
        </View>
      ) : query.isError ? (
        <AgErrorState onRetry={() => void query.refetch()} />
      ) : !data ? null : (
        <View className="mt-4 gap-3">
          <SampleNotice visible={Boolean(data.isSample)} />

          {analytics ? (
            <>
              <View className="flex-row gap-3">
                <AgCard variant="compact" className="flex-1 gap-1">
                  <AgText variant="headingS" weight="bold">
                    {analytics.totalOffers}
                  </AgText>
                  <AgText variant="caption" color="muted">
                    {t('admin.totalOffers')}
                  </AgText>
                </AgCard>
                <AgCard variant="compact" className="flex-1 gap-1">
                  <AgText variant="headingS" weight="bold">
                    {formatKg(analytics.totalQuantityKg)}
                  </AgText>
                  <AgText variant="caption" color="muted">
                    {t('admin.totalQuantity')}
                  </AgText>
                </AgCard>
              </View>
              <DistributionBars
                title={t('admin.byCrop')}
                items={analytics.byCrop.map((b) => ({ label: b.label, count: b.count }))}
              />
              <DistributionBars
                title={t('admin.byVillage')}
                items={analytics.byVillage.map((b) => ({ label: b.label, count: b.count }))}
              />
            </>
          ) : null}

          <AgText variant="label" weight="semibold" color="muted" className="mt-1">
            {t('admin.offers')}
          </AgText>
          {visibleItems.length === 0 ? (
            <AgEmptyState
              icon={Warehouse}
              title={t('admin.procurementEmptyTitle')}
              message={t('admin.procurementEmptyMessage')}
            />
          ) : (
            visibleItems.map((row) => (
              <ProcurementCard
                key={row.offerId}
                row={row}
                disabled={update.isPending || updateCase.isPending}
                adminId={admin.data?.id ?? null}
                revealedContact={revealedContacts[row.offerId]}
                onChangeStatus={(status) => onChange(row.offerId, status)}
                onSaveCase={(input) => updateCase.mutate(
                  { offerId: row.offerId, input },
                  { onError: () => Alert.alert(t('admin.statusUpdateFailed')) },
                )}
                onRevealContact={() => reveal.mutate(row.offerId, {
                  onSuccess: (contact) => setRevealedContacts((current) => ({ ...current, [row.offerId]: contact })),
                  onError: () => Alert.alert(t('admin.statusUpdateFailed')),
                })}
              />
            ))
          )}

          {data.page.totalPages > 1 ? (
            <View className="mt-2 flex-row items-center justify-between">
              <AgText
                variant="caption"
                color="muted"
                onPress={() => setPage((p) => Math.max(1, p - 1))}
              >
                {t('common.back')}
              </AgText>
              <AgText variant="caption" color="muted">
                {t('admin.pageOf', { page, total: data.page.totalPages })}
              </AgText>
              <AgText
                variant="caption"
                color="muted"
                onPress={() => setPage((p) => Math.min(data.page.totalPages, p + 1))}
              >
                {t('common.next')}
              </AgText>
            </View>
          ) : null}
        </View>
      )}
    </AgScreen>
  );
}
