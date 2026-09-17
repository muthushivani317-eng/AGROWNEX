import { forwardRef, type ReactNode, useCallback, useRef } from 'react';
import { Pressable, StyleSheet, TextInput, View, type StyleProp, type TextInputProps, type TextStyle, type ViewStyle } from 'react-native';

import { useAppTheme } from '@/hooks/useAppTheme';
import { cn } from '@/utils/cn';

import { AgText } from './AgText';

export interface AgInputProps extends TextInputProps {
  /** Force the high-contrast light field treatment used by fixed-light flows. */
  light?: boolean;
  label?: string;
  required?: boolean;
  error?: string;
  hint?: string;
  leftAccessory?: ReactNode;
  rightAccessory?: ReactNode;
  containerClassName?: string;
  fieldStyle?: ViewStyle;
  fieldBorderColor?: string;
  fieldBackgroundColor?: string;
  focusBorderColor?: string;
  labelStyle?: StyleProp<TextStyle>;
  hintStyle?: StyleProp<TextStyle>;
}

/**
 * Labelled text field with focus ring, error state and optional adornments.
 * Works standalone or as the render target of a React Hook Form `Controller`.
 */
export const AgInput = forwardRef<TextInput, AgInputProps>(function AgInput(
  {
    label,
    light = false,
    required,
    error,
    hint,
    leftAccessory,
    rightAccessory,
    containerClassName,
    fieldStyle,
    fieldBorderColor,
    fieldBackgroundColor,
    focusBorderColor,
    labelStyle,
    hintStyle,
    onFocus,
    onBlur,
    className,
    style,
    ...rest
  },
  ref,
) {
  const { colors } = useAppTheme();
  const palette = light
    ? {
        text: '#173B2B',
        muted: '#5F6F67',
        surface: '#FFFDF8',
        border: '#D8D1BD',
        primary: '#176B36',
        danger: '#B43A32',
      }
    : {
        text: colors.text,
        muted: colors.textMuted,
        surface: colors.surface,
        border: colors.border,
        primary: colors.primary,
        danger: colors.danger,
      };
  const inputRef = useRef<TextInput>(null);
  const fieldRef = useRef<View>(null);

  const setInputRef = useCallback(
    (node: TextInput | null) => {
      inputRef.current = node;
      if (typeof ref === 'function') ref(node);
      else if (ref) ref.current = node;
    },
    [ref],
  );

  const focusInput = useCallback(() => inputRef.current?.focus(), []);

  return (
    <View
      className={cn('w-full', containerClassName)}
      style={containerClassName ? undefined : styles.container}
    >
      {label ? (
        <AgText variant="label" weight="semibold" color="default" className="mb-2" style={[styles.label, light && { color: palette.text }, labelStyle]}>
          {label}{required ? <AgText color="danger"> *</AgText> : null}
        </AgText>
      ) : null}

      <Pressable
        ref={fieldRef}
        testID={rest.testID ? `${rest.testID}-container` : undefined}
        onPress={focusInput}
        style={[
          styles.field,
          {
            borderColor: error ? palette.danger : (fieldBorderColor ?? palette.border),
            backgroundColor: fieldBackgroundColor ?? palette.surface,
          },
          fieldStyle,
        ]}
        accessibilityRole="none"
      >
        {leftAccessory ? <View pointerEvents="none" style={styles.leftAccessory}>{leftAccessory}</View> : null}
        <TextInput
          ref={setInputRef}
          className={className}
          placeholderTextColor={palette.muted}
          selectionColor={palette.primary}
          cursorColor={palette.primary}
          style={[styles.input, { color: palette.text, backgroundColor: palette.surface }, style]}
          onFocus={(e) => {
            fieldRef.current?.setNativeProps({
              style: { borderColor: focusBorderColor ?? palette.primary, borderWidth: 2 },
            });
            onFocus?.(e);
          }}
          onBlur={(e) => {
            fieldRef.current?.setNativeProps({
              style: { borderColor: error ? palette.danger : (fieldBorderColor ?? palette.border), borderWidth: 1.5 },
            });
            onBlur?.(e);
          }}
          {...rest}
        />
        {rightAccessory ? <View pointerEvents="none" style={styles.rightAccessory}>{rightAccessory}</View> : null}
      </Pressable>

      {error ? (
        <AgText variant="caption" color="danger" className="mt-1.5">
          {error}
        </AgText>
      ) : hint ? (
        <AgText variant="caption" color="disabled" className="mt-1.5" style={[light && { color: palette.muted }, hintStyle]}>
          {hint}
        </AgText>
      ) : null}
    </View>
  );
});

const styles = StyleSheet.create({
  container: { width: '100%' },
  label: { marginBottom: 8 },
  field: {
    minHeight: 58,
    paddingHorizontal: 16,
    borderRadius: 14,
    borderWidth: 1.5,
    flexDirection: 'row',
    alignItems: 'center',
  },
  leftAccessory: { marginRight: 8 },
  rightAccessory: { marginLeft: 8 },
  input: {
    flex: 1,
    alignSelf: 'stretch',
    minHeight: 56,
    paddingVertical: 0,
    opacity: 1,
    fontSize: 17,
    lineHeight: 24,
  },
});
