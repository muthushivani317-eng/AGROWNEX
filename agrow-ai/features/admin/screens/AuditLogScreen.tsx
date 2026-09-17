import { ClipboardList } from 'lucide-react-native';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ScrollView, View } from 'react-native';

import {
  AgChip,
  AgEmptyState,
  AgErrorState,
  AgScreen,
  AgSkeleton,
  AgText,
} from '@/components/ui';

import { AccessDenied } from '../components/AccessDenied';
import { AdminHeader } from '../components/AdminHeader';
import { AuditRowItem } from '../components/AuditRowItem';
import { useAdminAudit } from '../hooks/useAdmin';
import { isAccessError } from '../services/adminProvider';

const ACTION_FILTERS = [
  'view_dashboard',
  'view_farmers',
  'view_procurement',
  'procurement_status_changed',
  'broadcast_sent',
  'announcement_created',
] as const;

/**
 * Audit logs — the immutable trail of every admin action (docs/SECURITY.md → audit is
 * never deleted). Filterable by action; newest first.
 */
export function AuditLogScreen() {
  const { t } = useTranslation();
  const [action, setAction] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);
  const query = useAdminAudit({ action }, page);

  if (isAccessError(query.error)) return <AccessDenied message={query.error.message} />;

  const data = query.data;

  return (
    <AgScreen scroll>
      <AdminHeader
        icon={ClipboardList}
        title={t('admin.nav.audit')}
        subtitle={t('admin.auditSubtitle')}
        back
      />

      <ScrollView horizontal showsHorizontalScrollIndicator={false} className="-mx-1 mt-4">
        <View className="flex-row gap-2 px-1">
          <AgChip
            label={t('admin.allActions')}
            selected={!action}
            onPress={() => {
              setAction(undefined);
              setPage(1);
            }}
          />
          {ACTION_FILTERS.map((a) => (
            <AgChip
              key={a}
              label={t(`admin.action.${a}`, { defaultValue: a })}
              selected={action === a}
              onPress={() => {
                setAction(a);
                setPage(1);
              }}
            />
          ))}
        </View>
      </ScrollView>

      {query.isLoading ? (
        <View className="mt-4 gap-2">
          {[0, 1, 2, 3, 4].map((i) => (
            <AgSkeleton key={i} className="h-16 w-full rounded-card" />
          ))}
        </View>
      ) : query.isError ? (
        <AgErrorState onRetry={() => void query.refetch()} />
      ) : !data || data.items.length === 0 ? (
        <AgEmptyState
          icon={ClipboardList}
          title={t('admin.auditEmptyTitle')}
          message={t('admin.auditEmptyMessage')}
        />
      ) : (
        <View className="mt-4 gap-2">
          {data.items.map((row) => (
            <AuditRowItem key={row.id} row={row} />
          ))}
          {data.totalPages > 1 ? (
            <View className="mt-2 flex-row items-center justify-between">
              <AgText
                variant="caption"
                color="muted"
                onPress={() => setPage((p) => Math.max(1, p - 1))}
              >
                {t('common.back')}
              </AgText>
              <AgText variant="caption" color="muted">
                {t('admin.pageOf', { page, total: data.totalPages })}
              </AgText>
              <AgText
                variant="caption"
                color="muted"
                onPress={() => setPage((p) => Math.min(data.totalPages, p + 1))}
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
