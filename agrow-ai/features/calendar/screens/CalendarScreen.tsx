import { useRouter } from "expo-router";
import dayjs from "dayjs";
import {
  ArrowLeft,
  CalendarDays,
  Lightbulb,
  RefreshCw,
  Sprout,
} from "lucide-react-native";
import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  TouchableOpacity,
  View,
} from "react-native";

import {
  AgButton,
  AgEmptyState,
  AgErrorState,
  AgScreen,
  AgText,
} from "@/components/ui";
import { useFarm } from "@/features/farm";
import { useSelectedFarm } from "@/features/weather";
import { useAppTheme } from "@/hooks/useAppTheme";

import { CalendarProgress } from "../components/CalendarProgress";
import { CropFilter } from "../components/CropFilter";
import { FarmSwitcher } from "../components/FarmSwitcher";
import { MonthView } from "../components/MonthView";
import { TaskCard } from "../components/TaskCard";
import { ViewTabs } from "../components/ViewTabs";
import { VIEW_LABEL_KEY } from "../constants";
import {
  useCalendarSummary,
  useCalendarView,
  useGenerateCalendar,
  useUpdateEvent,
} from "../hooks/useCalendar";
import type { CalendarEvent, CalendarView } from "../types";
import { CalendarError } from "../services/calendarProvider";

const CALENDAR_COLORS = {
  background: "#FBF8F0",
  card: "#FFFFFF",
  ink: "#153C24",
  body: "#34443A",
  primary: "#176B36",
  border: "#D7DDCF",
  pale: "#EEF4E8",
} as const;

export function CalendarScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();

  const {
    farms,
    selected,
    select,
    isLoading: farmsLoading,
    isError: farmsError,
    refetch: refetchFarms,
  } = useSelectedFarm();
  const farmId = selected?.id ?? null;
  const farmQuery = useFarm(farmId ?? undefined);
  const { data: farm } = farmQuery;
  const refreshLock = useRef(false);
  const mutationLock = useRef(false);
  const [refreshing, setRefreshing] = useState(false);

  const [view, setView] = useState<CalendarView>("today");
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [cropFilter, setCropFilter] = useState<string | null>(null);
  const [organicOnly, setOrganicOnly] = useState(false);

  const listView: CalendarView = view === "month" ? "timeline" : view;
  const { data, isLoading, isError, refetch, isRefetching } = useCalendarView(
    farmId,
    listView,
  );
  const summaryQuery = useCalendarSummary(farmId);
  const { data: summary, refetch: refetchSummary } = summaryQuery;
  const generate = useGenerateCalendar();
  const update = useUpdateEvent();

  const events = useMemo(() => data ?? [], [data]);
  const cachedAt = events.find((event) => event.dataState !== "live")?.cachedAt;
  const crops = useMemo(
    () =>
      Array.from(
        new Set(events.map((event) => event.crop).filter(Boolean) as string[]),
      ),
    [events],
  );
  const filtered = useMemo(
    () =>
      events.filter((event) => (!cropFilter || event.crop === cropFilter) && (!organicOnly || event.isOrganic)),
    [events, cropFilter, organicOnly],
  );
  const displayed = useMemo(() => {
    if (view !== "month") return filtered;
    return selectedDate
      ? filtered.filter((event) => event.scheduledDate === selectedDate)
      : [];
  }, [view, filtered, selectedDate]);

  const onToggle = (event: CalendarEvent) => {
    if (mutationLock.current || update.isPending || generate.isPending) return;
    mutationLock.current = true;
    update.mutate({
      id: event.id,
      patch: { status: event.status === "done" ? "pending" : "done" },
    }, { onSettled: () => { mutationLock.current = false; } });
  };

  const canGenerate = Boolean(farm?.sowingDate);
  const stageDataUnavailable =
    generate.error instanceof CalendarError &&
    generate.error.code === "STAGE_DATA_UNAVAILABLE";
  const onGenerate = () => {
    if (!farm || !farmId || farmQuery.isError || farmQuery.isFetching || generate.isPending || update.isPending || mutationLock.current) return;
    if (!farm.sowingDate) {
      router.push(`/farm/${farmId}/edit`);
      return;
    }
    mutationLock.current = true;
    generate.mutate({
      farmId,
      crop: farm.crop,
      sowingDate: farm.sowingDate,
      irrigationType: farm.irrigationType,
    }, { onSettled: () => { mutationLock.current = false; } });
  };

  const refreshAll = async () => {
    if (refreshLock.current || isRefetching || generate.isPending || update.isPending) return;
    refreshLock.current = true;
    setRefreshing(true);
    try {
      await Promise.all([refetchFarms(), ...(farmId ? [farmQuery.refetch(), refetch(), refetchSummary()] : [])]);
    } finally { refreshLock.current = false; setRefreshing(false); }
  };

  // Reached from Home's "Crop Calendar" quick action -- this shared header is
  // rendered on every branch (loading, error, no-farms, main) and had no back
  // affordance at all on any of them (2026-08 pre-release UI pass).
  const backButton = (
    <TouchableOpacity
      onPress={() => router.back()}
      accessibilityRole="button"
      accessibilityLabel={t("common.back")}
      hitSlop={8}
      activeOpacity={0.7}
      style={styles.iconButton}
    >
      <ArrowLeft size={25} color={CALENDAR_COLORS.ink} />
    </TouchableOpacity>
  );

  const header = (
    <View style={styles.headerBlock}>
      <View style={styles.brandBar}>
        {backButton}
        <View style={styles.brand} accessibilityLabel="AgrowAI">
          <Sprout size={28} color={CALENDAR_COLORS.primary} />
          <AgText variant="headingS" weight="bold" style={styles.brandText}>
            AgrowAI
          </AgText>
        </View>
        {events.length > 0 ? (
          <TouchableOpacity
            testID="calendar-refresh"
            onPress={onGenerate}
            disabled={generate.isPending || update.isPending || farmQuery.isFetching || farmQuery.isError || !canGenerate}
            accessibilityRole="button"
            accessibilityLabel={t("calendar.regenerate")}
            accessibilityState={{
              disabled: generate.isPending || !canGenerate,
              busy: generate.isPending,
            }}
            activeOpacity={0.72}
            style={[
              styles.refreshButton,
              {
                backgroundColor: CALENDAR_COLORS.card,
                borderColor: CALENDAR_COLORS.border,
                opacity:
                  generate.isPending || !canGenerate ? 0.5 : 1,
              },
            ]}
          >
            {generate.isPending ? (
              <ActivityIndicator size="small" color={CALENDAR_COLORS.primary} />
            ) : (
              <RefreshCw size={22} color={CALENDAR_COLORS.ink} />
            )}
          </TouchableOpacity>
        ) : (
          <View style={styles.iconButtonSpacer} />
        )}
      </View>
      <AgText variant="headingL" weight="bold" style={styles.title}>
        {t("calendar.title")}
      </AgText>
      <AgText variant="body" style={styles.subtitle}>
        {t("calendar.subtitle")}
      </AgText>
    </View>
  );

  if (farmsLoading) {
    return (
      <AgScreen backgroundColor={CALENDAR_COLORS.background}>
        {header}
        <CalendarSkeleton />
      </AgScreen>
    );
  }
  if (farmsError) {
    return (
      <AgScreen backgroundColor={CALENDAR_COLORS.background}>
        {header}
        <AgErrorState light onRetry={() => void refreshAll()} />
      </AgScreen>
    );
  }
  if (!farms.length) {
    return (
      <AgScreen backgroundColor={CALENDAR_COLORS.background}>
        {header}
        <AgEmptyState
          light
          icon={Sprout}
          title={t("calendar.noFarmsTitle")}
          message={t("calendar.noFarmsMessage")}
          actionLabel={t("farm.addFarm")}
          onAction={() => router.push("/farm/new")}
        />
      </AgScreen>
    );
  }

  const farmContext = [selected?.name, farm?.crop ?? selected?.crop]
    .filter(Boolean)
    .join(" • ");

  return (
    <AgScreen padded={false} backgroundColor={CALENDAR_COLORS.background}>
      <FlatList
        data={isError ? [] : displayed}
        keyExtractor={(item) => item.id}
        style={styles.list}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing || isRefetching}
            onRefresh={refreshAll}
            tintColor={colors.primary}
          />
        }
        ListHeaderComponent={
          <View style={styles.headerContent}>
            {header}
            <FarmSwitcher
              farms={farms}
              selectedId={selected?.id ?? null}
              onSelect={(id) => {
                if (generate.isPending || update.isPending) return;
                generate.reset();
                update.reset();
                select(id);
                setSelectedDate(null);
                setCropFilter(null);
              }}
            />
            {farmContext ? (
              <View
                style={[
                  styles.contextPill,
                  {
                    backgroundColor: CALENDAR_COLORS.card,
                    borderColor: CALENDAR_COLORS.border,
                  },
                ]}
              >
                <Sprout size={20} color={CALENDAR_COLORS.primary} />
                <AgText
                  variant="bodySmall"
                  weight="medium"
                  numberOfLines={2}
                  style={[styles.contextText, styles.bodyText]}
                >
                  {farmContext}
                </AgText>
              </View>
            ) : null}
            {farm?.sowingDate ? (
              <View style={styles.sowingRow}>
                <CalendarDays size={18} color={CALENDAR_COLORS.ink} />
                <AgText variant="bodySmall" style={styles.bodyText}>
                  {[
                    t("calendar.sownOn", {
                      date: dayjs(farm.sowingDate).format("DD MMM"),
                    }),
                    summary?.season
                      ? t(
                          `calendar.season${summary.season[0].toUpperCase()}${summary.season.slice(1)}`,
                        )
                      : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </AgText>
              </View>
            ) : null}
            {cachedAt ? (
              <View
                style={[
                  styles.contextPill,
                  {
                    backgroundColor: CALENDAR_COLORS.card,
                    borderColor: "#D59B26",
                  },
                ]}
              >
                <AgText variant="bodySmall" style={styles.bodyText}>
                  {t("calendar.cachedNotice", { time: cachedAt })}
                </AgText>
              </View>
            ) : null}
            {farmQuery.isLoading || summaryQuery.isLoading ? <CalendarSkeleton /> : null}
            {farmQuery.isError || summaryQuery.isError ? <AgErrorState light onRetry={refreshAll} /> : null}
            {generate.isError || update.isError ? <AgText color="danger" accessibilityRole="alert">
              {t(stageDataUnavailable ? "calendar.stageDataUnavailable" : "errors.generic")}
            </AgText> : null}
            {summary && !summaryQuery.isError && summary.total > 0 ? (
              <CalendarProgress summary={summary} />
            ) : null}
            <ViewTabs
              active={view}
              onChange={(nextView) => {
                setView(nextView);
                setSelectedDate(null);
              }}
            />
            <CropFilter
              crops={crops}
              selected={cropFilter}
              onSelect={setCropFilter}
            />
            <TouchableOpacity onPress={() => setOrganicOnly((value) => !value)} accessibilityRole="checkbox" accessibilityState={{ checked: organicOnly }} style={[styles.contextPill, { backgroundColor: organicOnly ? CALENDAR_COLORS.pale : CALENDAR_COLORS.card, borderColor: CALENDAR_COLORS.border }]}>
              <Sprout size={18} color={CALENDAR_COLORS.primary} />
              <AgText variant="bodySmall" weight="medium" style={styles.bodyText}>{t("organic.calendarOnly")}</AgText>
            </TouchableOpacity>
            {view === "month" ? (
              <MonthView
                events={filtered}
                selectedDate={selectedDate}
                onSelectDate={setSelectedDate}
              />
            ) : null}
            <View style={styles.sectionHeading}>
              <View style={styles.sectionTitle}>
                <CalendarDays size={21} color={CALENDAR_COLORS.primary} />
                <AgText
                  variant="headingS"
                  weight="semibold"
                  style={styles.title}
                >
                  {t("calendar.activitiesHeading", {
                    view: t(VIEW_LABEL_KEY[view]),
                  })}
                </AgText>
              </View>
              <View style={styles.countBadge}>
                <AgText variant="caption" style={styles.bodyText}>
                  {t("calendar.activityCount", { count: displayed.length })}
                </AgText>
              </View>
            </View>
          </View>
        }
        ItemSeparatorComponent={() => <View style={styles.itemSeparator} />}
        renderItem={({ item }) => (
          <TaskCard event={item} onToggle={onToggle} busy={update.isPending} />
        )}
        ListEmptyComponent={
          <View style={styles.emptyWrap}>
            {isLoading ? (
              <CalendarSkeleton />
            ) : isError ? (
              <AgErrorState light onRetry={refreshAll} />
            ) : farmQuery.isLoading || summaryQuery.isLoading ? (
              <CalendarSkeleton />
            ) : farmQuery.isError || summaryQuery.isError ? (
              <AgErrorState light onRetry={refreshAll} />
            ) : events.length === 0 && summary?.total === 0 ? (
              <AgEmptyState
                light
                icon={CalendarDays}
                title={
                  stageDataUnavailable
                    ? t("calendar.stageDataUnavailable")
                    : t("calendar.emptyTitle")
                }
                message={
                  stageDataUnavailable
                    ? t("calendar.manualTasksAvailable")
                    : canGenerate
                      ? t("calendar.emptyMessage")
                      : t("calendar.emptyNoSowing")
                }
                actionLabel={
                  stageDataUnavailable
                    ? undefined
                    : canGenerate
                      ? t("calendar.generate")
                      : t("calendar.setSowingDate")
                }
                onAction={stageDataUnavailable ? undefined : onGenerate}
              />
            ) : (
              <AgEmptyState
                light
                icon={CalendarDays}
                title={t("calendar.viewEmptyTitle")}
                message={
                  view === "month" && !selectedDate
                    ? t("calendar.monthHint")
                    : t("calendar.viewEmptyMessage")
                }
              />
            )}
          </View>
        }
        ListFooterComponent={
          events.length > 0 ? (
            <View
              style={[
                styles.tipCard,
                {
                  backgroundColor: CALENDAR_COLORS.pale,
                  borderColor: "#DDE6D7",
                },
              ]}
            >
              <View style={[styles.tipIcon, { backgroundColor: "#F8FBF4" }]}>
                <Lightbulb size={22} color={CALENDAR_COLORS.primary} />
              </View>
              <View style={styles.tipCopy}>
                <AgText variant="body" weight="semibold" style={styles.title}>
                  {t("calendar.tipTitle")}
                </AgText>
                <AgText variant="bodySmall" style={styles.bodyText}>
                  {t("calendar.tipMessage")}
                </AgText>
              </View>
            </View>
          ) : null
        }
      />
      {generate.isPending ? (
        <View style={styles.generatingOverlay}>
          <AgButton title={t("calendar.generating")} loading disabled />
        </View>
      ) : null}
    </AgScreen>
  );
}

function CalendarSkeleton() {
  const { colors } = useAppTheme();
  return (
    <View style={styles.skeleton}>
      <View style={[styles.skeletonHero, { backgroundColor: colors.border }]} />
      {[0, 1, 2].map((index) => (
        <View
          key={index}
          style={[styles.skeletonRow, { backgroundColor: colors.border }]}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  list: { flex: 1 },
  listContent: { paddingHorizontal: 20, paddingBottom: 44 },
  headerBlock: { gap: 3, paddingTop: 8 },
  brandBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  brand: { flexDirection: "row", alignItems: "center", gap: 7 },
  brandText: { color: CALENDAR_COLORS.primary },
  iconButton: {
    width: 48,
    height: 48,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: CALENDAR_COLORS.border,
    backgroundColor: CALENDAR_COLORS.card,
  },
  iconButtonSpacer: { width: 48, height: 48 },
  title: { color: CALENDAR_COLORS.ink },
  subtitle: { color: CALENDAR_COLORS.body },
  bodyText: { color: CALENDAR_COLORS.body },
  headerContent: { gap: 16, paddingBottom: 14 },
  refreshButton: {
    width: 48,
    height: 48,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  contextPill: {
    minHeight: 48,
    width: "100%",
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 9,
  },
  contextText: { flexShrink: 1 },
  sowingRow: {
    minHeight: 28,
    flexDirection: "row",
    alignItems: "center",
    gap: 9,
    paddingHorizontal: 8,
  },
  sectionHeading: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    marginTop: 2,
  },
  sectionTitle: { flex: 1, flexDirection: "row", alignItems: "center", gap: 9 },
  countBadge: {
    borderRadius: 14,
    backgroundColor: CALENDAR_COLORS.pale,
    paddingHorizontal: 12,
    paddingVertical: 5,
  },
  itemSeparator: { height: 12 },
  emptyWrap: { minHeight: 260, justifyContent: "center" },
  tipCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderWidth: 1,
    borderRadius: 20,
    padding: 16,
    marginTop: 18,
  },
  tipIcon: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
  },
  tipCopy: { flex: 1, gap: 2 },
  generatingOverlay: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 24,
    alignItems: "center",
  },
  skeleton: { gap: 12, marginTop: 10 },
  skeletonHero: { width: "100%", height: 176, borderRadius: 22 },
  skeletonRow: { width: "100%", height: 108, borderRadius: 20 },
});
