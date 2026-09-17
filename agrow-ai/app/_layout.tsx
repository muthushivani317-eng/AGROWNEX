import "../global.css";

import {
  Inter_400Regular,
  Inter_500Medium,
  Inter_600SemiBold,
  Inter_700Bold,
} from "@expo-google-fonts/inter";
import {
  NotoSansTamil_400Regular,
  NotoSansTamil_500Medium,
  NotoSansTamil_600SemiBold,
  NotoSansTamil_700Bold,
} from "@expo-google-fonts/noto-sans-tamil";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { StatusBar } from "expo-status-bar";
import { useCallback, useEffect, useRef, useState } from "react";
import { View } from "react-native";

import { ConfigurationErrorScreen } from "@/components/ConfigurationErrorScreen";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { AgOfflineBanner } from "@/components/ui";
import {
  getReleaseEnvironmentError,
  isDev,
  missingPublicEnvKeys,
} from "@/config/env";
import { useSessionGuard } from "@/features/auth";
import { SplashScreen as BrandedSplashScreen } from "@/features/auth/screens/SplashScreen";
import { useAuthStore } from "@/features/auth/store/authStore";
import { StartupStatusScreen } from "@/features/startup/StartupScreens";
import {
  runStartupSequence,
  type StartupErrorCategory,
  type StartupPhase,
} from "@/features/startup/startupStateMachine";
import { useStartupRouteGuard } from "@/features/startup/useStartupRouteGuard";
import { useAppTheme } from "@/hooks/useAppTheme";
import { initDatabase } from "@/lib/db";
import { logger } from "@/lib/logger";
import { initI18n } from "@/localization";
import { AppProviders } from "@/providers/AppProviders";

SplashScreen.preventAutoHideAsync().catch(() => {});

/** Renders the navigator and enforces the auth-aware route guard. */
function RootNavigator() {
  const { isDark, colors } = useAppTheme();
  useStartupRouteGuard();
  useSessionGuard();

  return (
    <View
      className="flex-1 bg-bg"
      style={{ flex: 1, backgroundColor: colors.bg }}
    >
      <StatusBar style={isDark ? "light" : "dark"} />
      <AgOfflineBanner />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: colors.bg },
          animation: "slide_from_right",
        }}
      >
        <Stack.Screen name="index" />
        <Stack.Screen name="(auth)" />
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="profile/edit" />
        <Stack.Screen name="profile/account" />
        <Stack.Screen name="profile/organizations" />
        <Stack.Screen name="support/index" />
        <Stack.Screen name="+not-found" options={{ presentation: "modal" }} />
      </Stack>
    </View>
  );
}

export default function RootLayout() {
  const configurationError = getReleaseEnvironmentError();
  const [phase, setPhase] = useState<StartupPhase>("BOOTING");
  const [startupError, setStartupError] = useState<StartupErrorCategory | null>(
    null,
  );
  const [attempt, setAttempt] = useState(0);
  const nativeSplashHidden = useRef(false);
  const bootstrap = useAuthStore((s) => s.bootstrap);
  const resetStartupState = useAuthStore((s) => s.resetStartupState);

  const [, fontError] = useFonts({
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
    NotoSansTamil_400Regular,
    NotoSansTamil_500Medium,
    NotoSansTamil_600SemiBold,
    NotoSansTamil_700Bold,
  });

  useEffect(() => {
    if (configurationError) {
      // Category only: never log endpoint values, credentials or exception text.
      logger.error("startup_configuration", configurationError);
      return;
    }

    // Flag a misconfigured *release* build loudly: if `.env` was not bundled,
    // every EXPO_PUBLIC_* value silently falls back to its default. Blank keys
    // are the normal state in local dev (mock providers), so only warn outside
    // dev to avoid noise. Log key names only — never the values themselves.
    if (!isDev) {
      const missing = missingPublicEnvKeys();
      if (missing.length > 0) {
        logger.warn(
          "env",
          `Missing/empty EXPO_PUBLIC_* keys (using fallback defaults): ${missing.join(", ")}. ` +
            "This means .env was not bundled into the build.",
        );
      }
    }

    let active = true;
    setPhase("BOOTING");
    setStartupError(null);
    logger.info("startup_phase", "BOOTING");

    void runStartupSequence(
      {
        initializeStorage: async () => {
          await initI18n();
        },
        initializeDatabase: initDatabase,
        // Firebase auto-initialises natively. This restores only the bounded,
        // on-device session state required for deterministic routing.
        restoreAuth: bootstrap,
        resolveRoute: () => {
          const state = useAuthStore.getState();
          logger.info(
            "startup_state",
            `auth=${state.status} onboarding=${state.hasOnboarded ? "complete" : "incomplete"} language=${state.languageSelected ? "selected" : "unselected"}`,
          );
        },
      },
      (nextPhase) => {
        if (!active) return;
        logger.info("startup_phase", nextPhase);
        setPhase(nextPhase);
      },
    ).then((result) => {
      if (!active) return;
      setStartupError(result.errorCategory);
      setPhase(result.phase);
    });

    return () => {
      active = false;
    };
  }, [attempt, bootstrap, configurationError]);

  useEffect(() => {
    if (fontError)
      logger.warn("startup_fonts", "font_loading_failed_using_system_fallback");
  }, [fontError]);

  const hideNativeSplashOnce = useCallback(() => {
    if (nativeSplashHidden.current) return;
    nativeSplashHidden.current = true;
    void SplashScreen.hideAsync().catch(() => {});
  }, []);

  const retry = useCallback(() => setAttempt((value) => value + 1), []);
  const safeReset = useCallback(() => {
    void resetStartupState().finally(() => setAttempt((value) => value + 1));
  }, [resetStartupState]);

  if (configurationError) {
    return (
      <View style={{ flex: 1 }} onLayout={hideNativeSplashOnce}>
        <ConfigurationErrorScreen category={configurationError} />
      </View>
    );
  }

  if (phase !== "READY" && phase !== "RECOVERABLE_ERROR") {
    return <BrandedSplashScreen onReady={hideNativeSplashOnce} />;
  }

  if (phase === "RECOVERABLE_ERROR") {
    return (
      <StartupStatusScreen
        phase={phase}
        errorCategory={startupError}
        onRetry={retry}
        onReset={safeReset}
        onLayout={hideNativeSplashOnce}
      />
    );
  }

  return (
    <ErrorBoundary>
      <AppProviders>
        <View
          testID="agrowai-react-root"
          className="flex-1"
          style={{ flex: 1, minHeight: 1 }}
          onLayout={hideNativeSplashOnce}
        >
          <RootNavigator />
        </View>
      </AppProviders>
    </ErrorBoundary>
  );
}
