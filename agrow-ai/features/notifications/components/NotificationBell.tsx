import { useRouter } from 'expo-router';
import { Bell } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { StyleSheet, View } from 'react-native';

import { AgPressable, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import { useUnreadCount } from '../hooks/useNotifications';

/** Notification bell + unread badge — the entry point to the Notification Center.
 * Reused in the Home header. */
export function NotificationBell({ light = false }: { light?: boolean }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const router = useRouter();
  const { data: unread = 0 } = useUnreadCount();
  const label =
    unread > 0
      ? t('notifications.bellLabelCount', { count: unread })
      : t('notifications.bellLabel');

  return (
    <AgPressable
      testID="home-notification-bell"
      onPress={() => router.push('/notifications')}
      accessibilityRole="button"
      accessibilityLabel={label}
      hitSlop={6}
      style={[styles.button, { backgroundColor: light ? '#FFFDF8' : colors.card }]}
    >
      <Bell size={25} strokeWidth={2} color={light ? '#173B2B' : colors.text} />
      {unread > 0 ? (
        <View
          testID="home-notification-badge"
          pointerEvents="none"
          style={[styles.badge, { backgroundColor: light ? '#F5B51B' : colors.primary, borderColor: light ? '#F7F4E8' : colors.bg }]}
        >
          <AgText
            variant="caption"
            weight="bold"
            color="onPrimary"
            numberOfLines={1}
            maxFontSizeMultiplier={1}
            style={[styles.badgeText, light && styles.badgeTextLight]}
          >
            {unread > 99 ? '99+' : unread}
          </AgText>
        </View>
      ) : null}
    </AgPressable>
  );
}

const styles = StyleSheet.create({
  button: {
    position: 'relative',
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badge: {
    position: 'absolute',
    top: -3,
    right: -3,
    minWidth: 22,
    height: 22,
    paddingHorizontal: 5,
    borderRadius: 11,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 2,
    elevation: 3,
  },
  badgeText: { fontSize: 11, lineHeight: 14, textAlign: 'center' },
  badgeTextLight: { color: '#173B2B' },
});
