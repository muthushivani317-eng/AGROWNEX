import fs from 'node:fs';
import path from 'node:path';

const read = (relative: string) =>
  fs.readFileSync(path.resolve(__dirname, '../../..', relative), 'utf8');

describe('OTP verification screen release contract', () => {
  const otpScreen = read('features/auth/screens/VerifyOtpScreen.tsx');
  const otpInput = read('components/ui/AgOtpInput.tsx');
  const screen = read('components/ui/AgScreen.tsx');
  const appConfig = read('app.config.js');

  it('keeps Verify disabled until exactly six digits and exposes pending state', () => {
    expect(otpScreen).toContain('disabled={code.length !== 6 || !hasConfirmation || verify.isPending || resend.isPending}');
    expect(otpScreen).toContain('loading={verify.isPending}');
    expect(otpScreen).toContain('if (value.length !== 6 || verify.isPending || !hasConfirmation) return;');
  });

  it('surfaces resend failures and locks conflicting actions while pending', () => {
    expect(otpScreen).toContain("authErrorMessage(t, resend.error, 'send')");
    expect(otpScreen).toContain('testID="otp-resend-error"');
    expect(otpScreen).toContain('resend.reset()');
    expect(otpScreen).toContain('disabled={verify.isPending || resend.isPending}');
  });

  it('keeps verification errors visible while leaving the OTP input mounted', () => {
    expect(otpScreen).toContain('<AgOtpInput');
    expect(otpScreen).toContain('error={showError}');
    expect(otpScreen).toContain('verify.reset()');
    expect(otpScreen).toContain('testID="otp-verification-error"');
    expect(otpScreen).not.toContain('if (showError) return null');
  });

  it('preserves resend and deliberate change-number actions', () => {
    expect(otpScreen).toContain('const RESEND_SECONDS = 30;');
    expect(otpScreen).toContain('setCode(\'\');');
    expect(otpScreen).toContain("router.replace('/(auth)/login')");
  });

  it('keeps the resend cooldown accurate after backgrounding the app', () => {
    expect(otpScreen).toContain("import { AppState, StyleSheet, View } from 'react-native';");
    expect(otpScreen).toContain('resendAvailableAt - Date.now()');
    expect(otpScreen).toContain("AppState.addEventListener('change'");
    expect(otpScreen).toContain("if (state === 'active') updateCountdown();");
    expect(otpScreen).toContain('appStateSubscription.remove()');
  });

  it('offers immediate recovery from an expired Firebase confirmation', () => {
    expect(otpScreen).toContain("verify.error?.code === 'auth/session-expired'");
    expect(otpScreen).toContain('const needsNewCode = Boolean(phoneE164) && !hasConfirmation;');
    expect(otpScreen).toContain("t('auth.resendNewCode')");
    expect(otpScreen).toContain('verify.reset()');
  });

  it('uses bounded focus recovery without dismissing the keyboard', () => {
    expect(otpInput).toContain('InteractionManager.runAfterInteractions');
    expect(otpInput).toContain('onPress={focusInput}');
    expect(otpInput).toContain('inputRef.current?.focus()');
    expect(otpInput).toContain('setTimeout(() =>');
    expect(otpInput).toContain('clearTimeout(retryTimer)');
    expect(otpInput).not.toContain('Keyboard.dismiss');
  });

  it('supports operating-system one-time-code suggestions and SMS autofill', () => {
    expect(otpInput).toContain("Platform.OS === 'ios' ? 'oneTimeCode' : undefined");
    expect(otpInput).toContain("Platform.OS === 'android' ? 'sms-otp' : 'one-time-code'");
    expect(otpInput).toContain('importantForAutofill="yes"');
    expect(otpInput).toContain('onChangeText={handleChange}');
    expect(otpInput).toContain('opacity: 1');
    expect(otpInput).toContain('fontSize: 1');
    expect(otpInput).not.toContain('secureTextEntry');
  });

  it('keeps clear space between the code cells and Verify action', () => {
    expect(otpScreen).toContain('<View style={styles.verifyAction}>');
    expect(otpScreen).toContain('verifyAction: { marginTop: 20 }');
    expect(otpScreen).not.toContain('className="mt-6"');
  });

  it('uses Android keyboard-aware scrolling and reproducible adjustResize config', () => {
    expect(screen).toContain('keyboardShouldPersistTaps="handled"');
    expect(screen).toContain("behavior={Platform.OS === 'ios' ? 'padding' : 'height'}");
    expect(appConfig).toContain('softwareKeyboardLayoutMode: "resize"');
  });

  it('does not auto-submit or log the OTP value', () => {
    expect(otpScreen).not.toContain('onComplete={submit}');
    expect(otpScreen).not.toMatch(/console\.(log|info|warn|error)/);
    expect(otpInput).not.toMatch(/console\.(log|info|warn|error)/);
  });
});
