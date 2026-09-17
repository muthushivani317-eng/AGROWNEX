import { Users } from 'lucide-react-native';
import { useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import {
  AgButton,
  AgEmptyState,
  AgErrorState,
  AgInput,
  AgScreen,
  AgSkeleton,
  AgText,
} from '@/components/ui';

import { AccessDenied } from '../components/AccessDenied';
import { AdminHeader } from '../components/AdminHeader';
import { FarmerCard } from '../components/FarmerCard';
import { useAdminFarmers } from '../hooks/useAdmin';
import { isAccessError } from '../services/adminProvider';

/**
 * Farmer management — a read-only, searchable directory of every registered farmer.
 * The admin can inspect a farmer's profile and cross-module activity, but never edits
 * farmer data (docs: no direct farmer-data modification).
 */
export function FarmerManagementScreen() {
  const { t } = useTranslation();
  const { view } = useLocalSearchParams<{ view?: string }>();
  const [term, setTerm] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const query = useAdminFarmers({ search: search || undefined }, page);

  if (isAccessError(query.error)) return <AccessDenied message={query.error.message} />;

  const onSearch = () => {
    setPage(1);
    setSearch(term.trim());
  };

  const data = query.data;
  const totalPages = data?.totalPages ?? 0;
  const today = new Date().toISOString().slice(0, 10);
  const visibleFarmers = data?.items.filter(
    (farmer) => view !== 'new' || farmer.createdAt?.slice(0, 10) === today,
  ) ?? [];

  return (
    <AgScreen scroll>
      <AdminHeader
        icon={Users}
        title={view === 'new' ? 'New farmers' : t('admin.nav.farmers')}
        subtitle={t('admin.farmersSubtitle')}
        back
      />

      <View className="mt-4 flex-row gap-2">
        <View className="flex-1">
          <AgInput
            placeholder={t('admin.searchFarmers')}
            value={term}
            onChangeText={setTerm}
            onSubmitEditing={onSearch}
            returnKeyType="search"
          />
        </View>
        <AgButton title={t('common.search')} onPress={onSearch} fullWidth={false} />
      </View>

      {query.isLoading ? (
        <View className="mt-4 gap-3">
          {[0, 1, 2, 3].map((i) => (
            <AgSkeleton key={i} className="h-20 w-full rounded-card" />
          ))}
        </View>
      ) : query.isError ? (
        <AgErrorState onRetry={() => void query.refetch()} />
      ) : !data || visibleFarmers.length === 0 ? (
        <AgEmptyState
          icon={Users}
          title={t('admin.farmersEmptyTitle')}
          message={t('admin.farmersEmptyMessage')}
        />
      ) : (
        <View className="mt-4 gap-3">
          <AgText variant="caption" color="muted">
            {t('admin.resultCount', { n: data.total })}
          </AgText>
          {visibleFarmers.map((farmer) => (
            <FarmerCard key={farmer.userId} farmer={farmer} />
          ))}

          {totalPages > 1 ? (
            <View className="mt-2 flex-row items-center justify-between">
              <AgButton
                title={t('common.back')}
                variant="outline"
                size="sm"
                fullWidth={false}
                disabled={page <= 1}
                onPress={() => setPage((p) => Math.max(1, p - 1))}
              />
              <AgText variant="caption" color="muted">
                {t('admin.pageOf', { page, total: totalPages })}
              </AgText>
              <AgButton
                title={t('common.next')}
                variant="outline"
                size="sm"
                fullWidth={false}
                disabled={page >= totalPages}
                onPress={() => setPage((p) => p + 1)}
              />
            </View>
          ) : null}
        </View>
      )}
    </AgScreen>
  );
}
