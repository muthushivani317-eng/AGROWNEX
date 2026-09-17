import { useMutation } from '@tanstack/react-query';
import * as Google from 'expo-auth-session/providers/google';
import * as WebBrowser from 'expo-web-browser';

import { env, isFirebaseConfigured, isGoogleConfigured } from '@/config/env';
import { getLanguage } from '@/localization';
import type { SupportedLanguage } from '@/types';

import { authProvider } from '../services/authProvider';
import { useAuthStore } from '../store/authStore';
import { AuthError } from '../types';

// Ensures the auth session popup dismisses correctly on return.
WebBrowser.maybeCompleteAuthSession();

const useReal = isGoogleConfigured && isFirebaseConfigured;

/**
 * Google sign-in flow. When Google + Firebase are configured it runs the real
 * OAuth flow (expo-auth-session) and exchanges the id token for a Firebase
 * credential; otherwise it falls back to the mock provider so the button works
 * in development. Returns a mutation-like handle for the UI.
 */
export function useGoogleAuth() {
  const signIn = useAuthStore((s) => s.signIn);

  // expo-auth-session's Google provider runs a render-time invariant check that
  // throws when a platform's client ID is undefined. When Google OAuth isn't
  // configured we pass a non-empty placeholder so the invariant passes; the
  // `useReal` guard below ensures promptAsync() is never called in that case.
  const [request, , promptAsync] = Google.useIdTokenAuthRequest({
    iosClientId: env.google.iosClientId || 'not-configured',
    androidClientId: env.google.androidClientId || 'not-configured',
    webClientId: env.google.webClientId || 'not-configured',
  });

  const mutation = useMutation({
    mutationFn: async () => {
      const language = getLanguage() as SupportedLanguage;

      if (!useReal) {
        const credential = await authProvider.signInWithGoogle('dev-mock');
        await signIn(credential, language);
        return credential;
      }

      const result = await promptAsync();
      if (result?.type !== 'success' || !result.params.id_token) {
        throw new AuthError('auth/cancelled', 'auth.socialCancelled');
      }
      const credential = await authProvider.signInWithGoogle(result.params.id_token);
      await signIn(credential, language);
      return credential;
    },
  });

  return {
    signIn: () => mutation.mutate(),
    isPending: mutation.isPending,
    isError: mutation.isError,
    error: mutation.error,
    // In real mode the request must be prepared before prompting.
    isReady: !useReal || Boolean(request),
  };
}
