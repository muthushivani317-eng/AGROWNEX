import { Image } from 'expo-image';
import { useRouter } from 'expo-router';
import { ArrowLeft, ArrowRight, ShieldCheck } from 'lucide-react-native';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AppState, StyleSheet, View } from 'react-native';

import { AgButton, AgOtpInput, AgPressable, AgScreen, AgText } from '@/components/ui';

import { authErrorMessage } from '../authMessages';
import { AuthErrorBanner } from '../components/AuthErrorBanner';
import { AuthLanguageSelector } from '../components/AuthLanguageSelector';
import { useResendOtp, useVerifyOtp } from '../hooks/useAuthActions';
import { useOtpFlowStore } from '../store/otpFlowStore';
import { AuthError } from '../types';

const RESEND_SECONDS = 30;
const OTP_COLORS = {
  background: '#F7F3E8', card: '#FFFFFF', ink: '#101713', muted: '#536158',
  green: '#176B36', paleGreen: '#EAF3E6', border: '#D9D6C8',
};

export function VerifyOtpScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const displayPhone = useOtpFlowStore((s) => s.displayPhone);
  const phoneE164 = useOtpFlowStore((s) => s.phoneE164);
  const hasConfirmation = useOtpFlowStore((s) => Boolean(s.confirmation));
  const verify = useVerifyOtp();
  const resend = useResendOtp();
  const [code, setCode] = useState('');
  const [seconds, setSeconds] = useState(RESEND_SECONDS);
  const [resendAvailableAt, setResendAvailableAt] = useState(
    () => Date.now() + RESEND_SECONDS * 1000,
  );

  useEffect(() => {
    if (!phoneE164) router.replace('/(auth)/login');
  }, [phoneE164, router]);

  useEffect(() => {
    const updateCountdown = () => {
      const remaining = Math.max(
        0,
        Math.ceil((resendAvailableAt - Date.now()) / 1000),
      );
      setSeconds(remaining);
    };

    updateCountdown();
    const id = setInterval(updateCountdown, 1000);
    const appStateSubscription = AppState.addEventListener('change', (state) => {
      if (state === 'active') updateCountdown();
    });

    return () => {
      clearInterval(id);
      appStateSubscription.remove();
    };
  }, [resendAvailableAt]);

  const submit = (value: string) => {
    if (value.length !== 6 || verify.isPending || !hasConfirmation) return;
    verify.mutate(value);
  };

  const onResend = (allowImmediate = false) => {
    if ((!allowImmediate && seconds > 0) || resend.isPending || verify.isPending) return;
    resend.reset();
    resend.mutate(undefined, {
      onSuccess: ({ installed }) => {
        if (!installed) return;
        setResendAvailableAt(Date.now() + RESEND_SECONDS * 1000);
        setSeconds(RESEND_SECONDS);
        setCode('');
        verify.reset();
      },
    });
  };

  const showError = verify.isError;
  const resendErrorMessage = resend.isError
    ? authErrorMessage(t, resend.error, 'send')
    : null;
  const expiredConfirmation =
    verify.error instanceof AuthError &&
    (verify.error?.code === 'auth/session-expired' ||
      verify.error?.code === 'auth/code-expired');
  const needsNewCode = Boolean(phoneE164) && !hasConfirmation;
  const errorMessage = authErrorMessage(t, verify.error, 'confirm');

  return (
    <AgScreen testID="otp-entry-screen" scroll keyboardAvoiding padded={false}
      backgroundColor={OTP_COLORS.background} contentContainerStyle={styles.screen}>
      <View style={styles.topBar}>
        <AgPressable haptic={false} onPress={() => router.back()}
          accessibilityLabel={t('common.back')} style={styles.backButton}>
          <ArrowLeft size={23} color={OTP_COLORS.ink} />
        </AgPressable>

        <View style={styles.brand} accessible accessibilityLabel="AgrowAI">
          <Image source={require('@/assets/images/android-icon-foreground.png')}
            contentFit="contain" style={styles.emblem} accessible={false} />
          <View style={styles.wordmark}>
            <AgText variant="headingS" weight="bold" style={styles.brandAgrow}>Agrow</AgText>
            <AgText variant="headingS" weight="bold" style={styles.brandAi}>AI</AgText>
          </View>
        </View>
        <AuthLanguageSelector variant="hero" style={styles.languageSelector} />
      </View>

      <View style={styles.content}>
        <View style={styles.card}>
          <View style={styles.securityMark}><ShieldCheck size={31} color={OTP_COLORS.green} /></View>
          <AgText variant="headingL" weight="bold" center style={styles.title}>{t('auth.otpTitle')}</AgText>
          <AgText variant="body" center style={styles.subtitle}>
            {t('auth.otpSubtitle', { phone: displayPhone ?? '' })}
          </AgText>

          <AgOtpInput light value={code} onChange={(value) => {
            setCode(value);
            if (showError) verify.reset();
          }} onComplete={submit} error={showError} />

          {showError ? <AuthErrorBanner testID="otp-verification-error" message={errorMessage} /> : null}
          {resendErrorMessage ? (
            <AuthErrorBanner
              testID="otp-resend-error"
              message={resendErrorMessage}
            />
          ) : null}

          {expiredConfirmation || needsNewCode ? (
            <AgButton
              light
              title={t('auth.resendNewCode')}
              onPress={() => onResend(true)}
              loading={resend.isPending}
              disabled={resend.isPending || verify.isPending}
              size="lg"
              className="mt-4"
            />
          ) : null}

          <AgButton light title={t('auth.verify')} onPress={() => submit(code)}
            loading={verify.isPending}
            disabled={code.length !== 6 || !hasConfirmation || verify.isPending || resend.isPending}
            size="lg"
            rightIcon={<ArrowRight size={20} color={OTP_COLORS.ink} />} className="mt-6" />

          <View style={styles.resendRow}>
            {seconds > 0 ? (
              <AgText variant="bodySmall" style={styles.timerText}>{t('auth.resendIn', { seconds })}</AgText>
            ) : (
                <AgPressable haptic={false} onPress={() => onResend()} disabled={resend.isPending || verify.isPending} style={styles.textButton}>
                <AgText variant="body" weight="semibold" style={styles.actionText}>
                  {resend.isPending ? t('common.loading') : t('auth.resend')}
                </AgText>
              </AgPressable>
            )}
          </View>

          <AgPressable haptic={false} onPress={() => router.replace('/(auth)/login')}
            disabled={verify.isPending || resend.isPending} style={styles.changeButton}>
            <AgText variant="body" weight="semibold" style={styles.changeText}>{t('auth.changeNumber')}</AgText>
          </AgPressable>
        </View>

        <View style={styles.securityNote}>
          <ShieldCheck size={20} color={OTP_COLORS.green} />
          <AgText variant="bodySmall" style={styles.securityCopy}>{t('auth.otpSupport')}</AgText>
        </View>
      </View>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  screen: { flexGrow: 1, paddingBottom: 24 },
  topBar: { minHeight: 92, paddingTop: 18, paddingHorizontal: 14, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 4 },
  backButton: { width: 48, height: 48, borderRadius: 16, borderWidth: 1, borderColor: OTP_COLORS.border, backgroundColor: OTP_COLORS.card, alignItems: 'center', justifyContent: 'center' },
  brand: { flexDirection: 'row', alignItems: 'center', minWidth: 0 },
  emblem: { width: 40, height: 40 },
  wordmark: { marginLeft: -5, flexDirection: 'row', alignItems: 'baseline' },
  brandAgrow: { color: '#165B33', letterSpacing: -0.6 },
  brandAi: { color: '#D99800', letterSpacing: -0.6 },
  languageSelector: { flexShrink: 0 },
  content: { flexGrow: 1, width: '100%', maxWidth: 540, alignSelf: 'center', justifyContent: 'center', paddingHorizontal: 20, paddingBottom: 18 },
  card: { backgroundColor: OTP_COLORS.card, paddingHorizontal: 20, paddingTop: 26, paddingBottom: 20, borderRadius: 24, borderWidth: 1, borderColor: OTP_COLORS.border, shadowColor: '#35483C', shadowOpacity: 0.1, shadowRadius: 14, shadowOffset: { width: 0, height: 6 }, elevation: 3 },
  securityMark: { width: 62, height: 62, borderRadius: 20, backgroundColor: OTP_COLORS.paleGreen, alignSelf: 'center', alignItems: 'center', justifyContent: 'center', marginBottom: 16 },
  title: { color: OTP_COLORS.ink },
  subtitle: { color: OTP_COLORS.muted, marginTop: 7, marginBottom: 28, alignSelf: 'center', maxWidth: 350 },
  resendRow: { minHeight: 48, marginTop: 16, alignItems: 'center', justifyContent: 'center' },
  textButton: { minHeight: 44, alignSelf: 'center', justifyContent: 'center', paddingHorizontal: 8 },
  timerText: { color: '#737B75' }, actionText: { color: OTP_COLORS.green },
  changeButton: { minHeight: 50, borderRadius: 14, borderWidth: 1, borderColor: OTP_COLORS.border, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 12 },
  changeText: { color: OTP_COLORS.green },
  securityNote: { marginTop: 18, paddingHorizontal: 12, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 9 },
  securityCopy: { color: OTP_COLORS.muted, flexShrink: 1 },
});
