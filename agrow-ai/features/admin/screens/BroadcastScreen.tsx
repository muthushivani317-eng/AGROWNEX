import { Megaphone } from 'lucide-react-native';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, View } from 'react-native';

import {
  AgButton,
  AgCard,
  AgChip,
  AgDropdown,
  AgErrorState,
  AgInput,
  AgScreen,
  AgSkeleton,
  AgText,
} from '@/components/ui';

import { AccessDenied } from '../components/AccessDenied';
import { AdminHeader } from '../components/AdminHeader';
import { BroadcastCard } from '../components/BroadcastCard';
import { SampleNotice } from '../components/SampleNotice';
import { BROADCAST_TARGET_LABEL_KEY, BROADCAST_TARGET_TYPES } from '../constants';
import { useAdminNotifications, useSendBroadcast } from '../hooks/useAdmin';
import { isAccessError } from '../services/adminProvider';
import type { BroadcastScheduleType, BroadcastTargetType } from '../types';

/**
 * Broadcast management — compose and send/schedule a farmer notification. Delivered
 * server-side via the Notifications engine; the history below retains every broadcast
 * with its delivery figures.
 */
export function BroadcastScreen() {
  const { t } = useTranslation();
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [targetType, setTargetType] = useState<BroadcastTargetType>('all');
  const [targetValue, setTargetValue] = useState('');
  const [scheduleType, setScheduleType] = useState<BroadcastScheduleType>('immediate');

  const send = useSendBroadcast();
  const list = useAdminNotifications(1);

  if (isAccessError(send.error)) return <AccessDenied message={send.error.message} />;
  if (isAccessError(list.error)) return <AccessDenied message={list.error.message} />;

  const targetOptions = BROADCAST_TARGET_TYPES.map((tt) => ({
    value: tt,
    label: t(BROADCAST_TARGET_LABEL_KEY[tt]),
  }));

  const needsValue = targetType !== 'all';
  const canSend =
    title.trim().length > 0 &&
    body.trim().length > 0 &&
    (!needsValue || targetValue.trim().length > 0);

  const onSend = () => {
    if (!canSend) return;
    send.mutate(
      {
        title: title.trim(),
        body: body.trim(),
        language: 'ta',
        targetType,
        targetValue: needsValue ? targetValue.trim() : null,
        scheduleType,
      },
      {
        onSuccess: () => {
          setTitle('');
          setBody('');
          setTargetValue('');
          Alert.alert(t('admin.broadcastSent'));
          void list.refetch();
        },
        onError: () => Alert.alert(t('admin.broadcastFailed')),
      },
    );
  };

  return (
    <AgScreen scroll keyboardAvoiding>
      <AdminHeader
        icon={Megaphone}
        title={t('admin.nav.broadcast')}
        subtitle={t('admin.broadcastSubtitle')}
        back
      />

      <AgCard className="mt-4 gap-3">
        <AgInput
          label={t('admin.broadcastTitleLabel')}
          placeholder={t('admin.broadcastTitlePlaceholder')}
          value={title}
          onChangeText={setTitle}
          maxLength={160}
        />
        <AgInput
          label={t('admin.broadcastBodyLabel')}
          placeholder={t('admin.broadcastBodyPlaceholder')}
          value={body}
          onChangeText={setBody}
          multiline
          numberOfLines={3}
        />
        <AgDropdown
          label={t('admin.broadcastTarget')}
          placeholder={t('admin.broadcastTarget')}
          value={targetType}
          options={targetOptions}
          searchable={false}
          onChange={(v) => setTargetType(v as BroadcastTargetType)}
        />
        {needsValue ? (
          <AgInput
            label={t('admin.broadcastTargetValue')}
            placeholder={t('admin.broadcastTargetValuePlaceholder')}
            value={targetValue}
            onChangeText={setTargetValue}
          />
        ) : null}
        <View className="gap-1.5">
          <AgText variant="label" weight="medium" color="muted">
            {t('admin.broadcastSchedule')}
          </AgText>
          <View className="flex-row gap-2">
            <AgChip
              label={t('admin.scheduleImmediate')}
              selected={scheduleType === 'immediate'}
              onPress={() => setScheduleType('immediate')}
            />
            <AgChip
              label={t('admin.scheduleScheduled')}
              selected={scheduleType === 'scheduled'}
              onPress={() => setScheduleType('scheduled')}
            />
          </View>
        </View>
        <AgButton
          title={t('admin.sendBroadcast')}
          onPress={onSend}
          disabled={!canSend}
          loading={send.isPending}
        />
      </AgCard>

      <View className="mt-5 flex-row items-center justify-between">
        <AgText variant="label" weight="semibold" color="muted">
          {t('admin.broadcastHistory')}
        </AgText>
        {list.data ? (
          <AgText variant="caption" color="muted">
            {t('admin.totalDelivered', { n: list.data.deliveredTotal })}
          </AgText>
        ) : null}
      </View>

      {list.isLoading ? (
        <View className="mt-3 gap-3">
          {[0, 1].map((i) => (
            <AgSkeleton key={i} className="h-24 w-full rounded-card" />
          ))}
        </View>
      ) : list.isError ? (
        <AgErrorState onRetry={() => void list.refetch()} />
      ) : list.data ? (
        <View className="mt-3 gap-3">
          <SampleNotice visible={Boolean(list.data.isSample)} />
          {list.data.broadcasts.items.length === 0 ? (
            <AgText variant="caption" color="muted">
              {t('admin.noBroadcasts')}
            </AgText>
          ) : (
            list.data.broadcasts.items.map((b) => <BroadcastCard key={b.id} broadcast={b} />)
          )}
        </View>
      ) : null}
    </AgScreen>
  );
}
