import * as Haptics from 'expo-haptics';
import { type ReactNode } from 'react';
import { Pressable, type PressableProps } from 'react-native';

export interface AgPressableProps extends PressableProps {
  children: ReactNode;
  scaleTo?: number;
  haptic?: boolean;
  className?: string;
}

/**
 * Pressable with a smooth press-in scale and optional haptic tick — the tactile
 * baseline for all tappable surfaces (buttons, cards, list rows, chips).
 */
export function AgPressable({
  children,
  scaleTo = 0.97,
  haptic = true,
  onPressIn,
  onPressOut,
  disabled,
  style,
  ...rest
}: AgPressableProps) {
  return (
    <Pressable
      style={(state) => [
        typeof style === 'function' ? style(state) : style,
        { transform: [{ scale: state.pressed ? scaleTo : 1 }] },
      ]}
      disabled={disabled}
      onPressIn={(e) => {
        if (haptic) Haptics.selectionAsync().catch(() => {});
        onPressIn?.(e);
      }}
      onPressOut={(e) => {
        onPressOut?.(e);
      }}
      {...rest}
    >
      {children}
    </Pressable>
  );
}
