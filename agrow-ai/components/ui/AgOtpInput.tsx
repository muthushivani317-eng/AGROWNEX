import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AppState,
  InteractionManager,
  Platform,
  Pressable,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';

import { cn } from '@/utils/cn';
import { useAppTheme } from '@/hooks/useAppTheme';

import { AgText } from './AgText';

interface AgOtpInputProps {
  value: string;
  onChange: (code: string) => void;
  length?: number;
  autoFocus?: boolean;
  error?: boolean;
  onComplete?: (code: string) => void;
  light?: boolean;
}

/**
 * Segmented one-time-code input. A single hidden TextInput owns the value (so
 * SMS autofill and paste work); the boxes are a visual projection of it.
 */
export function AgOtpInput({
  value,
  onChange,
  length = 6,
  autoFocus = true,
  error = false,
  onComplete,
  light = false,
}: AgOtpInputProps) {
  const { colors } = useAppTheme();
  const inputRef = useRef<TextInput>(null);
  const completedRef = useRef(false);
  const previousErrorRef = useRef(error);
  const restoreAfterBackgroundRef = useRef(false);
  const [focused, setFocused] = useState(false);

  const focusInput = useCallback(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!autoFocus) return;

    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    const interaction = InteractionManager.runAfterInteractions(() => {
      focusInput();
      retryTimer = setTimeout(() => {
        if (!inputRef.current?.isFocused()) focusInput();
      }, 180);
    });

    return () => {
      interaction.cancel();
      if (retryTimer) clearTimeout(retryTimer);
    };
  }, [autoFocus, focusInput]);

  useEffect(() => {
    const subscription = AppState.addEventListener('change', (nextState) => {
      if (nextState === 'active') {
        if (restoreAfterBackgroundRef.current) focusInput();
        restoreAfterBackgroundRef.current = false;
        return;
      }
      restoreAfterBackgroundRef.current = inputRef.current?.isFocused() ?? false;
    });
    return () => subscription.remove();
  }, [focusInput]);

  useEffect(() => {
    if (error && !previousErrorRef.current) focusInput();
    previousErrorRef.current = error;
  }, [error, focusInput]);

  useEffect(() => {
    if (value.length === length) {
      if (!completedRef.current) {
        completedRef.current = true;
        onComplete?.(value);
      }
    } else {
      completedRef.current = false;
    }
  }, [value, length, onComplete]);

  const handleChange = (text: string) => {
    onChange(text.replace(/\D/g, '').slice(0, length));
  };

  const cells = Array.from({ length });
  const activeIndex = Math.min(value.length, length - 1);

  return (
    <Pressable
      testID="otp-input-container"
      onPress={focusInput}
      className="w-full"
      style={styles.root}
      accessibilityRole="none"
    >
      <View
        testID="otp-visual-cells"
        pointerEvents="none"
        accessibilityElementsHidden
        importantForAccessibility="no-hide-descendants"
        className="flex-row justify-between"
        style={styles.cells}
      >
        {cells.map((_, i) => {
          const char = value[i] ?? '';
          const isActive = focused && i === activeIndex;
          const filled = Boolean(char);
          return (
            <View
              key={i}
              testID={`otp-cell-${i}`}
              style={[
                styles.cell,
                {
                  borderColor: error
                    ? light ? '#C83C32' : colors.danger
                    : filled || isActive
                      ? light ? '#176B36' : colors.primary
                      : light ? '#C9C7BD' : colors.border,
                  backgroundColor: light ? '#FFFFFF' : colors.surface,
                },
                isActive && [styles.activeCell, { shadowColor: colors.primary }],
              ]}
              className={cn(
                'h-14 w-12 items-center justify-center rounded-md border',
                filled || isActive ? 'border-primary' : 'border-border',
                error && 'border-danger',
              )}
            >
              <AgText variant="headingM" weight="bold" style={light ? styles.lightDigit : undefined}>
                {filled ? '•' : ''}
              </AgText>
            </View>
          );
        })}
      </View>

      <TextInput
        testID="otp-native-input"
        ref={inputRef}
        value={value}
        onChangeText={handleChange}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        keyboardType="number-pad"
        inputMode="numeric"
        showSoftInputOnFocus
        editable
        textContentType={Platform.OS === 'ios' ? 'oneTimeCode' : undefined}
        autoComplete={Platform.OS === 'android' ? 'sms-otp' : 'one-time-code'}
        importantForAutofill="yes"
        autoCorrect={false}
        autoCapitalize="none"
        maxLength={length}
        style={styles.nativeInput}
        caretHidden
        cursorColor="transparent"
        selectionColor="transparent"
        underlineColorAndroid="transparent"
        accessibilityLabel="One-time password"
        accessibilityHint="Enter the six-digit verification code"
      />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  root: { width: '100%', minHeight: 60 },
  cells: { flexDirection: 'row', justifyContent: 'space-between', gap: 8 },
  cell: {
    flex: 1,
    maxWidth: 52,
    minWidth: 42,
    height: 60,
    borderRadius: 14,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  activeCell: { shadowOpacity: 0.14, shadowRadius: 8, elevation: 2 },
  lightDigit: { color: '#101713' },
  nativeInput: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 60,
    zIndex: 2,
    color: 'transparent',
    backgroundColor: 'transparent',
    // Keep the native input fully present for SMS autofill. Android IMEs may
    // override a transparent foreground while composing an autofilled value,
    // so a 1px glyph size prevents the raw code from appearing over the cells.
    opacity: 1,
    fontSize: 1,
    lineHeight: 1,
    textShadowColor: 'transparent',
    padding: 0,
  },
});
