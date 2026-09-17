import { StyleSheet, View } from 'react-native';

import { useLanguage } from '@/hooks/useLanguage';
import type { SupportedLanguage } from '@/types';
import { cn } from '@/utils/cn';

import { AgPressable } from './ui/AgPressable';
import { AgText } from './ui/AgText';

const OPTIONS: { value: SupportedLanguage; label: string }[] = [
  { value: 'ta', label: 'தமிழ்' },
  { value: 'en', label: 'English' },
];

/** Compact Tamil/English segmented switch. */
export function AgLanguageToggle({ className }: { className?: string }) {
  const { language, setLanguage } = useLanguage();

  return (
    <View
      style={styles.container}
      className={cn(
        'flex-row rounded-full border border-border bg-surface-card p-1',
        className,
      )}
    >
      {OPTIONS.map((opt) => {
        const active = language === opt.value;
        return (
          <AgPressable
            key={opt.value}
            haptic={false}
            onPress={() => setLanguage(opt.value)}
            accessibilityRole="button"
            accessibilityState={{ selected: active }}
            style={styles.option}
            className={cn('rounded-full px-4 py-2', active && 'bg-primary')}
          >
            <AgText
              variant="caption"
              weight="semibold"
              color={active ? 'onPrimary' : 'muted'}
            >
              {opt.label}
            </AgText>
          </AgPressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    padding: 4,
    borderRadius: 999,
    borderWidth: 1,
  },
  option: { minHeight: 38, paddingHorizontal: 16, borderRadius: 999, alignItems: 'center', justifyContent: 'center' },
});
