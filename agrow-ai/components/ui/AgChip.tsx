import { type ReactNode } from 'react';
import { View } from 'react-native';

import { useAppTheme } from '@/hooks/useAppTheme';
import { cn } from '@/utils/cn';

import { AgPressable } from './AgPressable';
import { AgText } from './AgText';

interface AgChipProps {
  label: string;
  selected?: boolean;
  onPress?: () => void;
  leftIcon?: ReactNode;
  className?: string;
  light?: boolean;
}

/** Selectable pill — crop selection, filters, AI quick replies. */
export function AgChip({ label, selected, onPress, leftIcon, className, light = false }: AgChipProps) {
  const { colors } = useAppTheme();
  return (
    <AgPressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      className={cn(
        'min-h-12 flex-row items-center gap-1.5 rounded-full border px-4 py-2.5',
        selected ? 'border-primary' : 'border-border',
        className,
      )}
      style={({ pressed }) => ({
        minHeight: 48,
        paddingHorizontal: 16,
        paddingVertical: 10,
        borderRadius: 999,
        borderWidth: 1,
        borderColor: selected ? (light ? '#176B36' : colors.primary) : (light ? '#D9D6C8' : colors.border),
        backgroundColor: selected ? (light ? '#E8F3E5' : colors.primary) : (light ? '#FFFFFF' : colors.surface),
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        opacity: pressed ? 0.82 : 1,
      })}
    >
      {leftIcon ? <View>{leftIcon}</View> : null}
      <AgText
        variant="bodySmall"
        weight={selected ? 'semibold' : 'regular'}
        color={selected ? 'onPrimary' : 'default'}
        style={light ? { color: '#101713' } : undefined}
      >
        {label}
      </AgText>
    </AgPressable>
  );
}
