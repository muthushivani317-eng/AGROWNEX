import { useLocalSearchParams, useRouter } from "expo-router";
import {
  ArrowLeft,
  History,
  Plus,
  RefreshCw,
  ShieldCheck,
  Sprout,
  Wheat,
} from "lucide-react-native";
import { AgBadge } from "@/components/ui";
import { useCallback, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Pressable, StyleSheet, View } from "react-native";

import { AgScreen, AgText } from "@/components/ui";

import { ProduceListView } from "../components/ProduceListView";
import { ProduceViewTabs } from "../components/ProduceViewTabs";
import {
  useProduceHistory,
  useProduceList,
  useUpcomingProduce,
} from "../hooks/useProduce";
import { useProduceSync } from "../hooks/useProduceSync";
import { PRODUCE_COLORS as C } from "../produceTheme";
import type { ProduceView } from "../types";

export function ProduceListScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const params = useLocalSearchParams<{ organicOnly?: string | string[] }>();
  const organicOnlyParam = Array.isArray(params.organicOnly)
    ? params.organicOnly[0]
    : params.organicOnly;
  useProduceSync();
  const [view, setView] = useState<ProduceView>("all");
  const [organicOnly, setOrganicOnly] = useState(organicOnlyParam === "true");
  const refreshLock = useRef(false);
  const [refreshing, setRefreshing] = useState(false);
  const listQuery = useProduceList({ pageSize: 50, organicOnly }, view === "all");
  const availableQuery = useProduceList({ pageSize: 50, availabilityType: 'available_now', organicOnly }, view === 'available');
  const upcomingQuery = useUpcomingProduce(view === "upcoming");
  const historyQuery = useProduceHistory(view === "history");
  const active = useMemo(() => {
    if (view === "upcoming") return upcomingQuery;
    if (view === 'available') return availableQuery;
    if (view === "history") return historyQuery;
    return listQuery;
  }, [availableQuery, historyQuery, listQuery, upcomingQuery, view]);
  const refresh = useCallback(async () => {
    if (refreshLock.current) return;
    refreshLock.current = true;
    setRefreshing(true);
    try {
      await active.refetch();
    } finally {
      refreshLock.current = false;
      setRefreshing(false);
    }
  }, [active]);
  const empty =
    view === 'available'
      ? { icon: Sprout, title: t('produce.availableEmptyTitle'), message: t('produce.availableEmptyMessage') }
      : view === "upcoming"
      ? {
          icon: Wheat,
          title: t("produce.upcomingEmptyTitle"),
          message: t("produce.upcomingEmptyMessage"),
        }
      : view === "history"
        ? {
            icon: History,
            title: t("produce.historyEmptyTitle"),
            message: t("produce.historyEmptyMessage"),
          }
        : {
            icon: Sprout,
            title: t("produce.emptyTitle"),
            message: t("produce.emptyMessage"),
          };

  const header = (
    <View style={styles.header}>
      <View style={styles.topRow}>
        <Pressable
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={t("common.back")}
          hitSlop={8}
          style={styles.iconButton}
        >
          <ArrowLeft size={26} color={C.ink} />
        </Pressable>
        <View style={styles.featureMark}>
          <Wheat size={28} color={C.paper} />
        </View>
        <View style={styles.headingCopy}>
          <AgText variant="caption" weight="bold" style={styles.eyebrow}>
            {t("produce.eyebrow")}
          </AgText>
          <AgText variant="headingL" weight="bold" style={styles.ink}>
            {t("produce.title")}
          </AgText>
        </View>
        <Pressable
          onPress={() => void refresh()}
          disabled={refreshing}
          accessibilityRole="button"
          accessibilityLabel={t("produce.refresh")}
          hitSlop={8}
          style={styles.iconButton}
        >
          <RefreshCw size={23} color={C.green} />
        </Pressable>
      </View>
      <AgText variant="body" style={styles.muted}>
        {t("produce.subtitle")}
      </AgText>
      <View style={styles.notice}>
        <ShieldCheck size={22} color={C.gold} />
        <View style={styles.flex}>
          <AgText weight="semibold" style={styles.ink}>
            {t("produce.noticeTitle")}
          </AgText>
          <AgText variant="bodySmall" style={styles.muted}>
            {t("produce.procurementNote")}
          </AgText>
        </View>
      </View>
      <ProduceViewTabs active={view} onChange={setView} />
      {view === "all" || view === "available" ? (
        <Pressable
          onPress={() => setOrganicOnly((prev) => !prev)}
          accessibilityRole="checkbox"
          accessibilityState={{ checked: organicOnly }}
          style={styles.organicFilter}
        >
          <AgBadge
            label={t("produce.organicOnlyFilter")}
            tone={organicOnly ? "success" : "neutral"}
          />
        </Pressable>
      ) : null}
      {active.data?.cached ? (
        <AgText accessibilityRole="alert" variant="bodySmall" style={styles.cachedNotice}>
          {t("produce.cachedNotice")}
        </AgText>
      ) : null}
    </View>
  );

  return (
    <AgScreen padded={false} backgroundColor={C.bg}>
      <View style={styles.screenBody}>
        <ProduceListView
          items={active.isLoading || active.isError ? [] : active.data?.items ?? []}
          isLoading={active.isLoading}
          isError={active.isError}
          isRefetching={refreshing || active.isRefetching}
          onRefresh={() => void refresh()}
          onRetry={() => void refresh()}
          header={header}
          emptyIcon={empty.icon}
          emptyTitle={empty.title}
          emptyMessage={empty.message}
          emptyActionLabel={t("produce.create")}
          onEmptyAction={() => router.push("/produce/new")}
        />
      </View>
      <Pressable
        onPress={() => router.push("/produce/new")}
        accessibilityRole="button"
        accessibilityLabel={t("produce.create")}
        testID="produce-add-listing-button"
        style={styles.addButton}
      >
        <Plus size={22} color={C.paper} />
        <AgText weight="bold" style={styles.addLabel}>
          {t("produce.create")}
        </AgText>
      </Pressable>
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  screenBody: { flex: 1, paddingHorizontal: 20 },
  header: { paddingTop: 12, paddingBottom: 8, gap: 16 },
  organicFilter: { alignSelf: "flex-start" },
  topRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  iconButton: {
    width: 48,
    height: 48,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.paper,
    alignItems: "center",
    justifyContent: "center",
  },
  featureMark: {
    width: 52,
    height: 52,
    borderRadius: 18,
    backgroundColor: C.green,
    alignItems: "center",
    justifyContent: "center",
  },
  headingCopy: { flex: 1, minWidth: 0 },
  eyebrow: { color: C.gold, letterSpacing: 1.1 },
  ink: { color: C.ink },
  muted: { color: C.muted },
  cachedNotice: { color: "#8A5A00" },
  flex: { flex: 1 },
  notice: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
    padding: 16,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#E6C979",
    backgroundColor: C.goldSoft,
  },
  addButton: {
    position: "absolute",
    left: 20,
    right: 20,
    bottom: 16,
    height: 60,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingHorizontal: 20,
    borderRadius: 18,
    backgroundColor: C.green,
    shadowColor: C.ink,
    shadowOpacity: 0.22,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 5 },
    elevation: 5,
    zIndex: 20,
  },
  addLabel: { color: C.paper },
});
