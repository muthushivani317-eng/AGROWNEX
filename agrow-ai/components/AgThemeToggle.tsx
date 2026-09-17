import { Moon, Smartphone, Sun, type LucideIcon } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { useAppTheme } from '@/hooks/useAppTheme';
import { useThemeStore, type ThemePreference } from '@/stores/themeStore';
import { cn } from '@/utils/cn';

import { AgPressable } from './ui/AgPressable';
import { AgText } from './ui/AgText';

const OPTIONS: { value: ThemePreference; labelKey: string; icon: LucideIcon }[] = [
  { value: 'system', labelKey: 'settings.themeAuto', icon: Smartphone },
  { value: 'light', labelKey: 'settings.themeLight', icon: Sun },
  { value: 'dark', labelKey: 'settings.themeDark', icon: Moon },
];

/** Three-way theme preference switch (Auto / Light / Dark). */
export function AgThemeToggle() {
  const { t } = useTranslation();
  const preference = useThemeStore((s) => s.preference);
  const setPreference = useThemeStore((s) => s.setPreference);
  const { colors } = useAppTheme();

  return (
    <View className="flex-row rounded-md border border-border bg-surface-card p-1">
      {OPTIONS.map(({ value, labelKey, icon: Icon }) => {
        const active = preference === value;
        return (
          <AgPressable
            key={value}
            haptic={false}
            onPress={() => setPreference(value)}
            accessibilityRole="button"
            accessibilityState={{ selected: active }}
            className={cn(
              'min-h-12 flex-1 flex-row items-center justify-center gap-1.5 rounded-sm py-2',
              active && 'bg-primary',
            )}
          >
            <Icon size={16} color={active ? colors.onPrimary : colors.textMuted} />
            <AgText
              variant="caption"
              weight="semibold"
              color={active ? 'onPrimary' : 'muted'}
            >
              {t(labelKey)}
            </AgText>
          </AgPressable>
        );
      })}
    </View>
  );
}
