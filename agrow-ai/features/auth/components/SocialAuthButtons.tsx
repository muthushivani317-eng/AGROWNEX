import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

import { AgButton, AgText } from '@/components/ui';

import { useAppleAuth } from '../hooks/useAppleAuth';
import { useGoogleAuth } from '../hooks/useGoogleAuth';
import { AuthError } from '../types';
import { authErrorMessage } from '../authMessages';

interface SocialAuthButtonsProps {
  onError?: (message: string) => void;
}

/** Google (all platforms) and Apple (iOS) sign-in buttons. */
export function SocialAuthButtons({ onError }: SocialAuthButtonsProps) {
  const { t } = useTranslation();
  const google = useGoogleAuth();
  const apple = useAppleAuth();

  // Surface sign-in failures (e.g. access-allowlist rejection) to the parent.
  // User-initiated cancellation is benign, so it is not reported as an error.
  const authError = google.error ?? apple.error;
  useEffect(() => {
    if (!authError) return;
    if (authError instanceof AuthError) {
      if (authError.code === 'auth/cancelled') return;
      onError?.(authErrorMessage(t, authError, 'signIn'));
    } else {
      onError?.(authErrorMessage(t, authError, 'signIn'));
    }
  }, [authError, onError, t]);

  return (
    <>
      <AgButton
        variant="outline"
        leftIcon={<AgText weight="bold" color="primary">G</AgText>}
        title={t('auth.continueWithGoogle')}
        onPress={google.signIn}
        loading={google.isPending}
        disabled={!google.isReady}
        accessibilityLabel={t('auth.continueWithGoogle')}
      />
      {apple.isSupported ? (
        <AgButton
          variant="outline"
          title={t('auth.continueWithApple')}
          onPress={apple.signIn}
          loading={apple.isPending}
          disabled={!apple.isAvailable}
          className="mt-3"
          accessibilityLabel={t('auth.continueWithApple')}
        />
      ) : null}
    </>
  );
}
