import { useRouter } from 'expo-router';
import { ArrowRight, Landmark } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { StyleSheet, View } from 'react-native';

import { AgPressable, AgSkeleton, AgText } from '@/components/ui';
import { MODULE_ICON } from '@/features/notifications/components/moduleIcon';
import { useNotificationList } from '@/features/notifications/hooks/useNotifications';
import { isValidActionRoute, selectTopPriority } from '@/features/notifications/utils/priority';
import { notificationDisplayPayload } from '@/features/notifications/utils/displayPayload';

export function PriorityHeroCard() {
  const { t } = useTranslation();
  const router = useRouter();
  const query = useNotificationList({ pageSize: 5, unread: true });
  const items = query.data?.pages.flatMap((page) => page.items) ?? [];
  const top = selectTopPriority(items);
  const displayPayload = notificationDisplayPayload(top?.payload ?? {});

  if (query.isLoading) return <AgSkeleton style={styles.skeleton} />;

  const Icon = top ? MODULE_ICON[top.module] : Landmark;
  const actionable = top ? isValidActionRoute(top.actionRoute) : true;
  const isUnverifiedSchemeClaim = top?.module === 'schemes';
  const title = top && !isUnverifiedSchemeClaim
    ? t(top.titleKey, displayPayload)
    : t('home.priorityFallbackTitle');
  const message = top && !isUnverifiedSchemeClaim
    ? t(top.messageKey, displayPayload)
    : t('home.priorityFallbackMessage');
  const destination = top?.actionRoute ?? '/schemes';

  const card = (
    <View
      style={[
        styles.card,
        {
          backgroundColor: '#165B33',
          borderColor: '#0F4828',
        },
      ]}
    >
      <View style={styles.iconTile}>
        <Icon size={34} color="#FFFFFF" strokeWidth={1.7} />
      </View>
      <View style={styles.copy}>
        <AgText variant="caption" weight="bold" style={styles.eyebrow}>{t('home.todaysPriority')}</AgText>
        <AgText variant="headingS" weight="bold" numberOfLines={3} style={styles.title}>{title}</AgText>
        <AgText variant="bodySmall" numberOfLines={3} style={styles.message}>{message}</AgText>
        {actionable ? (
          <View style={styles.actionRow}>
            <AgText variant="bodySmall" weight="bold" style={styles.actionText}>{t('common.viewDetails')}</AgText>
            <ArrowRight size={17} color="#F5B51B" />
          </View>
        ) : null}
      </View>
    </View>
  );

  if (!actionable) return card;
  return (
    <AgPressable
      onPress={() => router.push(destination as never)}
      accessibilityRole="button"
      accessibilityLabel={title}
    >
      {card}
    </AgPressable>
  );
}

const styles = StyleSheet.create({
  skeleton: { width: '100%', height: 166, borderRadius: 18 },
  card: {
    minHeight: 166, borderRadius: 18, borderWidth: 1,
    padding: 18, flexDirection: 'row', alignItems: 'center', gap: 15,
    shadowColor: '#173B2B', shadowOpacity: 0.16, shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 }, elevation: 4,
  },
  iconTile: { width: 54, height: 54, borderRadius: 18, borderWidth: 1, borderColor: '#7FAD8F', alignItems: 'center', justifyContent: 'center' },
  copy: { flex: 1, minWidth: 0 },
  eyebrow: { color: '#F5B51B', letterSpacing: 0.5 },
  title: { marginTop: 5, color: '#FFFFFF', lineHeight: 27 },
  message: { marginTop: 5, color: '#E4F0E8', lineHeight: 20 },
  actionRow: { marginTop: 10, minHeight: 30, flexDirection: 'row', alignItems: 'center', gap: 7 },
  actionText: { color: '#F5B51B' },
});
