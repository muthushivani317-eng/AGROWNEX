import { Sprout } from "lucide-react-native";
import { useRouter } from "expo-router";
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

import { SoilFeatureHeader } from "../components/SoilFeatureHeader";
import { SoilRecommendationCard } from "../components/SoilRecommendationCard";
import { SOIL_UI } from "../design";
import { useSoilRecommendations } from "../hooks/useSoil";

/** All generic agronomic recommendations for a farm (no commercial brands). */
export function SoilRecommendationsScreen({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const query = useSoilRecommendations(farmId);
  const items = query.data ?? [];

  return (
    <AgScreen padded={false} backgroundColor={SOIL_UI.canvas}>
      <AgOfflineBanner />
      <View style={styles.screen}>
        <FlatList
          data={items}
          keyExtractor={(item) => item.code}
          ListHeaderComponent={
            <View style={styles.headerSpace}>
              <SoilFeatureHeader
                title={t("soil.recommendationsTitle")}
                onBack={() => router.back()}
              />
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
          renderItem={({ item }) => <SoilRecommendationCard rec={item} />}
          ListEmptyComponent={
            query.isLoading ? (
              <View style={styles.loadingList}>
                {[0, 1, 2].map((i) => (
                  <AgSkeleton key={i} className="h-24 w-full rounded-card" />
                ))}
              </View>
            ) : query.isError ? (
              <AgErrorState light onRetry={() => void query.refetch()} />
            ) : (
              <AgEmptyState
                light
                icon={Sprout}
                title={t("soil.recsEmptyTitle")}
                message={t("soil.recsEmptyMessage")}
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
  headerSpace: { paddingBottom: 4 },
  loadingList: { marginTop: 8, gap: 12 },
});
