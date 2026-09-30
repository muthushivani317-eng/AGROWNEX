import * as Haptics from 'expo-haptics';
import { useState, type ReactNode } from 'react';
import { Pressable, StyleSheet, type PressableProps, type PressableStateCallbackType } from 'react-native';

export interface AgPressableProps extends PressableProps {
  children: ReactNode;
  scaleTo?: number;
  haptic?: boolean;
  className?: string;
}

/**
 * Pressable with a smooth press-in scale and optional haptic tick — the tactile
 * baseline for all tappable surfaces (buttons, cards, list rows, chips).
 *
 * The style is resolved here and passed to Pressable as a plain style (not a
 * `(state) => style` function): NativeWind's Pressable interop drops function
 * styles, which left `style=`-styled buttons, chips and step circles with no
 * background or border on device.
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
  const [pressed, setPressed] = useState(false);
  const state = { pressed, hovered: false } as PressableStateCallbackType;
  const resolved = typeof style === 'function' ? style(state) : style;
  // NativeWind's Pressable interop can discard nested style arrays on Android.
  // Flatten to the plain object promised by this component's contract so
  // borders, row direction and button surfaces render consistently on device.
  const nativeStyle = StyleSheet.flatten([
    resolved,
    pressed && scaleTo !== 1 ? { transform: [{ scale: scaleTo }] } : null,
  ]);

  return (
    <Pressable
      style={nativeStyle}
      disabled={disabled}
      onPressIn={(e) => {
        setPressed(true);
        if (haptic) Haptics.selectionAsync().catch(() => {});
        onPressIn?.(e);
      }}
      onPressOut={(e) => {
        setPressed(false);
        onPressOut?.(e);
      }}
      {...rest}
    >
      {children}
    </Pressable>
  );
}
