import { useRouter, useSegments } from 'expo-router';
import { useEffect, useRef } from 'react';
import { Platform } from 'react-native';

import { logger } from '@/lib/logger';
import { useAuthStore } from '@/features/auth/store/authStore';

import { resolveStartupRoute, shouldReplaceStartupRoute } from './startupStateMachine';

/** The only auth/onboarding redirect controller in the application. */
export function useStartupRouteGuard() {
  const router = useRouter();
  const segments = useSegments() as string[];
  const status = useAuthStore((state) => state.status);
  const user = useAuthStore((state) => state.user);
  const hasOnboarded = useAuthStore((state) => state.hasOnboarded);
  const languageSelected = useAuthStore((state) => state.languageSelected);
  const lastNavigation = useRef<string | null>(null);

  useEffect(() => {
    const target = resolveStartupRoute({
      authStatus: status,
      languageSelected,
      hasOnboarded,
      profileCompleted: Boolean(user?.profileCompleted),
    });
    if (!target) return;

    const group = segments[0];
    const screen = segments[1];
    const atIndex = segments.length === 0 || group === 'index';

    // The web root is AgrowAI's public website. Native cold starts keep using
    // the existing authentication/onboarding state machine unchanged.
    if (Platform.OS === 'web' && atIndex) return;

    const inAuth = group === '(auth)';
    const atTarget =
      (target === '/(tabs)' && group === '(tabs)') ||
      (target === '/(auth)/complete-profile' && inAuth && screen === 'complete-profile') ||
      (target === '/(auth)/language' && inAuth && screen === 'language') ||
      (target === '/(auth)/onboarding' && inAuth && screen === 'onboarding') ||
      (target === '/(auth)/login' && inAuth && screen === 'login');

    if (atTarget) {
      lastNavigation.current = null;
      return;
    }

    // Signed-out users may move through valid auth screens. Other route groups
    // are always redirected. Signed-in users cannot remain in the auth group.
    const shouldReplace = shouldReplaceStartupRoute({
      atIndex,
      inAuth,
      status,
      screen,
    });
    if (!shouldReplace || lastNavigation.current === target) return;

    lastNavigation.current = target;
    logger.info('startup_route', `resolved=${target}`);
    router.replace(target);
  }, [hasOnboarded, languageSelected, router, segments, status, user?.profileCompleted]);
}
