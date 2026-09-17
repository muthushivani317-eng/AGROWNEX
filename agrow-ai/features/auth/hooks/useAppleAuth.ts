import { useMutation } from '@tanstack/react-query';
import * as AppleAuthentication from 'expo-apple-authentication';
import * as Crypto from 'expo-crypto';
import { useEffect, useState } from 'react';
import { Platform } from 'react-native';

import { isFirebaseConfigured } from '@/config/env';
import { getLanguage } from '@/localization';
import type { SupportedLanguage } from '@/types';

import { authProvider } from '../services/authProvider';
import { useAuthStore } from '../store/authStore';
import { AuthError } from '../types';

const useReal = Platform.OS === 'ios' && isFirebaseConfigured;

function joinName(name: AppleAuthentication.AppleAuthenticationFullName | null): string | null {
  if (!name) return null;
  const parts = [name.givenName, name.familyName].filter(Boolean);
  return parts.length ? parts.join(' ') : null;
}

/**
 * Apple sign-in flow (iOS). Uses expo-apple-authentication with a hashed nonce
 * and exchanges the identity token for a Firebase credential. Falls back to the
 * mock provider in development or on non-iOS platforms.
 */
export function useAppleAuth() {
  const signIn = useAuthStore((s) => s.signIn);
  const [isAvailable, setIsAvailable] = useState(!useReal);

  useEffect(() => {
    if (!useReal) return;
    AppleAuthentication.isAvailableAsync()
      .then(setIsAvailable)
      .catch(() => setIsAvailable(false));
  }, []);

  const mutation = useMutation({
    mutationFn: async () => {
      const language = getLanguage() as SupportedLanguage;

      if (!useReal) {
        const credential = await authProvider.signInWithApple({
          identityToken: 'dev-mock',
          rawNonce: '',
          email: null,
          fullName: null,
        });
        await signIn(credential, language);
        return credential;
      }

      const rawNonce = Crypto.randomUUID();
      const hashedNonce = await Crypto.digestStringAsync(
        Crypto.CryptoDigestAlgorithm.SHA256,
        rawNonce,
      );

      const appleCred = await AppleAuthentication.signInAsync({
        requestedScopes: [
          AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
          AppleAuthentication.AppleAuthenticationScope.EMAIL,
        ],
        nonce: hashedNonce,
      });

      if (!appleCred.identityToken) {
        throw new AuthError('auth/cancelled', 'auth.socialCancelled');
      }

      const credential = await authProvider.signInWithApple({
        identityToken: appleCred.identityToken,
        rawNonce,
        email: appleCred.email,
        fullName: joinName(appleCred.fullName),
      });
      await signIn(credential, language);
      return credential;
    },
  });

  return {
    signIn: () => mutation.mutate(),
    isPending: mutation.isPending,
    isError: mutation.isError,
    error: mutation.error,
    isAvailable,
    // Shown only on iOS per Apple guidelines; dev/mock also renders for testing.
    isSupported: Platform.OS === 'ios' || __DEV__,
  };
}
