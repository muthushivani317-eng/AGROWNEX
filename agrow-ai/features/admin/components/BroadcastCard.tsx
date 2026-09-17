import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { AgBadge, AgCard, AgText } from '@/components/ui';

import { BROADCAST_STATUS_TONE, BROADCAST_TARGET_LABEL_KEY } from '../constants';
import type { Broadcast } from '../types';
import { formatShortDate } from './adminMeta';

/** A sent/scheduled broadcast with its delivery figures (history is retained). */
export function BroadcastCard({ broadcast }: { broadcast: Broadcast }) {
  const { t } = useTranslation();
  const target = broadcast.targetValue
    ? `${t(BROADCAST_TARGET_LABEL_KEY[broadcast.targetType] ?? broadcast.targetType)}: ${broadcast.targetValue}`
    : t(BROADCAST_TARGET_LABEL_KEY[broadcast.targetType] ?? broadcast.targetType);
  return (
    <AgCard className="gap-2">
      <View className="flex-row items-start justify-between gap-2">
        <AgText variant="body" weight="semibold" className="flex-1">
          {broadcast.title}
        </AgText>
        <AgBadge
          label={t(`admin.broadcastStatus.${broadcast.status}`)}
          tone={BROADCAST_STATUS_TONE[broadcast.status] ?? 'neutral'}
        />
      </View>
      <AgText variant="caption" color="muted" numberOfLines={2}>
        {broadcast.body}
      </AgText>
      <View className="flex-row flex-wrap items-center gap-x-3 gap-y-0.5">
        <AgText variant="caption" color="muted">
          {target}
        </AgText>
        <AgText variant="caption" color="muted">
          {t('admin.deliveredOf', {
            delivered: broadcast.deliveredCount,
            total: broadcast.recipientCount,
          })}
        </AgText>
        <AgText variant="caption" color="muted" className="ml-auto">
          {formatShortDate(broadcast.sentAt ?? broadcast.createdAt)}
        </AgText>
      </View>
    </AgCard>
  );
}
