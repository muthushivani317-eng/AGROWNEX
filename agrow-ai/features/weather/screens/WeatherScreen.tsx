import { useRouter } from "expo-router";
import { ArrowLeft, MapPinOff, RefreshCw, Sprout } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { ActivityIndicator, Pressable, StyleSheet, View } from "react-native";

import {
  AgEmptyState,
  AgErrorState,
  AgPressable,
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";

import { FarmSelector } from "../components/FarmSelector";
import { HourlyForecast } from "../components/HourlyForecast";
import { TodayMissionCard } from "../components/TodayMissionCard";
import { WeatherAlerts } from "../components/WeatherAlerts";
import { WeatherCard } from "../components/WeatherCard";
import { WeatherMetrics } from "../components/WeatherMetrics";
import { WeeklyForecast } from "../components/WeeklyForecast";
import { useSelectedFarm } from "../hooks/useSelectedFarm";
import { useWeather } from "../hooks/useWeather";
import { WEATHER_REFRESH_MS } from "../constants";
import { WEATHER_SHADOW, WEATHER_UI } from "../design";

export function isWeatherDataStale(
  fetchedAt: string,
  now = Date.now(),
): boolean {
  const fetched = Date.parse(fetchedAt);
  return !Number.isFinite(fetched) || now - fetched > WEATHER_REFRESH_MS;
}

function WeatherSkeleton() {
  return (
    <View style={styles.skeletons}>
      <AgSkeleton
        style={[styles.heroSkeleton, styles.lightSkeleton]}
      />
      <View style={styles.skeletonRow}>
        <AgSkeleton
          style={[styles.metricSkeleton, styles.lightSkeleton]}
        />
        <AgSkeleton
          style={[styles.metricSkeleton, styles.lightSkeleton]}
        />
      </View>
      <AgSkeleton
        style={[styles.forecastSkeleton, styles.lightSkeleton]}
      />
    </View>
  );
}

function WeatherHeader({
  refreshing,
  onRefresh,
}: {
  refreshing: boolean;
  onRefresh: () => void;
}) {
  const { t } = useTranslation();
  const router = useRouter();
  return (
    <View style={styles.header}>
      {/* Reached from Home's "Weather" quick action -- this shared header
          renders on every branch (loading, error, no-farms, main) and had no
          back affordance at all (2026-08 pre-release UI pass). */}
      <AgPressable
        onPress={() => router.back()}
        accessibilityRole="button"
        accessibilityLabel={t("common.back")}
        hitSlop={8}
        style={styles.backButton}
      >
        <ArrowLeft size={24} color={WEATHER_UI.text} />
      </AgPressable>
      <View style={styles.headerCopy}>
        <AgText variant="label" weight="semibold" style={styles.eyebrow}>
          {t("weather.fieldForecast")}
        </AgText>
        <AgText variant="headingM" weight="bold" style={styles.headerTitle}>
          {t("weather.title")}
        </AgText>
      </View>
      <Pressable
        testID="weather-refresh-button"
        accessibilityRole="button"
        accessibilityLabel={t("weather.refresh")}
        accessibilityState={{ disabled: refreshing, busy: refreshing }}
        disabled={refreshing}
        onPress={onRefresh}
        style={[
          styles.refreshButton,
          {
            backgroundColor: WEATHER_UI.surface,
            borderColor: WEATHER_UI.border,
          },
        ]}
      >
        {refreshing ? (
          <ActivityIndicator color={WEATHER_UI.field} />
        ) : (
          <RefreshCw size={22} color={WEATHER_UI.field} />
        )}
      </Pressable>
    </View>
  );
}

export function WeatherScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const {
    farms,
    selected,
    select,
    isLoading: farmsLoading,
    isError: farmsError,
    refetch: refetchFarms,
  } = useSelectedFarm();

  const hasCoords = selected?.latitude != null && selected?.longitude != null;
  const query = selected
    ? {
        farmId: selected.id,
        latitude: selected.latitude,
        longitude: selected.longitude,
        name: selected.name,
      }
    : {};
  const { data, isLoading, isError, isFetching, refetch } = useWeather(
    query,
    Boolean(selected) && hasCoords,
  );
  // Only the offline-cache fallback in useWeather sets isCached; "stale"
  // additionally requires that cached bundle to be older than the normal
  // refresh cadence, so a farmer only sees a warning once it's actually
  // meaningfully out of date, not on every brief reconnect blip.
  const cached = Boolean(data?.isCached);
  const stale = cached && isWeatherDataStale(data?.fetchedAt ?? "");

  if (farmsLoading) {
    return (
      <AgScreen
        scroll
        backgroundColor={WEATHER_UI.canvas}
        contentContainerStyle={styles.content}
      >
        <WeatherHeader refreshing onRefresh={() => void refetchFarms()} />
        <WeatherSkeleton />
      </AgScreen>
    );
  }

  if (farmsError) {
    return (
      <AgScreen
        backgroundColor={WEATHER_UI.canvas}
        contentContainerStyle={styles.content}
      >
        <WeatherHeader
          refreshing={false}
          onRefresh={() => void refetchFarms()}
        />
        <AgErrorState light onRetry={() => void refetchFarms()} />
      </AgScreen>
    );
  }

  if (!farms.length) {
    return (
      <AgScreen
        backgroundColor={WEATHER_UI.canvas}
        contentContainerStyle={styles.content}
      >
        <WeatherHeader
          refreshing={false}
          onRefresh={() => void refetchFarms()}
        />
        <AgEmptyState
          light
          icon={Sprout}
          title={t("weather.noFarmsTitle")}
          message={t("weather.noFarmsMessage")}
          actionLabel={t("farm.addFarm")}
          onAction={() => router.push("/farm/new")}
        />
      </AgScreen>
    );
  }

  return (
    <AgScreen
      scroll
      backgroundColor={WEATHER_UI.canvas}
      contentContainerStyle={styles.content}
    >
      <WeatherHeader refreshing={isFetching} onRefresh={() => void refetch()} />
      <FarmSelector
        farms={farms}
        selectedId={selected?.id ?? null}
        onSelect={select}
        light
      />

      {selected && !hasCoords ? (
        <AgEmptyState
          light
          icon={MapPinOff}
          title={t("weather.noLocationTitle")}
          message={t("weather.noLocationMessage")}
          actionLabel={t("weather.addLocation")}
          onAction={() => router.push(`/farm/${selected.id}/edit`)}
        />
      ) : isLoading ? (
        <WeatherSkeleton />
      ) : isError || !data ? (
        <AgErrorState
          light
          message={t("weather.errorMessage")}
          onRetry={() => void refetch()}
        />
      ) : (
        <View testID="weather-dynamic-content" style={styles.dynamicContent}>
          <TodayMissionCard
            mission={data.mission}
            insights={data.insights}
            cached={cached}
            stale={stale}
          />
          <WeatherCard
            current={data.current}
            location={data.location}
            fetchedAt={data.fetchedAt}
            cached={cached}
            stale={stale}
          />
          <WeatherMetrics
            current={data.current}
            today={data.daily[0] ?? null}
            fetchedAt={data.fetchedAt}
            cached={cached}
            stale={stale}
          />
          <HourlyForecast
            hourly={data.hourly}
            fetchedAt={data.fetchedAt}
            cached={cached}
            stale={stale}
          />
          <WeatherAlerts
            insights={data.insights}
            fetchedAt={data.fetchedAt}
            cached={cached}
            stale={stale}
          />
          <WeeklyForecast
            daily={data.daily}
            fetchedAt={data.fetchedAt}
            cached={cached}
            stale={stale}
          />
        </View>
      )}
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  // Keep the forecast comfortably clear of the system and app navigation bars.
  content: { paddingTop: 12, paddingBottom: 128 },
  header: {
    minHeight: 58,
    marginBottom: 16,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 16,
  },
  headerCopy: { flex: 1, gap: 1 },
  eyebrow: { color: WEATHER_UI.sun, letterSpacing: 0.8 },
  headerTitle: { color: WEATHER_UI.text },
  backButton: {
    width: 48,
    height: 48,
    borderRadius: 16,
    backgroundColor: WEATHER_UI.surface,
    alignItems: "center",
    justifyContent: "center",
    ...WEATHER_SHADOW,
  },
  refreshButton: {
    width: 50,
    height: 50,
    borderRadius: 25,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  pressed: { opacity: 0.72 },
  dynamicContent: { gap: 16, paddingTop: 16 },
  skeletons: { marginTop: 4, gap: 14 },
  lightSkeleton: { backgroundColor: WEATHER_UI.surface },
  heroSkeleton: { width: "100%", height: 220, borderRadius: 26 },
  skeletonRow: { flexDirection: "row", gap: 12 },
  metricSkeleton: { flex: 1, height: 132, borderRadius: 22 },
  forecastSkeleton: { width: "100%", height: 330, borderRadius: 24 },
});
