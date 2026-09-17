import { TrendingUp } from "lucide-react-native";
import { useTranslation } from "react-i18next";
import { View } from "react-native";

import { AgOfflineBanner, AgScreen } from "@/components/ui";

import { ProduceBackHeader } from "../components/ProduceBackHeader";
import { ProduceListView } from "../components/ProduceListView";
import { useUpcomingProduce } from "../hooks/useProduce";
import { PRODUCE_COLORS as C } from "../produceTheme";

/** Dedicated Upcoming Harvest screen (docs: Upcoming Harvest Screen). */
export function UpcomingHarvestScreen() {
  const { t } = useTranslation();
  const query = useUpcomingProduce();

  return (
    <AgScreen padded={false} backgroundColor={C.bg}>
      <AgOfflineBanner />
      <View className="flex-1 px-5">
        <ProduceListView
          items={query.data?.items ?? []}
          isLoading={query.isLoading}
          isError={query.isError}
          isRefetching={query.isRefetching}
          onRefresh={() => void query.refetch()}
          onRetry={() => void query.refetch()}
          header={<ProduceBackHeader title={t("produce.upcomingTitle")} />}
          emptyIcon={TrendingUp}
          emptyTitle={t("produce.upcomingEmptyTitle")}
          emptyMessage={t("produce.upcomingEmptyMessage")}
        />
      </View>
    </AgScreen>
  );
}
