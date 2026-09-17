import { ShieldCheck } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { FlatList, RefreshControl, StyleSheet, View } from "react-native";

import {
  AgEmptyState,
  AgErrorState,
  AgOfflineBanner,
  AgScreen,
  AgSkeleton,
} from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";

import { SatelliteAlertCard } from "../components/SatelliteAlertCard";
import { SatelliteBackHeader } from "../components/SatelliteBackHeader";
import { useSatelliteAlerts } from "../hooks/useSatellite";
import { SATELLITE_UI } from "../design";

/** All satellite alerts for the latest session. */
export function SatelliteAlertsScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const query = useSatelliteAlerts(farmId);
  const items = query.data ?? [];

  return (
    <AgScreen padded={false} backgroundColor={SATELLITE_UI.canvas}>
      <AgOfflineBanner />
      <View style={styles.screen}>
        <FlatList
          data={items}
          keyExtractor={(item) => item.code}
          ListHeaderComponent={
            <View className="pb-2">
              <SatelliteBackHeader title={t("satellite.alertsTitle")} />
            </View>
          }
          contentContainerStyle={styles.content}
          refreshControl={
            <RefreshControl
              refreshing={query.isRefetching}
              onRefresh={() => void query.refetch()}
              tintColor={colors.primary}
            />
          }
          renderItem={({ item }) => <SatelliteAlertCard alert={item} />}
          ListEmptyComponent={
            query.isLoading ? (
              <View className="mt-2 gap-3">
                {[0, 1, 2].map((i) => (
                  <AgSkeleton key={i} className="h-20 w-full rounded-card" />
                ))}
              </View>
            ) : query.isError ? (
              <AgErrorState onRetry={() => void query.refetch()} />
            ) : (
              <AgEmptyState
                icon={ShieldCheck}
                title={t("satellite.alertsEmptyTitle")}
                message={t("satellite.alertsEmptyMessage")}
              />
            )
          }
        />
      </View>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, paddingHorizontal: 20 },
  content: { gap: 12, paddingBottom: 112 },
});
