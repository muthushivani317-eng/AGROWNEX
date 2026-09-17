import { type ReactNode } from 'react';
import { ActivityIndicator, Pressable, View, type ViewStyle } from 'react-native';

import { useAppTheme } from '@/hooks/useAppTheme';

import { AgText } from './AgText';

type Variant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success';
type Size = 'sm' | 'md' | 'lg';

export interface AgButtonProps {
  title: string;
  onPress?: () => void;
  variant?: Variant;
  size?: Size;
  disabled?: boolean;
  loading?: boolean;
  fullWidth?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  className?: string;
  accessibilityLabel?: string;
  /** Opt-in light surface treatment for screens with a fixed light design. */
  light?: boolean;
}

const variantText: Record<Variant, 'onPrimary' | 'default' | 'primary'> = {
  primary: 'onPrimary',
  secondary: 'default',
  outline: 'primary',
  ghost: 'primary',
  danger: 'onPrimary',
  success: 'onPrimary',
};

export function AgButton({
  title,
  onPress,
  variant = 'primary',
  size = 'md',
  disabled,
  loading,
  fullWidth = true,
  leftIcon,
  rightIcon,
  className,
  accessibilityLabel,
  light = false,
}: AgButtonProps) {
  const { colors } = useAppTheme();
  const isDisabled = disabled || loading;
  const visuallyDisabled = disabled && !loading;
  const spinnerColor =
    variant === 'primary' || variant === 'danger' || variant === 'success'
      ? colors.onPrimary
      : colors.primary;
  const nativeStyle: ViewStyle = {
    minHeight: size === 'lg' ? 64 : size === 'md' ? 56 : 48,
    width: fullWidth ? '100%' : undefined,
    paddingHorizontal: size === 'lg' ? 24 : size === 'md' ? 20 : 16,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    backgroundColor: light
      ? visuallyDisabled
        ? '#ECE9DF'
        : variant === 'primary'
          ? '#F2B632'
          : variant === 'danger'
            ? '#DC2626'
            : variant === 'success'
              ? '#176B36'
              : variant === 'secondary'
                ? '#FFFFFF'
                : 'transparent'
      :
      visuallyDisabled
        ? colors.card
        : variant === 'primary'
        ? colors.primary
        : variant === 'danger'
          ? colors.danger
          : variant === 'success'
            ? colors.success
            : variant === 'secondary'
              ? colors.card
              : 'transparent',
    borderWidth: visuallyDisabled || variant === 'outline' || variant === 'secondary' ? 1 : 0,
    borderColor: light
      ? visuallyDisabled
        ? '#D9D6C8'
        : variant === 'outline'
          ? '#176B36'
          : '#D9D6C8'
      : visuallyDisabled ? colors.border : variant === 'outline' ? colors.primary : colors.border,
    opacity: 1,
  };

  return (
    <View
      className={className}
      style={nativeStyle}
    >
      <Pressable
        onPress={onPress}
        disabled={isDisabled}
        accessibilityRole="button"
        accessibilityState={{ disabled: isDisabled, busy: loading }}
        accessibilityLabel={accessibilityLabel ?? title}
        style={({ pressed }) => ({
          width: '100%',
          minHeight: nativeStyle.minHeight,
          alignItems: 'center',
          justifyContent: 'center',
          transform: [{ scale: pressed ? 0.98 : 1 }],
        })}
      >
        {loading ? (
          <ActivityIndicator color={spinnerColor} />
        ) : (
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            {leftIcon}
            <AgText
              weight="semibold"
              variant={size === 'lg' ? 'bodyLarge' : 'body'}
              color={visuallyDisabled ? 'muted' : variantText[variant]}
              style={light ? { color: visuallyDisabled ? '#7A817C' : variant === 'danger' || variant === 'success' ? '#FFFFFF' : '#101713' } : undefined}
            >
              {title}
            </AgText>
            {rightIcon}
          </View>
        )}
      </Pressable>
    </View>
  );
}
