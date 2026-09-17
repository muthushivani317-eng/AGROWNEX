import fs from 'node:fs';
import path from 'node:path';

const read = (relative: string) =>
  fs.readFileSync(path.resolve(__dirname, '../../..', relative), 'utf8');

describe('phone input Android keyboard contract', () => {
  const input = read('components/ui/AgInput.tsx');
  const login = read('features/auth/screens/LoginScreen.tsx');
  const screen = read('components/ui/AgScreen.tsx');
  const manifest = read('android/app/src/main/AndroidManifest.xml');

  it('renders a real visible native TextInput with explicit Android IME props', () => {
    expect(input).toContain('<TextInput');
    expect(login).toContain('editable');
    expect(login).toContain('showSoftInputOnFocus');
    expect(login).toContain('keyboardType="phone-pad"');
    expect(login).toContain('inputMode="tel"');
    expect(login).toContain('testID="phone-number-input"');
  });

  it('makes the complete field and country-code area focus the native input', () => {
    expect(input).toContain('<Pressable');
    expect(input).toContain('onPress={focusInput}');
    expect(input).toContain('inputRef.current?.focus()');
    expect(input).toContain('pointerEvents="none"');
  });

  it('does not rerender the TextInput when focus changes', () => {
    expect(input).not.toContain('useState(false)');
    expect(input).toContain('fieldRef.current?.setNativeProps');
    expect(input).not.toContain('Keyboard.dismiss');
    expect(login).not.toContain('Keyboard.dismiss');
  });

  it('keeps input enabled after a recoverable Firebase error and refocuses it', () => {
    expect(login).not.toContain('editable={!sendOtp.isPending}');
    expect(login).toContain('if (sendOtp.isError) phoneInputRef.current?.focus();');
    expect(login).toContain('testID="otp-send-error"');
  });

  it('gates Send OTP on validated form state', () => {
    expect(login).toContain('disabled={!formState.isValid || sendOtp.isPending}');
    expect(login).toContain('sanitizeIndianPhoneInput(text)');
  });

  it('keeps the layout resize-safe and allows taps while the keyboard is open', () => {
    expect(screen).toContain('keyboardShouldPersistTaps="handled"');
    expect(screen).toContain("behavior={Platform.OS === 'ios' ? 'padding' : 'height'}");
    expect(manifest).toContain('android:windowSoftInputMode="adjustResize"');
  });

  it('does not log the full phone value', () => {
    expect(login).not.toMatch(/console\.(log|info|warn|error)/);
    expect(input).not.toMatch(/console\.(log|info|warn|error)/);
  });
});
