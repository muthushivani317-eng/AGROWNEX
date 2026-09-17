import { useRouter } from "expo-router";
import {
  ArrowLeft,
  Bookmark,
  FileText,
  Info,
  Landmark,
  MapPin,
  ShieldCheck,
  Sparkles,
} from "lucide-react-native";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Alert, FlatList, RefreshControl, StyleSheet, TouchableOpacity, View } from "react-native";

import {
  AgEmptyState,
  AgErrorState,
  AgScreen,
  AgSkeleton,
  AgText,
} from "@/components/ui";
import { useSelectedFarm } from "@/features/weather";
import { FarmSelector } from "@/features/weather/components/FarmSelector";
import { useAppTheme } from "@/hooks/useAppTheme";

import { SchemeCard } from "../components/SchemeCard";
import { SchemeFilterBar } from "../components/SchemeFilterBar";
import { SchemeViewTabs } from "../components/SchemeViewTabs";
import { SEARCH_DEBOUNCE_MS } from "../constants";
import {
  useAddBookmark,
  useAllSchemes,
  useBookmarkedSchemes,
  useEligibleSchemes,
  useRecommendedSchemes,
  useRemoveBookmark,
  useSchemeQuery,
} from "../hooks/useSchemes";
import type {
  SchemeCategory,
  SchemeContext,
  SchemeSummary,
  SchemeTab,
} from "../types";

const SCREEN_BG = "#F7F3E8";
const TEXT = "#101713";
const MUTED = "#536158";
const GREEN = "#176B36";
const AMBER = "#B87517";

export function SchemesScreen() {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const router = useRouter();
  const farmQuery = useSelectedFarm();
  const { farms, selected, select } = farmQuery;
  const refreshLock = useRef(false);
  const bookmarkLock = useRef(false);
  const [refreshing, setRefreshing] = useState(false);
  const { query } = useSchemeQuery(selected);

  const [view, setView] = useState<SchemeTab>("eligible");
  const [category, setCategory] = useState<SchemeCategory | null>(null);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  useEffect(() => {
    const handle = setTimeout(
      () => setDebouncedSearch(search.trim()),
      SEARCH_DEBOUNCE_MS,
    );
    return () => clearTimeout(handle);
  }, [search]);

  const contextReady = !farmQuery.isLoading && !farmQuery.isError;
  const eligibleQuery = useEligibleSchemes(query, view === "eligible" && contextReady);
  const recommendedQuery = useRecommendedSchemes(query, view === "recommended" && contextReady);
  const allQuery = useAllSchemes(
    { category, search: debouncedSearch || null, pageSize: 50 },
    view === "all",
  );
  const bookmarksQuery = useBookmarkedSchemes(query, view === "bookmarked");
  const addBookmark = useAddBookmark();
  const removeBookmark = useRemoveBookmark();
  const bookmarkBusy = addBookmark.isPending || removeBookmark.isPending;

  const onToggleBookmark = (scheme: SchemeSummary) => {
    if (bookmarkLock.current) return;
    bookmarkLock.current = true;
    const mutation = scheme.bookmarked ? removeBookmark : addBookmark;
    mutation.mutate(scheme.id, {
      onError: () => Alert.alert(t("common.somethingWrong"), t("schemes.saveFailed")),
      onSettled: () => { bookmarkLock.current = false; },
    });
  };

  const active = useMemo(() => {
    switch (view) {
      case "eligible":
        return {
          items: eligibleQuery.data?.results.items ?? [],
          context: eligibleQuery.data?.context ?? null,
          isLoading: eligibleQuery.isLoading,
          isError: eligibleQuery.isError,
          isRefetching: eligibleQuery.isRefetching,
          refetch: eligibleQuery.refetch,
        };
      case "recommended":
        return {
          items: recommendedQuery.data?.items ?? [],
          context: recommendedQuery.data?.context ?? null,
          isLoading: recommendedQuery.isLoading,
          isError: recommendedQuery.isError,
          isRefetching: recommendedQuery.isRefetching,
          refetch: recommendedQuery.refetch,
        };
      case "all":
        return {
          items: allQuery.data?.items ?? [],
          context: null as SchemeContext | null,
          isLoading: allQuery.isLoading,
          isError: allQuery.isError,
          isRefetching: allQuery.isRefetching,
          refetch: allQuery.refetch,
        };
      case "bookmarked":
        return {
          items: bookmarksQuery.data ?? [],
          context: null as SchemeContext | null,
          isLoading: bookmarksQuery.isLoading,
          isError: bookmarksQuery.isError,
          isRefetching: bookmarksQuery.isRefetching,
          refetch: bookmarksQuery.refetch,
        };
    }
  }, [view, eligibleQuery, recommendedQuery, allQuery, bookmarksQuery]);

  const showContext = view === "eligible" || view === "recommended";
  const loading = active.isLoading || (showContext && farmQuery.isLoading);
  const failed = active.isError || (showContext && farmQuery.isError);
  const cached = view === "eligible" ? eligibleQuery.data?.cached
    : view === "recommended" ? recommendedQuery.data?.cached
    : view === "all" ? allQuery.data?.cached : false;
  const refresh = async () => {
    if (refreshLock.current) return;
    refreshLock.current = true;
    setRefreshing(true);
    try {
      await Promise.allSettled([farmQuery.refetch(), ...(contextReady || !showContext ? [active.refetch()] : [])]);
    } finally {
      refreshLock.current = false;
      setRefreshing(false);
    }
  };
  const empty = emptyFor(view, t);

  const header = (
    <View style={styles.headerContent}>
      <View style={styles.topBar}>
        <TouchableOpacity
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={t("common.back")}
          activeOpacity={0.7}
          style={styles.iconButton}
        >
          <ArrowLeft size={24} color={TEXT} />
        </TouchableOpacity>
        <View style={styles.titleIcon}>
          <Landmark size={28} color={GREEN} />
        </View>
        <View style={styles.titleRow} accessibilityLabel={t("schemes.title")}>
          <AgText variant="headingM" weight="bold" style={styles.primaryText}>
            {t("schemes.titleGovernment")}{" "}
          </AgText>
          <AgText variant="headingM" weight="bold" style={styles.greenText}>
            {t("schemes.titleSchemes")}
          </AgText>
        </View>
        <TouchableOpacity
          onPress={() => setView("bookmarked")}
          accessibilityRole="button"
          accessibilityLabel={t("schemes.tabBookmarked")}
          activeOpacity={0.7}
          style={styles.iconButton}
        >
          <Bookmark size={23} color={GREEN} />
        </TouchableOpacity>
      </View>

      <AgText variant="bodySmall" style={styles.secondaryText}>
        {t("schemes.subtitle")}
      </AgText>

      <View style={styles.verificationBanner} accessibilityRole="alert">
        <ShieldCheck size={26} color={AMBER} />
        <View style={styles.flexCopy}>
          <AgText
            variant="bodySmall"
            weight="semibold"
            style={styles.primaryText}
          >
            {t("schemes.testingOnlyInformation")}
          </AgText>
          <AgText variant="caption" style={styles.secondaryText}>
            {t("schemes.verifyAgainstOfficialSource")}
          </AgText>
        </View>
        <Info size={20} color={MUTED} />
      </View>

      {farms.length > 1 ? (
        <FarmSelector
          farms={farms}
          selectedId={selected?.id ?? null}
          onSelect={select}
          light
        />
      ) : null}
      <SchemeViewTabs active={view} onChange={setView} />

      {cached ? <AgText accessibilityRole="alert" style={styles.secondaryText}>{t("schemes.cachedNotice")}</AgText> : null}
      {showContext && !loading && !failed && active.context ? (
        <ContextBanner context={active.context} />
      ) : showContext && !loading && !failed && !selected ? (
        <View style={styles.contextCard}>
          <MapPin size={22} color={GREEN} />
          <View style={styles.flexCopy}>
            <AgText
              variant="bodySmall"
              weight="semibold"
              style={styles.primaryText}
            >
              {t("schemes.noFarmContextTitle")}
            </AgText>
            <AgText variant="caption" style={styles.secondaryText}>
              {t("schemes.noFarmContextMessage")}
            </AgText>
          </View>
        </View>
      ) : null}

      <TouchableOpacity
        onPress={() => router.push("/schemes/my-documents")}
        accessibilityRole="button"
        accessibilityLabel={t("schemes.myDocuments")}
        activeOpacity={0.72}
        style={styles.documentsButton}
      >
        <FileText size={18} color={GREEN} />
        <AgText variant="bodySmall" weight="semibold" style={styles.greenText}>
          {t("schemes.myDocuments")}
        </AgText>
      </TouchableOpacity>

      {view === "all" ? (
        <SchemeFilterBar
          search={search}
          onSearchChange={setSearch}
          category={category}
          onCategoryChange={setCategory}
        />
      ) : null}
    </View>
  );

  return (
    <AgScreen padded={false} backgroundColor={SCREEN_BG}>
      <View style={styles.screenBody}>
        <FlatList
          data={loading || failed ? [] : active.items}
          keyExtractor={(item) => item.id}
          ListHeaderComponent={header}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing || active.isRefetching}
              onRefresh={refresh}
              tintColor={colors.primary}
            />
          }
          renderItem={({ item }) => (
            <SchemeCard
              scheme={item}
              onToggleBookmark={onToggleBookmark}
              busy={bookmarkBusy}
            />
          )}
          ListEmptyComponent={
            loading ? (
              <SchemesSkeleton />
            ) : failed ? (
              <AgErrorState light onRetry={refresh} />
            ) : (
              <AgEmptyState
                light
                icon={empty.icon}
                title={empty.title}
                message={empty.message}
              />
            )
          }
        />
      </View>
    </AgScreen>
  );
}

function emptyFor(view: SchemeTab, t: (key: string) => string) {
  switch (view) {
    case "eligible":
      return {
        icon: ShieldCheck,
        title: t("schemes.eligibleEmptyTitle"),
        message: t("schemes.eligibleEmptyMessage"),
      };
    case "recommended":
      return {
        icon: Sparkles,
        title: t("schemes.recommendedEmptyTitle"),
        message: t("schemes.recommendedEmptyMessage"),
      };
    case "bookmarked":
      return {
        icon: Bookmark,
        title: t("schemes.bookmarkedEmptyTitle"),
        message: t("schemes.bookmarkedEmptyMessage"),
      };
    default:
      return {
        icon: FileText,
        title: t("schemes.allEmptyTitle"),
        message: t("schemes.allEmptyMessage"),
      };
  }
}

function ContextBanner({ context }: { context: SchemeContext }) {
  const { t } = useTranslation();
  const parts: string[] = [];
  if (context.district) parts.push(context.district);
  if (context.crop) parts.push(context.crop);
  if (context.farmerCategory)
    parts.push(
      t(`schemes.farmer_${context.farmerCategory}`, {
        defaultValue: context.farmerCategory,
      }),
    );
  if (parts.length === 0) return null;
  return (
    <View style={styles.contextCard}>
      <View style={styles.contextIcon}>
        <MapPin size={21} color={GREEN} />
      </View>
      <View style={styles.flexCopy}>
        <AgText variant="caption" style={styles.secondaryText}>
          {t("schemes.basedOn")}
        </AgText>
        <AgText variant="body" weight="semibold" style={styles.primaryText}>
          {parts.join(" · ")}
        </AgText>
      </View>
    </View>
  );
}

function SchemesSkeleton() {
  return (
    <View style={styles.skeletons}>
      {[0, 1, 2, 3].map((i) => (
        <AgSkeleton key={i} style={{ height: 208, width: "100%", borderRadius: 16, backgroundColor: "#D9D6C8" }} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  screenBody: { flex: 1, paddingHorizontal: 18 },
  listContent: { gap: 14, paddingBottom: 40 },
  headerContent: { gap: 16, paddingTop: 14, paddingBottom: 4 },
  topBar: { flexDirection: "row", alignItems: "center", gap: 10 },
  iconButton: {
    width: 44,
    height: 44,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 13,
    borderWidth: 1,
    borderColor: "#D9D6C8",
    backgroundColor: "#FFFFFF",
  },
  titleIcon: {
    width: 52,
    height: 52,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 26,
    borderWidth: 1,
    borderColor: "#BDD2B8",
    backgroundColor: "#EAF3E5",
  },
  titleRow: {
    flex: 1,
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "baseline",
  },
  primaryText: { color: TEXT },
  secondaryText: { color: MUTED },
  greenText: { color: GREEN },
  flexCopy: { flex: 1, gap: 3 },
  verificationBanner: {
    minHeight: 82,
    flexDirection: "row",
    alignItems: "center",
    gap: 13,
    padding: 16,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#E1CC9F",
    backgroundColor: "#FFF8E8",
  },
  contextCard: {
    minHeight: 76,
    flexDirection: "row",
    alignItems: "center",
    gap: 13,
    padding: 14,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#D9D6C8",
    backgroundColor: "#FFFFFF",
  },
  contextIcon: {
    width: 44,
    height: 44,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 22,
    backgroundColor: "#EAF3E5",
  },
  documentsButton: {
    minHeight: 48,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#BDD2B8",
    backgroundColor: "#EAF3E5",
  },
  skeletons: { gap: 14, paddingTop: 4 },
});
