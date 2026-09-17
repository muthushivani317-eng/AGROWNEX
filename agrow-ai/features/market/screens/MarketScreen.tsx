import {
  MapPin,
  RefreshCw,
  ShieldCheck,
  Star,
  TrendingUp,
  X,
} from "lucide-react-native";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { AgErrorState, AgOfflineBanner, AgScreen } from "@/components/ui";
import { useSelectedFarm } from "@/features/weather";
import { MarketCard } from "../components/MarketCard";
import { MarketSearchBar } from "../components/MarketSearchBar";
import { MarketViewTabs } from "../components/MarketViewTabs";
import { SEARCH_TYPE_LABEL_KEY, SEARCH_TYPE_TO_FILTER } from "../constants";
import {
  useAddFavourite,
  useFavourites,
  useMarketPrices,
  useRemoveFavourite,
} from "../hooks/useMarket";
import type {
  MarketFavourite,
  MarketFilters,
  MarketPrice,
  MarketSearchResult,
  MarketView,
} from "../types";
import { formatRupees } from "../utils/format";
import {
  resolveMarketDataNotice,
  resolveMarketListState,
} from "../utils/marketListState";

const keyOf = (commodity: string, market: string, district: string) =>
  `${commodity}|${market}|${district}`.toLowerCase();

export function MarketScreen() {
  const { t } = useTranslation();
  const { selected: farm, isLoading: farmsLoading, isError: farmsError, refetch: refetchFarms } = useSelectedFarm();
  const [view, setView] = useState<MarketView>("all");
  const [filter, setFilter] = useState<MarketSearchResult | null>(null);
  const favouritesQuery = useFavourites();
  const favourites = useMemo(
    () => favouritesQuery.data ?? [],
    [favouritesQuery.data],
  );
  const favouriteIndex = useMemo(
    () =>
      new Map(
        favourites.map((item) => [
          keyOf(item.commodity, item.market, item.district),
          item,
        ]),
      ),
    [favourites],
  );
  const addFavourite = useAddFavourite();
  const removeFavourite = useRemoveFavourite();
  const nearbyDistrict = farm?.district ?? null;
  const filters = useMemo<MarketFilters>(() => {
    const next: MarketFilters = { pageSize: 30 };
    if (filter) next[SEARCH_TYPE_TO_FILTER[filter.type]] = filter.value;
    if (view === "today") next.todayOnly = true;
    if (view === "nearby" && nearbyDistrict) next.district = nearbyDistrict;
    return next;
  }, [filter, nearbyDistrict, view]);
  const nearbyBlocked = view === "nearby" && !nearbyDistrict;
  const pricesEnabled = view !== "favourites" && !nearbyBlocked;
  const pricesQuery = useMarketPrices(filters, pricesEnabled);
  const prices = useMemo(
    () => pricesQuery.data?.items ?? [],
    [pricesQuery.data],
  );
  const marketDataNotice = resolveMarketDataNotice({
    error: pricesQuery.isError || pricesQuery.data?.fromCache === true,
    itemCount: prices.length,
    view,
  });
  const busy = addFavourite.isPending || removeFavourite.isPending;
  const refreshing = pricesQuery.isFetching || favouritesQuery.isFetching;
  const refresh = () => {
    if (refreshing) return;
    if (view === "nearby") void refetchFarms();
    if (pricesEnabled) void pricesQuery.refetch({ cancelRefetch: false });
    void favouritesQuery.refetch({ cancelRefetch: false });
  };
  const mutationError = () => Alert.alert(t("common.somethingWrong"));
  const toggleFavourite = (price: MarketPrice) => {
    if (busy || favouritesQuery.isLoading || favouritesQuery.isError) return;
    const saved = favouriteIndex.get(
      keyOf(price.commodity, price.market, price.district),
    );
    if (saved) removeFavourite.mutate(saved.id, { onError: mutationError });
    else
      addFavourite.mutate({
        commodity: price.commodity,
        market: price.market,
        district: price.district,
        state: price.state,
      }, { onError: mutationError });
  };
  const header = (
    <View style={styles.header}>
      <View style={styles.titleRow}>
        <View style={styles.titleIcon}>
          <TrendingUp size={25} color="#fff" />
        </View>
        <View style={styles.flex}>
          <Text style={styles.eyebrow}>MARKET INTELLIGENCE</Text>
          <Text style={styles.title}>{t("market.title")}</Text>
        </View>
        <TouchableOpacity
          onPress={refresh}
          disabled={refreshing}
          accessibilityState={{ disabled: refreshing, busy: refreshing }}
          accessibilityRole="button"
          accessibilityLabel={t("common.refresh")}
          style={styles.iconButton}
        >
          {refreshing ? <ActivityIndicator color="#176B3A" /> : <RefreshCw size={22} color="#176B3A" />}
        </TouchableOpacity>
      </View>
      <View style={styles.notice}>
        <ShieldCheck size={21} color="#A56800" />
        <Text style={styles.noticeText}>
          {t("market.verifyOfficialSource")}
        </Text>
      </View>
      {marketDataNotice ? (
        <View style={styles.lastVerifiedNotice} accessibilityRole="alert">
          <View style={styles.lastVerifiedCopy}>
            <Text style={styles.lastVerifiedTitle}>
              {t(marketDataNotice.titleKey)}
            </Text>
            <Text style={styles.lastVerifiedMessage}>
              {t(marketDataNotice.messageKey)}
            </Text>
          </View>
          <TouchableOpacity
            onPress={refresh}
            accessibilityRole="button"
            accessibilityLabel={t("common.retry")}
            style={styles.lastVerifiedRetry}
          >
            <RefreshCw size={18} color="#6D4A05" />
            <Text style={styles.lastVerifiedRetryText}>
              {t("common.retry")}
            </Text>
          </TouchableOpacity>
        </View>
      ) : null}
      <MarketSearchBar onSelect={setFilter} />
      {view !== "favourites" && favouritesQuery.isError ? <AgErrorState light onRetry={() => void favouritesQuery.refetch()} /> : null}
      {filter ? (
        <TouchableOpacity
          onPress={() => setFilter(null)}
          style={styles.filterPill}
        >
          <Text style={styles.filterText}>
            {t(SEARCH_TYPE_LABEL_KEY[filter.type])}: {filter.label}
          </Text>
          <X size={16} color="#176B3A" />
        </TouchableOpacity>
      ) : null}
      <MarketViewTabs active={view} onChange={setView} />
    </View>
  );
  const data: Array<MarketPrice | MarketFavourite> =
    view === "favourites" ? favourites : nearbyBlocked ? [] : prices;
  const loading =
    view === "favourites" ? favouritesQuery.isLoading : view === "nearby" && farmsLoading ? true : pricesQuery.isLoading;
  const error =
    view === "favourites" ? favouritesQuery.isError : pricesQuery.isError;
  const listState = resolveMarketListState({
    loading,
    error,
    nearbyBlocked,
    view,
  });
  return (
    <AgScreen padded={false} backgroundColor="#FBF7EA">
      <AgOfflineBanner />
      <FlatList<MarketPrice | MarketFavourite>
        data={data}
        keyExtractor={(item) => item.id}
        style={styles.list}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={
              pricesQuery.isRefetching || favouritesQuery.isRefetching
            }
            onRefresh={refresh}
            colors={["#176B3A"]}
            tintColor="#176B3A"
          />
        }
        ListHeaderComponent={header}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
        renderItem={({ item }) =>
          "latest" in item ? (
            <FavouriteRow
              favourite={item}
              busy={busy}
              onRemove={() => { if (!busy) removeFavourite.mutate(item.id, { onError: mutationError }); }}
            />
          ) : (
            <MarketCard
              price={item}
              isFavourite={favouriteIndex.has(
                keyOf(item.commodity, item.market, item.district),
              )}
              onToggleFavourite={toggleFavourite}
              busy={busy || favouritesQuery.isLoading || favouritesQuery.isError}
            />
          )
        }
        ListEmptyComponent={
          view === "nearby" && farmsError ? <AgErrorState light onRetry={() => void refetchFarms()} /> : listState.kind === "loading" ? (
            <View style={styles.loading}>
              <ActivityIndicator size="large" color="#176B3A" />
            </View>
          ) : (
            <StateCard
              icon={
                listState.kind === "nearby"
                  ? "location"
                  : listState.kind === "favourites"
                    ? "star"
                    : "trend"
              }
              title={t(listState.titleKey)}
              message={t(listState.messageKey)}
              onRetry={listState.canRetry ? refresh : undefined}
            />
          )
        }
      />
    </AgScreen>
  );
}

function StateCard({
  icon = "trend",
  title,
  message,
  onRetry,
}: {
  icon?: "trend" | "location" | "star";
  title: string;
  message: string;
  onRetry?: () => void;
}) {
  const { t } = useTranslation();
  const Icon =
    icon === "location" ? MapPin : icon === "star" ? Star : TrendingUp;
  return (
    <View style={styles.stateCard}>
      <View style={styles.stateIcon}>
        <Icon size={34} color="#176B3A" />
      </View>
      <Text style={styles.stateTitle}>{title}</Text>
      <Text style={styles.stateMessage}>{message}</Text>
      {onRetry ? (
        <TouchableOpacity onPress={onRetry} style={styles.retry}>
          <RefreshCw size={19} color="#fff" />
          <Text style={styles.retryText}>{t("common.retry")}</Text>
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

function FavouriteRow({
  favourite,
  onRemove,
  busy,
}: {
  favourite: MarketFavourite;
  onRemove: () => void;
  busy?: boolean;
}) {
  const { t } = useTranslation();
  return (
    <View style={styles.card}>
      <View style={styles.titleRow}>
        <View style={styles.flex}>
          <Text style={styles.cardTitle}>{favourite.commodity}</Text>
          <Text style={styles.cardSub}>
            {favourite.market}
            {favourite.district ? `, ${favourite.district}` : ""}
          </Text>
        </View>
        <TouchableOpacity
          onPress={onRemove}
          disabled={busy}
          style={styles.iconButton}
        >
          <Star size={22} color="#B87900" fill="#F4B72C" />
        </TouchableOpacity>
      </View>
      {favourite.latest ? (
        <View style={styles.priceBlock}>
          <Text style={styles.caption}>{t("market.modalPrice")}</Text>
          <Text style={styles.price}>
            {formatRupees(favourite.latest.modalPrice)}
          </Text>
        </View>
      ) : (
        <Text style={styles.cardSub}>{t("market.noRecentPrice")}</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  list: { flex: 1, backgroundColor: "#FBF7EA" },
  content: {
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 110,
    flexGrow: 1,
  },
  header: { gap: 14, paddingBottom: 18 },
  separator: { height: 14 },
  flex: { flex: 1 },
  titleRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  titleIcon: {
    width: 52,
    height: 52,
    borderRadius: 17,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#176B3A",
  },
  eyebrow: {
    color: "#A56800",
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 0.8,
  },
  title: { color: "#173B2B", fontSize: 31, lineHeight: 38, fontWeight: "800" },
  iconButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "#D3D8D1",
    backgroundColor: "#FFFDF8",
  },
  notice: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    padding: 14,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#E2C987",
    backgroundColor: "#FFF8E7",
  },
  noticeText: {
    flex: 1,
    color: "#6D4A05",
    fontSize: 13,
    lineHeight: 18,
    fontWeight: "700",
  },
  lastVerifiedNotice: {
    gap: 12,
    padding: 14,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#E2C987",
    backgroundColor: "#FFF8E7",
  },
  lastVerifiedCopy: { gap: 3 },
  lastVerifiedTitle: {
    color: "#6D4A05",
    fontSize: 15,
    lineHeight: 20,
    fontWeight: "800",
  },
  lastVerifiedMessage: {
    color: "#765D2A",
    fontSize: 13,
    lineHeight: 19,
  },
  lastVerifiedRetry: {
    minHeight: 44,
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingHorizontal: 15,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#B87900",
    backgroundColor: "#FFFDF8",
  },
  lastVerifiedRetryText: {
    color: "#6D4A05",
    fontSize: 14,
    fontWeight: "800",
  },
  filterPill: {
    alignSelf: "flex-start",
    maxWidth: "100%",
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    borderRadius: 18,
    backgroundColor: "#EEF6EC",
    paddingHorizontal: 13,
    paddingVertical: 9,
  },
  filterText: {
    flexShrink: 1,
    color: "#176B3A",
    fontSize: 14,
    fontWeight: "700",
  },
  loading: { minHeight: 240, alignItems: "center", justifyContent: "center" },
  stateCard: {
    marginTop: 18,
    alignItems: "center",
    padding: 30,
    borderWidth: 1,
    borderColor: "#D8D7C9",
    borderRadius: 24,
    backgroundColor: "#FFFDF8",
  },
  stateIcon: {
    width: 82,
    height: 82,
    borderRadius: 41,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#EEF6EC",
  },
  stateTitle: {
    marginTop: 18,
    color: "#173B2B",
    fontSize: 23,
    lineHeight: 30,
    fontWeight: "800",
    textAlign: "center",
  },
  stateMessage: {
    marginTop: 8,
    color: "#58685F",
    fontSize: 16,
    lineHeight: 23,
    textAlign: "center",
  },
  retry: {
    marginTop: 22,
    minHeight: 50,
    alignSelf: "stretch",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 9,
    borderRadius: 16,
    backgroundColor: "#176B3A",
  },
  retryText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  card: {
    padding: 18,
    gap: 14,
    borderWidth: 1,
    borderColor: "#D8D7C9",
    borderRadius: 22,
    backgroundColor: "#FFFDF8",
  },
  cardTitle: { color: "#173B2B", fontSize: 21, fontWeight: "800" },
  cardSub: { marginTop: 4, color: "#58685F", fontSize: 15, lineHeight: 21 },
  priceBlock: { borderTopWidth: 1, borderTopColor: "#E4E4DA", paddingTop: 12 },
  caption: { color: "#607068", fontSize: 13 },
  price: { color: "#176B3A", fontSize: 27, fontWeight: "800" },
});
