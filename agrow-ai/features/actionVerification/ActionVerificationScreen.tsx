import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import {
  ArrowLeft,
  ChevronRight,
  CircleCheckBig,
  ClipboardCheck,
  Clock3,
  History,
  RefreshCw,
  ShieldCheck,
  Sprout,
  WifiOff,
} from "lucide-react-native";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { ActivityIndicator, Pressable as AgPressable, RefreshControl, ScrollView, StyleSheet, View } from "react-native";

import {
  AgButton,
  AgCard,
  AgInput,
  AgOfflineBanner,
  AgScreen,
  AgText,
} from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";
import { queryClient } from "@/lib/queryClient";
import {
  getAction,
  getActionHistory,
  getActionConflicts,
  listActions,
  resolveActionConflict,
  respondToAction,
  syncActionOutbox,
} from "./api";
import {
  actionStatusLabelKey,
  submitErrorMessageKey,
  type ActionVerification,
} from "./types";

export function ActionVerificationScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { colors } = useAppTheme();
  const [selected, setSelected] = useState<ActionVerification | null>(null);
  const [note, setNote] = useState("");
  const [conflicts, setConflicts] = useState(getActionConflicts);
  const [syncError, setSyncError] = useState(false);
  const actions = useQuery({
    queryKey: ["action-verification"],
    queryFn: () => listActions(false),
    retry: false,
  });
  const detail = useQuery({
    queryKey: ["action-verification", "detail", selected?.id],
    queryFn: () => getAction(selected!.id),
    enabled: Boolean(selected?.id),
    retry: false,
  });
  const history = useQuery({
    queryKey: ["action-verification", "history", selected?.id],
    queryFn: () => getActionHistory(selected!.id),
    enabled: Boolean(selected?.id),
    retry: false,
  });
  const submit = useMutation({
    mutationFn: ({
      event,
    }: {
      event: "done" | "not_done" | "defer" | "skip" | "unable";
    }) =>
      respondToAction({
        actionId: selected!.id,
        event,
        expectedVersion: detail.data?.version ?? selected!.version,
        note: note || undefined,
        idempotencyKey: `action-${selected!.id}-${Date.now()}`,
      }),
    onSuccess: (value) => {
      setSelected(value);
      setNote("");
      queryClient.setQueryData(["action-verification", "detail", value.id], value);
      void queryClient.invalidateQueries({ queryKey: ["action-verification"] });
    },
  });

  useEffect(() => {
    void syncActionOutbox().then((count) => {
      setConflicts(getActionConflicts());
      if (count) void actions.refetch();
    }).catch(() => setSyncError(true));
  }, []);

  const resolution = useMutation({
    mutationFn: ({ id, choice }: { id: string; choice: "keep_server" | "apply_mine" }) => resolveActionConflict(id, choice),
    onSuccess: (value) => {
      setSelected(value);
      setNote("");
      setConflicts(getActionConflicts());
      void queryClient.invalidateQueries({ queryKey: ["action-verification"] });
    },
  });
  const refreshing = actions.isFetching || (Boolean(selected) && (detail.isFetching || history.isFetching));
  const refresh = () => {
    if (refreshing || submit.isPending || resolution.isPending) return;
    void actions.refetch();
    if (selected) { void detail.refetch(); void history.refetch(); }
  };
  const responseDisabled = submit.isPending || resolution.isPending || detail.isFetching || detail.isError || !detail.data;

  return (
    <AgScreen padded={false} backgroundColor={colors.bg}>
      <AgOfflineBanner />
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.primary} />}
      >
        <View style={styles.headerRow}>
          <AgPressable
            accessibilityRole="button"
            accessibilityLabel={t("common.back")}
            onPress={() => router.back()}
            hitSlop={8}
            style={[
              styles.iconButton,
              { backgroundColor: colors.card, borderColor: colors.border },
            ]}
          >
            <ArrowLeft size={25} color={colors.text} />
          </AgPressable>
          <View
            style={[
              styles.featureIcon,
              { backgroundColor: colors.primaryDark },
            ]}
          >
            <ClipboardCheck size={27} color="#FFFFFF" />
          </View>
          <View style={styles.flexOne}>
            <AgText variant="label" weight="semibold" color="primary">
              {t("actionVerification.eyebrow")}
            </AgText>
            <AgText variant="headingM" weight="bold">
              {t("actionVerification.title")}
            </AgText>
          </View>
        </View>

        <View
          style={[styles.scopeCard, { backgroundColor: colors.primaryDark }]}
        >
          <View style={styles.scopeTopRow}>
            <View
              style={[
                styles.scopeIcon,
                { backgroundColor: `${colors.primaryLight}24` },
              ]}
            >
              <ShieldCheck size={24} color={colors.primaryLight} />
            </View>
            <View style={styles.flexOne}>
              <AgText
                variant="headingS"
                weight="semibold"
                style={{ color: "#FFFFFF" }}
              >
                {t("actionVerification.scopeTitle")}
              </AgText>
              <AgText
                variant="bodySmall"
                style={{ color: "#E7F2E8", marginTop: 4 }}
              >
                {t("actionVerification.scope")}
              </AgText>
            </View>
          </View>
          <View style={styles.scopeMetaRow}>
            <Sprout size={18} color={colors.primaryLight} />
            <AgText variant="bodySmall" style={{ color: "#E7F2E8", flex: 1 }}>
              {t("actionVerification.scopeHint")}
            </AgText>
          </View>
        </View>

        <View style={styles.sectionHeader}>
          <View style={styles.flexOne}>
            <AgText variant="headingS" weight="semibold">
              {t("actionVerification.waitingTitle")}
            </AgText>
            <AgText variant="bodySmall" color="muted">
              {t("actionVerification.waitingHint")}
            </AgText>
          </View>
          {!actions.isLoading && !actions.isError ? (
            <View
              style={[
                styles.countPill,
                { backgroundColor: `${colors.primary}14` },
              ]}
            >
              <AgText variant="bodySmall" weight="semibold" color="primary">
                {t("actionVerification.actionCount", {
                  count: actions.data?.length ?? 0,
                })}
              </AgText>
            </View>
          ) : null}
        </View>

        {actions.isLoading ? (
          <StateCard
            colors={colors}
            icon={<ActivityIndicator size="large" color={colors.primary} />}
            title={t("actionVerification.loadingTitle")}
            body={t("actionVerification.loadingHint")}
          />
        ) : null}
        {actions.isError ? (
          <StateCard
            colors={colors}
            icon={<WifiOff size={34} color={colors.danger} />}
            title={t("actionVerification.loadErrorTitle")}
            body={t("actionVerification.loadErrorHint")}
          >
            <AgButton
              title={t("common.retry")}
              variant="outline"
              leftIcon={<RefreshCw size={19} color={colors.primary} />}
              disabled={refreshing}
              onPress={refresh}
            />
          </StateCard>
        ) : null}
        {!actions.isLoading && !actions.isError && !actions.data?.length ? (
          <StateCard
            colors={colors}
            icon={<CircleCheckBig size={38} color={colors.primary} />}
            title={t("actionVerification.emptyTitle")}
            body={t("actionVerification.emptyHint")}
          >
            <View
              style={[
                styles.infoStrip,
                { backgroundColor: `${colors.primary}0D` },
              ]}
            >
              <Clock3 size={20} color={colors.primary} />
              <AgText variant="bodySmall" color="muted" style={styles.flexOne}>
                {t("actionVerification.empty")}
              </AgText>
            </View>
          </StateCard>
        ) : null}

        {actions.data?.map((action) => (
          <AgPressable
            key={action.id}
            accessibilityRole="button"
            accessibilityLabel={`${action.actionCode}. ${t(actionStatusLabelKey(action.status))}`}
            disabled={submit.isPending || resolution.isPending}
            onPress={() => { setSelected(action); setNote(""); submit.reset(); }}
            style={[
              styles.actionCard,
              { backgroundColor: colors.card, borderColor: colors.border },
            ]}
          >
            <View
              style={[
                styles.actionIcon,
                { backgroundColor: `${colors.primary}12` },
              ]}
            >
              <ClipboardCheck size={24} color={colors.primary} />
            </View>
            <View style={styles.flexOne}>
              <AgText weight="semibold">{action.actionCode}</AgText>
              <AgText variant="bodySmall" color="muted">
                {t(actionStatusLabelKey(action.status))}
              </AgText>
              {action.pendingSync ? (
                <AgText variant="caption" color="primary">
                  {t("actionVerification.pendingSync")}
                </AgText>
              ) : null}
            </View>
            <View
              style={[
                styles.chevronButton,
                { backgroundColor: `${colors.primary}0D` },
              ]}
            >
              <ChevronRight size={21} color={colors.primary} />
            </View>
          </AgPressable>
        ))}

        {selected ? (
          <AgCard
            className="gap-3"
            style={{ borderColor: colors.border, borderWidth: 1 }}
          >
            <View style={styles.detailHeading}>
              <View
                style={[
                  styles.actionIcon,
                  { backgroundColor: `${colors.primary}12` },
                ]}
              >
                <ClipboardCheck size={23} color={colors.primary} />
              </View>
              <View style={styles.flexOne}>
                <AgText variant="headingS" weight="bold">
                  {t("actionVerification.detail")}
                </AgText>
                <AgText variant="bodySmall" color="muted">
                  {t(actionStatusLabelKey(detail.data?.status ?? selected.status))}
                </AgText>
              </View>
            </View>
            <AgText weight="semibold">
              {detail.data?.actionCode ?? selected.actionCode}
            </AgText>
            <View
              style={[
                styles.metadata,
                { backgroundColor: `${colors.primary}0A` },
              ]}
            >
              <AgText variant="bodySmall" color="muted">
                {t("actionVerification.source", {
                  source: detail.data?.sourceFeature ?? selected.sourceFeature,
                })}
              </AgText>
              <AgText variant="bodySmall" color="muted">
                {t("actionVerification.farmReference", {
                  farm: detail.data?.farmId ?? selected.farmId,
                })}
              </AgText>
            </View>
            {detail.isFetching ? <ActivityIndicator color={colors.primary} /> : null}
            {detail.isError ? <View accessibilityRole="alert">
              <AgText color="danger">{t("actionVerification.loadErrorHint")}</AgText>
              <AgButton title={t("common.retry")} disabled={detail.isFetching} onPress={() => void detail.refetch()} />
            </View> : null}
            <AgInput
              label={t("actionVerification.note")}
              value={note}
              onChangeText={setNote}
              multiline
            />
            <AgText variant="caption" color="muted">
              {t("actionVerification.evidenceUnavailable")}
            </AgText>
            <AgButton
              title={t("actionVerification.done")}
              loading={submit.isPending}
              disabled={responseDisabled}
              leftIcon={
                !submit.isPending ? (
                  <CircleCheckBig size={20} color={colors.onPrimary} />
                ) : undefined
              }
              onPress={() => { if (!responseDisabled) submit.mutate({ event: "done" }); }}
            />
            <View style={styles.secondaryActions}>
              <AgButton
                title={t("actionVerification.notDone")}
                variant="outline"
                disabled={responseDisabled}
                onPress={() => { if (!responseDisabled) submit.mutate({ event: "not_done" }); }}
              />
              <AgButton
                title={t("actionVerification.later")}
                variant="outline"
                disabled={responseDisabled}
                onPress={() => { if (!responseDisabled) submit.mutate({ event: "defer" }); }}
              />
            </View>
            <AgButton
              title={t("actionVerification.unable")}
              variant="ghost"
              disabled={responseDisabled}
              onPress={() => { if (!responseDisabled) submit.mutate({ event: "unable" }); }}
            />
            {submit.isError ? (
              <AgText color="danger">
                {t(submitErrorMessageKey(submit.error))}
              </AgText>
            ) : null}
          </AgCard>
        ) : null}

        {selected ? (
          <AgCard
            className="gap-3"
            style={{ borderColor: colors.border, borderWidth: 1 }}
          >
            <View style={styles.detailHeading}>
              <History size={23} color={colors.primary} />
              <AgText variant="headingS" weight="bold">
                {t("actionVerification.history")}
              </AgText>
            </View>
            {history.isFetching ? <ActivityIndicator color={colors.primary} /> : null}
            {history.isError ? <View accessibilityRole="alert">
              <AgText color="danger">{t("actionVerification.loadErrorHint")}</AgText>
              <AgButton title={t("common.retry")} disabled={history.isFetching} onPress={() => void history.refetch()} />
            </View> : null}
            {history.data?.map((event) => (
              <View
                key={event.id}
                style={[styles.historyRow, { borderColor: colors.border }]}
              >
                <View
                  style={[
                    styles.timelineDot,
                    { backgroundColor: colors.primary },
                  ]}
                />
                <AgText
                  variant="bodySmall"
                  color="muted"
                  style={styles.flexOne}
                >
                  {t(`actionVerification.status.${event.newStatus}`)}
                  {event.note ? ` — ${event.note}` : ""}
                </AgText>
              </View>
            ))}
          </AgCard>
        ) : null}

        {syncError || resolution.isError ? <AgText color="danger" accessibilityRole="alert">{t("actionVerification.loadErrorHint")}</AgText> : null}
        {conflicts.map((conflict) => (
          <AgCard
            key={conflict.input.actionId}
            className="gap-3"
            style={{ borderColor: colors.warning, borderWidth: 1 }}
          >
            <AgText variant="headingS" weight="bold">
              {t("actionVerification.conflictTitle")}
            </AgText>
            <AgText>{t("actionVerification.conflictMessage")}</AgText>
            <AgButton
              title={t("actionVerification.keepServer")}
              disabled={resolution.isPending || submit.isPending}
              onPress={() => resolution.mutate({ id: conflict.input.actionId, choice: "keep_server" })}
            />
            <AgButton
              title={t("actionVerification.applyMine")}
              variant="outline"
              disabled={resolution.isPending || submit.isPending}
              onPress={() => resolution.mutate({ id: conflict.input.actionId, choice: "apply_mine" })}
            />
          </AgCard>
        ))}
      </ScrollView>
    </AgScreen>
  );
}

function StateCard({
  colors,
  icon,
  title,
  body,
  children,
}: {
  colors: ReturnType<typeof useAppTheme>["colors"];
  icon: ReactNode;
  title: string;
  body: string;
  children?: ReactNode;
}) {
  return (
    <View
      style={[
        styles.stateCard,
        { backgroundColor: colors.card, borderColor: colors.border },
      ]}
    >
      <View
        style={[styles.stateIcon, { backgroundColor: `${colors.primary}14` }]}
      >
        {icon}
      </View>
      <AgText variant="headingM" weight="semibold" center>
        {title}
      </AgText>
      <AgText color="muted" center style={styles.stateBody}>
        {body}
      </AgText>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 56,
    gap: 20,
    flexGrow: 1,
  },
  headerRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  iconButton: {
    width: 48,
    height: 48,
    borderRadius: 16,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  featureIcon: {
    width: 48,
    height: 48,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
  },
  flexOne: { flex: 1 },
  scopeCard: { borderRadius: 24, padding: 20, gap: 16, overflow: "hidden" },
  scopeTopRow: { flexDirection: "row", gap: 14, alignItems: "flex-start" },
  scopeIcon: {
    width: 48,
    height: 48,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
  },
  scopeMetaRow: {
    flexDirection: "row",
    gap: 10,
    alignItems: "center",
    paddingTop: 14,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: "#FFFFFF42",
  },
  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 12,
  },
  countPill: {
    minHeight: 36,
    paddingHorizontal: 14,
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
  },
  stateCard: {
    borderWidth: 1,
    borderRadius: 28,
    paddingHorizontal: 24,
    paddingVertical: 36,
    alignItems: "center",
    gap: 14,
  },
  stateIcon: {
    width: 80,
    height: 80,
    borderRadius: 40,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 4,
  },
  stateBody: { maxWidth: 320 },
  infoStrip: {
    width: "100%",
    borderRadius: 16,
    padding: 14,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginTop: 8,
  },
  actionCard: {
    minHeight: 88,
    borderWidth: 1,
    borderRadius: 20,
    padding: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  actionIcon: {
    width: 48,
    height: 48,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
  },
  chevronButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
  },
  detailHeading: { flexDirection: "row", alignItems: "center", gap: 12 },
  metadata: { borderRadius: 14, padding: 14, gap: 4 },
  secondaryActions: { gap: 10 },
  historyRow: {
    minHeight: 44,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    paddingVertical: 8,
  },
  timelineDot: { width: 8, height: 8, borderRadius: 4 },
});
