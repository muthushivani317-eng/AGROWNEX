import { useState } from "react";
import { useTranslation } from "react-i18next";
import { RefreshControl, ScrollView, StyleSheet, View } from "react-native";

import {
  AgChip,
  AgErrorState,
  AgOfflineBanner,
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import { ComparisonView } from "../components/ComparisonView";
import { SatelliteBackHeader } from "../components/SatelliteBackHeader";
import { TimelineChart } from "../components/TimelineChart";
import { TIMELINE_MONTHLY, TIMELINE_WEEKLY } from "../constants";
import {
  useSatelliteHistory,
  useSatelliteTimeline,
} from "../hooks/useSatellite";
import { SATELLITE_UI } from "../design";

/** Historical NDVI / NDRE / moisture charts + comparison for a farm. */
export function SatelliteTimelineScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const [range, setRange] = useState(TIMELINE_WEEKLY);
  const query = useSatelliteTimeline(farmId, range);
  const historyQuery = useSatelliteHistory(farmId);
  const points = query.data?.points ?? [];

  return (
    <AgScreen padded={false} backgroundColor={SATELLITE_UI.canvas}>
      <AgOfflineBanner />
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={query.isRefetching}
            onRefresh={() => void query.refetch()}
            tintColor={colors.primary}
          />
        }
      >
        <View className="pb-1 pt-1">
          <SatelliteBackHeader title={t("satellite.timelineTitle")} />
        </View>

        <View className="flex-row gap-2">
          <AgChip
            light
            label={t("satellite.weekly")}
            selected={range === TIMELINE_WEEKLY}
            onPress={() => setRange(TIMELINE_WEEKLY)}
          />
          <AgChip
            light
            label={t("satellite.monthly")}
            selected={range === TIMELINE_MONTHLY}
            onPress={() => setRange(TIMELINE_MONTHLY)}
          />
        </View>

        {query.isLoading ? (
          <View className="gap-3">
            {[0, 1, 2].map((i) => (
              <AgSkeleton key={i} className="h-32 w-full rounded-card" />
            ))}
          </View>
        ) : query.isError ? (
          <AgErrorState onRetry={() => void query.refetch()} />
        ) : (
          <>
            <TimelineChart
              points={points}
              indexKey="ndvi"
              titleKey="satellite.ndviChart"
            />
            <TimelineChart
              points={points}
              indexKey="ndre"
              titleKey="satellite.ndreChart"
            />
            <TimelineChart
              points={points}
              indexKey="ndmi"
              titleKey="satellite.moistureChart"
            />
            {(historyQuery.data?.items?.length ?? 0) >= 2 ? (
              <ComparisonView entries={historyQuery.data!.items} />
            ) : (
              <AgText variant="caption" style={styles.mutedText} className="px-1">
                {t("satellite.needMoreForComparison")}
              </AgText>
            )}
          </>
        )}
      </ScrollView>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1, paddingHorizontal: 20 },
  content: { gap: 12, paddingBottom: 112 },
  mutedText: { color: SATELLITE_UI.muted },
});
