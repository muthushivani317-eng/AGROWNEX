import { type ReactNode } from 'react';
import { View, type ViewProps, type ViewStyle } from 'react-native';

import { cn } from '@/utils/cn';

type Variant = 'default' | 'elevated' | 'outlined' | 'compact';

export interface AgCardProps extends ViewProps {
  children: ReactNode;
  variant?: Variant;
  className?: string;
}

const variantClass: Record<Variant, string> = {
  default: 'bg-surface-card border border-border p-4',
  elevated: 'bg-surface-card p-4 shadow-md shadow-black/10',
  outlined: 'bg-transparent border border-border p-4',
  compact: 'bg-surface-card border border-border p-3',
};

const baseStyle: ViewStyle = {
  borderRadius: 20,
  padding: 16,
  borderWidth: 1,
};

/** Rounded container with the standard 24dp card radius (docs/DESIGN_SYSTEM.md). */
export function AgCard({
  children,
  variant = 'default',
  className,
  ...rest
}: AgCardProps) {
  return (
    <View
      {...rest}
      className={cn('rounded-card', variantClass[variant], className)}
      style={[
        baseStyle,
        variant === 'compact' && { padding: 12 },
        variant === 'outlined' && { backgroundColor: 'transparent' },
        variant === 'elevated' && {
          elevation: 3,
          shadowColor: '#102A1B',
          shadowOpacity: 0.1,
          shadowRadius: 8,
          shadowOffset: { width: 0, height: 3 },
        },
        rest.style,
      ]}
    >
      {children}
    </View>
  );
}
