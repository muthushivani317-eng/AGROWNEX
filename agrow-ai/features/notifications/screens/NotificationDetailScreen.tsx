import { useRouter } from 'expo-router';
import { ExternalLink, Trash2 } from 'lucide-react-native';
import { useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { AgBadge, AgButton, AgCard, AgScreen, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import { NotificationBackHeader } from '../components/NotificationBackHeader';
import { MODULE_ICON } from '../components/moduleIcon';
import {
  MODULE_LABEL_KEY,
  SEVERITY_LABEL_KEY,
  SEVERITY_TONE,
} from '../constants';
import {
  useDismissNotification,
  useMarkRead,
  useNotificationList,
} from '../hooks/useNotifications';
import { isValidActionRoute } from '../utils/priority';
import { relativeTimeKey } from '../utils/time';
import { notificationTheme as nt } from '../notificationTheme';

/** Notification detail: full message, source, severity, and a deep link to the
 * originating module + dismiss. */
export function NotificationDetailScreen({ id }: { id: string }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const router = useRouter();

  // The detail is read from the already-loaded list (no per-item GET endpoint).
  const listQuery = useNotificationList({ pageSize: 100 });
  const item = useMemo(
    () => listQuery.data?.pages.flatMap((page) => page.items).find((n) => n.id === id) ?? null,
    [listQuery.data, id],
  );

  const markRead = useMarkRead();
  const dismiss = useDismissNotification();

  useEffect(() => {
    if (item && !item.read) markRead.mutate(item.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item?.id]);

  const onDismiss = () => {
    dismiss.mutate(id, { onSuccess: () => router.back() });
  };

  const goToSource = () => {
    const actionRoute = item?.actionRoute ?? null;
    if (isValidActionRoute(actionRoute)) {
      router.push(actionRoute as never);
    }
  };

  if (!item) {
    return (
      <AgScreen backgroundColor={nt.background}>
        <NotificationBackHeader title={t('notifications.detailTitle')} />
        <View className="mt-10 items-center">
          <AgText color="muted">
            {listQuery.isLoading ? t('common.loading') : t('notifications.notFound')}
          </AgText>
        </View>
      </AgScreen>
    );
  }

  const Icon = MODULE_ICON[item.module];
  const rt = relativeTimeKey(item.createdAt);

  return (
    <AgScreen scroll backgroundColor={nt.background}>
      <NotificationBackHeader title={t('notifications.detailTitle')} />

      <AgCard className="mt-4 gap-3">
        <View className="flex-row items-center gap-3">
          <View
            className="h-11 w-11 items-center justify-center rounded-full"
            style={{ backgroundColor: `${colors.primary}1A` }}
          >
            <Icon size={22} color={colors.primary} />
          </View>
          <View className="flex-1">
            <AgText variant="caption" color="muted">
              {t(MODULE_LABEL_KEY[item.module])} · {t(rt.key, rt.params)}
            </AgText>
            <AgText variant="headingS" weight="bold">
              {t(item.titleKey, item.payload)}
            </AgText>
          </View>
        </View>

        <AgBadge
          label={t(SEVERITY_LABEL_KEY[item.severity])}
          tone={SEVERITY_TONE[item.severity]}
        />

        <AgText variant="body" color="muted">
          {t(item.messageKey, item.payload)}
        </AgText>
      </AgCard>

      {isValidActionRoute(item.actionRoute) ? (
        <AgButton
          className="mt-4"
          variant="primary"
          title={t('notifications.openSource')}
          leftIcon={<ExternalLink size={18} color={colors.onPrimary} />}
          onPress={goToSource}
        />
      ) : null}

      <AgButton
        className="mt-3"
        variant="ghost"
        title={t('notifications.dismiss')}
        leftIcon={<Trash2 size={18} color={colors.danger} />}
        onPress={onDismiss}
        loading={dismiss.isPending}
      />
    </AgScreen>
  );
}
