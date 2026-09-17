import { Tabs } from 'expo-router';
import {
  Home,
  MessageCircle,
  Sprout,
  TrendingUp,
  User,
  type LucideIcon,
} from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { Platform, type ColorValue } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useAppTheme } from '@/hooks/useAppTheme';

const tabIcon =
  (Icon: LucideIcon) =>
  ({ color, size }: { color: ColorValue; size: number }) => (
    <Icon color={color as string} size={size} />
  );

export default function TabsLayout() {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const insets = useSafeAreaInsets();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: '#FFFFFF',
        tabBarInactiveTintColor: '#DCEADF',
        tabBarActiveBackgroundColor: 'rgba(255,255,255,0.16)',
        tabBarStyle: {
          backgroundColor: colors.primaryDark,
          borderTopColor: 'transparent',
          borderTopWidth: 0,
          borderTopLeftRadius: 28,
          borderTopRightRadius: 28,
          height: Platform.OS === 'ios' ? 94 : 68 + insets.bottom,
          paddingTop: 8,
          paddingBottom: Platform.OS === 'ios' ? 28 : Math.max(insets.bottom, 8),
          overflow: 'hidden',
          elevation: 14,
          shadowColor: '#0B2C16',
          shadowOpacity: 0.24,
          shadowRadius: 14,
          shadowOffset: { width: 0, height: -4 },
        },
        tabBarItemStyle: { borderRadius: 22, marginHorizontal: 3, paddingVertical: 2 },
        tabBarIconStyle: { marginTop: 1 },
        tabBarLabelStyle: { fontFamily: 'Inter_600SemiBold', fontSize: 11, lineHeight: 14, marginTop: 1 },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{ title: t('tabs.home'), tabBarIcon: tabIcon(Home) }}
      />
      <Tabs.Screen
        name="ai"
        options={{ title: t('tabs.ai'), tabBarIcon: tabIcon(MessageCircle) }}
      />
      <Tabs.Screen
        name="farm"
        options={{ title: t('tabs.farm'), tabBarIcon: tabIcon(Sprout) }}
      />
      <Tabs.Screen
        name="market"
        options={{ title: t('tabs.market'), tabBarIcon: tabIcon(TrendingUp) }}
      />
      <Tabs.Screen
        name="profile"
        options={{ title: t('tabs.profile'), tabBarIcon: tabIcon(User) }}
      />
    </Tabs>
  );
}
