import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { AgCard, AgText } from '@/components/ui';

import type { AuditRow } from '../types';
import { formatShortDate } from './adminMeta';

/** One immutable audit-trail entry (docs/SECURITY.md → audit is never deleted). */
export function AuditRowItem({ row }: { row: AuditRow }) {
  const { t } = useTranslation();
  const target = [row.target, row.targetId].filter(Boolean).join(' · ');
  const status =
    row.meta && typeof row.meta.status === 'string' ? (row.meta.status as string) : null;
  return (
    <AgCard variant="compact" className="gap-1">
      <View className="flex-row items-center justify-between gap-2">
        <AgText variant="bodySmall" weight="semibold" className="flex-1">
          {t(`admin.action.${row.action}`, { defaultValue: row.action })}
        </AgText>
        <AgText variant="caption" color="muted">
          {formatShortDate(row.createdAt)}
        </AgText>
      </View>
      <View className="flex-row flex-wrap items-center gap-x-3 gap-y-0.5">
        {row.role ? (
          <AgText variant="caption" color="muted">
            {row.role}
          </AgText>
        ) : null}
        {target ? (
          <AgText variant="caption" color="muted">
            {target}
          </AgText>
        ) : null}
        {status ? (
          <AgText variant="caption" color="muted">
            → {status}
          </AgText>
        ) : null}
        {row.ipAddress ? (
          <AgText variant="caption" color="muted" className="ml-auto">
            {row.ipAddress}
          </AgText>
        ) : null}
      </View>
    </AgCard>
  );
}
