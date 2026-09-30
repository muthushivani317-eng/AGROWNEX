import type { Href } from 'expo-router';
import { useRouter } from 'expo-router';
import {
  BarChart3,
  Bell,
  Building2,
  ChevronDown,
  ChevronRight,
  ClipboardCheck,
  LayoutDashboard,
  Settings,
  ShieldCheck,
  ShoppingBasket,
  Sprout,
  Users,
} from 'lucide-react-native';
import { useState } from 'react';
import { View } from 'react-native';

import { AgCard, AgPressable, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

type NavItem = {
  label: string;
  route?: Href;
  planned?: boolean;
};

type NavGroup = {
  label: string;
  icon: typeof Users;
  items?: NavItem[];
  route?: Href;
  planned?: boolean;
};

const GROUPS: NavGroup[] = [
  { label: 'Dashboard', icon: LayoutDashboard, route: '/admin' },
  {
    label: 'Farmers',
    icon: Users,
    items: [
      { label: 'All Farmers', route: '/admin/farmers' },
      { label: 'New Farmers', route: '/admin/farmers?view=new' },
      { label: 'Farmer Map', planned: true },
      { label: 'Farmer Analytics', route: '/admin/analytics' },
    ],
  },
  {
    label: 'Sell My Produce',
    icon: ShoppingBasket,
    items: [
      { label: 'New Listings', route: '/admin/procurement?view=new' },
      { label: 'All Listings', route: '/admin/procurement' },
      { label: 'Buyer Search', route: '/admin/procurement?view=buyer-search' },
      { label: 'Negotiations', route: '/admin/procurement?view=negotiations' },
      { label: 'Completed Deals', route: '/admin/procurement?view=completed' },
      { label: 'Produce Analytics', route: '/admin/analytics' },
    ],
  },
  {
    label: 'Farms',
    icon: Sprout,
    items: [
      { label: 'All Farms', planned: true },
      { label: 'Crops', route: '/admin/crop-intelligence' as Href },
      { label: 'Geographic Distribution', route: '/admin/crop-intelligence' as Href },
    ],
  },
  {
    label: 'App Analytics',
    icon: BarChart3,
    items: [
      { label: 'Active Farmers', route: '/admin/analytics' },
      { label: 'Feature Usage', route: '/admin/ai' },
      { label: 'Retention', planned: true },
      { label: 'Growth', route: '/admin/analytics' },
    ],
  },
  {
    label: 'Operations',
    icon: ClipboardCheck,
    items: [
      { label: 'Disease Activity', route: '/admin/ai' },
      { label: 'Weather', planned: true },
      { label: 'Market Prices', planned: true },
      { label: 'System Health', route: '/admin/ai' },
    ],
  },
  { label: 'Notifications', icon: Bell, route: '/admin/broadcast' },
  {
    label: 'Buyers',
    icon: Building2,
    items: [
      { label: 'Buyer Database', planned: true },
      { label: 'Requirements', route: '/admin/procurement?view=buyer-search' },
      { label: 'Transactions', route: '/admin/procurement?view=completed' },
    ],
  },
  { label: 'Reports', icon: BarChart3, route: '/admin/analytics' },
  { label: 'Team & Permissions', icon: ShieldCheck, route: '/admin/audit' },
  { label: 'Settings', icon: Settings, planned: true },
];

function NavigationRow({ item }: { item: NavItem }) {
  const router = useRouter();
  const { colors } = useAppTheme();
  const disabled = item.planned || !item.route;

  return (
    <AgPressable
      onPress={() => item.route && router.push(item.route)}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={item.label}
      className="flex-row items-center justify-between rounded-xl px-3 py-3"
    >
      <View className="flex-row items-center gap-3">
        <View className="h-1.5 w-1.5 rounded-full bg-primary" />
        <AgText variant="bodySmall" color={disabled ? 'muted' : 'default'}>
          {item.label}
        </AgText>
      </View>
      {item.planned ? (
        <View className="rounded-full bg-surface-muted px-2 py-1">
          <AgText variant="caption" color="muted">Planned</AgText>
        </View>
      ) : (
        <ChevronRight size={16} color={colors.textMuted} />
      )}
    </AgPressable>
  );
}

/** Mobile/tablet navigation tree for the internal AgrowAI operator console. */
export function AdminConsoleNavigation() {
  const router = useRouter();
  const { colors } = useAppTheme();
  const [open, setOpen] = useState<Record<string, boolean>>({
    Farmers: true,
    'Sell My Produce': true,
  });

  return (
    <AgCard className="gap-1 p-2">
      <View className="px-3 pb-2 pt-3">
        <AgText variant="caption" weight="bold" color="muted">AGROWNEX ADMIN</AgText>
        <AgText variant="headingS" weight="bold">Operations console</AgText>
      </View>

      {GROUPS.map(({ label, icon: Icon, items, route, planned }) => {
        const expanded = Boolean(open[label]);
        return (
          <View key={label}>
            <AgPressable
              onPress={() => {
                if (items) setOpen((current) => ({ ...current, [label]: !expanded }));
                else if (route) router.push(route);
              }}
              disabled={planned || (!items && !route)}
              accessibilityRole="button"
              accessibilityLabel={label}
              className="flex-row items-center justify-between rounded-xl px-3 py-3"
            >
              <View className="flex-row items-center gap-3">
                <View className="h-9 w-9 items-center justify-center rounded-xl bg-primary/10">
                  <Icon size={18} color={colors.primary} />
                </View>
                <AgText variant="bodySmall" weight="semibold">{label}</AgText>
              </View>
              {items ? (
                expanded
                  ? <ChevronDown size={18} color={colors.textMuted} />
                  : <ChevronRight size={18} color={colors.textMuted} />
              ) : route ? (
                <ChevronRight size={18} color={colors.textMuted} />
              ) : (
                <AgText variant="caption" color="muted">Planned</AgText>
              )}
            </AgPressable>
            {items && expanded ? (
              <View className="ml-9 border-l border-border pl-2">
                {items.map((item) => <NavigationRow key={item.label} item={item} />)}
              </View>
            ) : null}
          </View>
        );
      })}
    </AgCard>
  );
}
