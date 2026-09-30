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
  background: '#F7F4E8', card: '#FFFDF8', ink: '#073F2A', muted: '#617069',
  green: '#176B36', paleGreen: '#EAF3E6', border: '#D7DDCF',
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

        <View style={styles.brand} accessible accessibilityLabel={t('auth.brandAccessibility')}>
          <Image source={require('@/assets/images/android-icon-foreground.png')}
            contentFit="contain" style={styles.emblem} accessible={false} />
          <View style={styles.wordmark}>
            <AgText variant="headingS" weight="bold" style={styles.brandAgro}>Agro</AgText>
            <AgText variant="headingS" weight="bold" style={styles.brandNex}>nex</AgText>
          </View>
        </View>
        <AuthLanguageSelector variant="hero" style={styles.languageSelector} />
      </View>

      <View style={styles.content}>
        <View style={styles.card}>
          <Image
            source={require('@/assets/images/android-icon-foreground.png')}
            contentFit="contain"
            style={styles.cardLeafTop}
            accessible={false}
          />
          <View style={styles.securityMark}><ShieldCheck size={36} strokeWidth={2.2} color={OTP_COLORS.green} /></View>
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

          <View style={styles.verifyAction}>
            <AgButton light title={t('auth.verify')} onPress={() => submit(code)}
              loading={verify.isPending}
              disabled={code.length !== 6 || !hasConfirmation || verify.isPending || resend.isPending}
              size="lg"
              rightIcon={<ArrowRight size={20} color={OTP_COLORS.ink} />} />
          </View>

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
  topBar: { minHeight: 108, paddingTop: 18, paddingHorizontal: 18, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 4 },
  backButton: { width: 48, height: 48, borderRadius: 24, alignItems: 'center', justifyContent: 'center' },
  brand: { flexDirection: 'row', alignItems: 'center', minWidth: 0 },
  emblem: { width: 48, height: 48 },
  wordmark: { marginLeft: -5, flexDirection: 'row', alignItems: 'baseline' },
  brandAgro: { color: '#165B33', letterSpacing: -0.7 },
  brandNex: { color: '#E99818', letterSpacing: -0.7 },
  languageSelector: { flexShrink: 0 },
  content: { flexGrow: 1, width: '100%', maxWidth: 540, alignSelf: 'center', justifyContent: 'center', paddingHorizontal: 20, paddingBottom: 24 },
  card: { overflow: 'hidden', backgroundColor: OTP_COLORS.card, paddingHorizontal: 24, paddingTop: 42, paddingBottom: 22, borderRadius: 32, borderWidth: 1, borderColor: OTP_COLORS.border, shadowColor: '#315C42', shadowOpacity: 0.14, shadowRadius: 20, shadowOffset: { width: 0, height: 9 }, elevation: 4 },
  cardLeafTop: { position: 'absolute', top: -28, left: -30, width: 132, height: 132, opacity: 0.1, transform: [{ rotate: '-24deg' }] },
  securityMark: { width: 88, height: 88, borderRadius: 44, backgroundColor: OTP_COLORS.paleGreen, alignSelf: 'center', alignItems: 'center', justifyContent: 'center', marginBottom: 20 },
  title: { color: OTP_COLORS.ink },
  subtitle: { color: OTP_COLORS.muted, marginTop: 8, marginBottom: 30, alignSelf: 'center', maxWidth: 350, lineHeight: 25 },
  verifyAction: { marginTop: 20 },
  resendRow: { minHeight: 48, marginTop: 18, alignItems: 'center', justifyContent: 'center' },
  textButton: { minHeight: 44, alignSelf: 'center', justifyContent: 'center', paddingHorizontal: 8 },
  timerText: { color: '#737B75' }, actionText: { color: OTP_COLORS.green },
  changeButton: { minHeight: 50, alignSelf: 'flex-start', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 4, marginTop: 2 },
  changeText: { color: OTP_COLORS.green },
  securityNote: { marginTop: 24, paddingHorizontal: 22, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10 },
  securityCopy: { color: OTP_COLORS.muted, flexShrink: 1 },
});
