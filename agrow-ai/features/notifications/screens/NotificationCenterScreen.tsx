import { useRouter } from 'expo-router';
import { ArrowLeft, BellRing, CheckCheck, ShieldCheck, Settings2 } from 'lucide-react-native';
import { useCallback, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, StyleSheet, View } from 'react-native';

import { AgPressable, AgScreen, AgText } from '@/components/ui';

import { NotificationFilters } from '../components/NotificationFilters';
import { NotificationListView } from '../components/NotificationListView';
import { useMarkAllRead, useMarkRead, useNotificationList } from '../hooks/useNotifications';
import { useNotificationSync } from '../hooks/useNotificationSync';
import type { NotificationItem, NotificationModuleKey, Severity } from '../types';
import { notificationTheme as nt } from '../notificationTheme';

/** Existing notification center, visually redesigned without changing its data or mutations. */
export function NotificationCenterScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  useNotificationSync();

  const [module, setModule] = useState<NotificationModuleKey | null>(null);
  const [severity, setSeverity] = useState<Severity | null>(null);
  const refreshLock = useRef(false);
  const [refreshing, setRefreshing] = useState(false);

  // Load the canonical feed once; filter/count only the real rows currently loaded.
  const query = useNotificationList({ pageSize: 50 });
  const markRead = useMarkRead();
  const markAllRead = useMarkAllRead();
  const allItems = useMemo(() => query.data?.pages.flatMap((page) => page.items) ?? [], [query.data]);
  const hasUnread = useMemo(() => allItems.some((item) => !item.read), [allItems]);
  const counts = useMemo(() => ({
    all: allItems.length,
    info: allItems.filter((item) => item.severity === 'info').length,
    warning: allItems.filter((item) => item.severity === 'warning').length,
    critical: allItems.filter((item) => item.severity === 'critical').length,
  }), [allItems]);
  const items = useMemo(
    () => allItems.filter((item) => (!module || item.module === module) && (!severity || item.severity === severity)),
    [allItems, module, severity],
  );
  const hasSchemeNotifications = allItems.some((item) => item.module === 'schemes');
  const cached = query.data?.pages.some((page) => page.cached) ?? false;

  const refresh = useCallback(async () => {
    if (refreshLock.current) return;
    refreshLock.current = true;
    setRefreshing(true);
    try {
      await query.refetch();
    } finally {
      refreshLock.current = false;
      setRefreshing(false);
    }
  }, [query]);

  const openItem = useCallback((item: NotificationItem) => {
    if (!item.read) markRead.mutate(item.id, {
      onError: () => Alert.alert(t('common.error'), t('notifications.actionFailed')),
    });
    router.push({ pathname: '/notifications/[id]', params: { id: item.id } });
  }, [markRead, router, t]);

  const header = (
    <View style={styles.header}>
      <View style={styles.topBar}>
        <AgPressable onPress={() => router.back()} accessibilityRole="button" accessibilityLabel={t('common.back')} style={styles.iconButton}>
          <ArrowLeft size={25} color={nt.ink} />
        </AgPressable>
        <View style={styles.brandIcon}><BellRing size={24} color={nt.primary} /></View>
        <View style={styles.titleRow} accessibilityLabel={t('notifications.title')}>
          <AgText variant="headingL" weight="bold" style={styles.primaryText}>{t('notifications.title')}</AgText>
        </View>
        <AgPressable onPress={() => router.push('/notifications/preferences')} accessibilityRole="button" accessibilityLabel={t('notifications.preferences')} style={styles.iconButton}>
          <Settings2 size={22} color={nt.ink} />
        </AgPressable>
      </View>

      <AgPressable
        onPress={() => markAllRead.mutate(undefined, {
          onError: () => Alert.alert(t('common.error'), t('notifications.actionFailed')),
        })}
        disabled={!hasUnread || markAllRead.isPending}
        accessibilityRole="button"
        accessibilityLabel={t('notifications.markAllRead')}
        accessibilityState={{ disabled: !hasUnread || markAllRead.isPending, busy: markAllRead.isPending }}
        style={[styles.readAll, !hasUnread && styles.disabled]}
      >
        <CheckCheck size={21} color={hasUnread ? nt.primary : nt.muted} />
        <AgText variant="bodySmall" weight="semibold" style={{ color: hasUnread ? nt.primary : nt.muted }}>{hasUnread ? t('notifications.markAllReadShort') : t('notifications.allRead')}</AgText>
      </AgPressable>

      <AgText variant="body" style={styles.secondaryText}>{t('notifications.subtitle')}</AgText>
      {cached ? <AgText accessibilityRole="alert" variant="bodySmall" style={styles.cachedText}>{t('notifications.cachedNotice')}</AgText> : null}
      <NotificationFilters module={module} severity={severity} counts={counts} onModule={setModule} onSeverity={setSeverity} />
    </View>
  );

  const footer = hasSchemeNotifications ? (
    <View style={styles.safetyCard}>
      <View style={styles.safetyIcon}><ShieldCheck size={25} color={nt.primary} /></View>
      <View style={styles.safetyCopy}>
        <AgText variant="body" weight="semibold" style={styles.greenText}>{t('notifications.schemeSafetyTitle')}</AgText>
        <AgText variant="bodySmall" style={styles.primaryText}>{t('notifications.schemeSafetyMessage')}</AgText>
      </View>
    </View>
  ) : undefined;

  const filtered = module !== null || severity !== null;
  return (
    <AgScreen padded={false} backgroundColor={nt.background}>
      <View style={styles.screenBody}>
        <NotificationListView
          items={query.isLoading || query.isError ? [] : items}
          isLoading={query.isLoading}
          isError={query.isError}
          isRefetching={refreshing || query.isRefetching}
          isFetchingNextPage={query.isFetchingNextPage}
          onRefresh={() => void refresh()}
          onRetry={() => void refresh()}
          onEndReached={() => { if (query.hasNextPage && !query.isFetchingNextPage) void query.fetchNextPage(); }}
          onPressItem={openItem}
          header={header}
          footer={footer}
          emptyTitle={filtered ? t('notifications.noFilterResultsTitle') : t('notifications.emptyTitle')}
          emptyMessage={filtered ? t('notifications.noFilterResultsMessage') : t('notifications.emptyMessage')}
        />
      </View>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  screenBody: { flex: 1, paddingHorizontal: 20 },
  header: { gap: 16, paddingTop: 16, paddingBottom: 8 },
  topBar: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  iconButton: { width: 48, height: 48, alignItems: 'center', justifyContent: 'center', borderRadius: 18, borderWidth: 1, borderColor: nt.border, backgroundColor: nt.surface },
  brandIcon: { width: 48, height: 48, alignItems: 'center', justifyContent: 'center', borderRadius: 16, backgroundColor: nt.primarySoft },
  titleRow: { flex: 1 },
  primaryText: { color: nt.ink },
  secondaryText: { color: nt.muted },
  cachedText: { color: '#8A5A00' },
  greenText: { color: nt.primary },
  readAll: { minHeight: 46, alignSelf: 'flex-start', flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 14, borderRadius: 16, backgroundColor: nt.primarySoft },
  disabled: { opacity: 0.55 },
  safetyCard: { flexDirection: 'row', alignItems: 'center', gap: 13, marginTop: 8, padding: 17, borderRadius: 22, borderWidth: 1, borderColor: nt.border, backgroundColor: nt.primarySoft },
  safetyIcon: { width: 48, height: 48, alignItems: 'center', justifyContent: 'center', borderRadius: 16, backgroundColor: nt.surface },
  safetyCopy: { flex: 1, gap: 4 },
});
