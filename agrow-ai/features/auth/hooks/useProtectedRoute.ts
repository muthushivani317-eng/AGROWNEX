import { useRouter, useSegments } from 'expo-router';
import { useEffect } from 'react';

import { useAuth } from './useAuth';

/**
 * Central navigation guard. Keeps the visible route in sync with auth state:
 *  - signed out → onboarding / login
 *  - signed in but no profile → complete-profile
 *  - fully signed in → app tabs (and out of the auth group)
 */
export function useProtectedRoute() {
  const segments = useSegments();
  const router = useRouter();
  const { status, isAuthenticated, needsProfile, hasOnboarded } = useAuth();

  useEffect(() => {
    if (status === 'initializing') return;

    const seg = segments as string[];
    const inAuthGroup = seg[0] === '(auth)';
    const onProfileScreen = seg[1] === 'complete-profile';

    if (!isAuthenticated) {
      if (!inAuthGroup) {
        router.replace(hasOnboarded ? '/(auth)/login' : '/(auth)/language');
      }
      return;
    }

    if (needsProfile) {
      if (!onProfileScreen) router.replace('/(auth)/complete-profile');
      return;
    }

    if (inAuthGroup) router.replace('/(tabs)');
  }, [status, segments, isAuthenticated, needsProfile, hasOnboarded, router]);
}
