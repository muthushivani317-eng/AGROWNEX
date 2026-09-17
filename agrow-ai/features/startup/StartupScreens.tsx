import { ActivityIndicator, Pressable, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { useAppTheme } from '@/hooks/useAppTheme';
import { SplashScreen } from '@/features/auth/screens/SplashScreen';

import type { StartupErrorCategory, StartupPhase } from './startupStateMachine';

interface StartupStatusScreenProps {
  phase: StartupPhase;
  errorCategory?: StartupErrorCategory | null;
  onRetry?: () => void;
  onReset?: () => void;
  onLayout?: () => void;
}

/** Dependency-free visible startup surface; safe even when theme/i18n fail. */
export function StartupStatusScreen({
  phase,
  errorCategory,
  onRetry,
  onReset,
  onLayout,
}: StartupStatusScreenProps) {
  const { colors } = useAppTheme();
  const { t } = useTranslation();
  const failed = phase === 'RECOVERABLE_ERROR';
  return (
    <View
      testID={failed ? 'startup-error-screen' : 'startup-loading-screen'}
      onLayout={onLayout}
      style={{
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        padding: 28,
        backgroundColor: colors.bg,
      }}
    >
      <Text style={{ color: colors.primary, fontSize: 30, fontWeight: '800' }}>{t('common.appName')}</Text>
      {failed ? (
        <>
          <Text style={{ marginTop: 18, color: colors.text, fontSize: 18, textAlign: 'center' }}>
            {t('startup.failureMessage')}
          </Text>
          <Text testID="startup-error-category" style={{ marginTop: 8, color: colors.textMuted }}>
            {errorCategory}
          </Text>
          <Pressable
            testID="startup-retry"
            accessibilityRole="button"
            onPress={onRetry}
            style={{ marginTop: 24, borderRadius: 10, backgroundColor: colors.primary, paddingHorizontal: 24, paddingVertical: 12 }}
          >
            <Text style={{ color: colors.onPrimary, fontWeight: '700' }}>{t('startup.retry')}</Text>
          </Pressable>
          <Pressable
            testID="startup-safe-reset"
            accessibilityRole="button"
            onPress={onReset}
            style={{ marginTop: 12, padding: 10 }}
          >
            <Text style={{ color: colors.primary, fontWeight: '600' }}>{t('startup.resetNavigation')}</Text>
          </Pressable>
        </>
      ) : (
        <>
          <ActivityIndicator testID="startup-spinner" color={colors.primary} style={{ marginTop: 22 }} />
          <Text style={{ marginTop: 14, color: colors.textMuted }}>{t('startup.startingSecurely')}</Text>
        </>
      )}
    </View>
  );
}

export function RouteResolvingScreen() {
  // The index route can remain mounted for a frame while Expo Router applies
  // the startup redirect. Keep that hand-off visually identical to the real
  // splash instead of flashing the old generic spinner screen.
  return (
    <View testID="route-resolving-screen" style={{ flex: 1 }}>
      <SplashScreen />
    </View>
  );
}
