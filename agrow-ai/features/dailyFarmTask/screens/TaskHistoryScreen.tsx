// History view for completed / dismissed tasks. Read-only -- every history
// item already has a `final_response`, so re-opening a closed task to
// change history would undermine the audit trail this feature relies on
// for threshold tuning (see backend `daily_task_audit_log`).
import dayjs from "dayjs";
import { useTranslation } from "react-i18next";
import { ActivityIndicator, FlatList, StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { AgErrorState, AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";
import { useLanguage } from "@/hooks/useLanguage";

import { localizedTaskText } from "../copy";
import { RESPONSE_LABEL_KEY, TASK_ICON } from "../constants";
import { useTaskHistory } from "../hooks/useDailyTask";
import { EmptyState } from "../components/EmptyState";
import type { ResponseType, TaskHistoryItem } from "../types";

const RESPONSE_TONE: Record<ResponseType, "success" | "warning" | "muted" | "danger"> = {
  done: "success",
  problem_found: "warning",
  no_issue: "muted",
  need_help: "danger",
  not_relevant: "muted",
};

export function TaskHistoryScreen() {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const { isTamil } = useLanguage();
  const { data, isLoading, isError, fetchNextPage, hasNextPage, isFetchingNextPage, refetch } =
    useTaskHistory();

  const items: TaskHistoryItem[] = data?.pages.flatMap((page) => page.items) ?? [];
  const toneColor: Record<string, string> = {
    success: colors.primary,
    warning: colors.warning,
    muted: colors.textMuted,
    danger: colors.danger,
  };

  if (isLoading) {
    return (
      <SafeAreaView style={[styles.screen, { backgroundColor: colors.bg }]}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" />
        </View>
      </SafeAreaView>
    );
  }

  if (isError) {
    return (
      <SafeAreaView style={[styles.screen, { backgroundColor: colors.bg }]}>
        <View style={styles.centered}>
          <AgErrorState onRetry={refetch} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: colors.bg }]}>
      <FlatList
        contentContainerStyle={styles.content}
        data={items}
        keyExtractor={(item) => item.id}
        onEndReached={hasNextPage ? () => fetchNextPage() : undefined}
        onEndReachedThreshold={0.4}
        ListHeaderComponent={
          <AgText variant="headingS" weight="bold" style={{ color: colors.text, marginBottom: 16 }}>
            {t("dailyTask.historyTitle")}
          </AgText>
        }
        ListEmptyComponent={<EmptyState />}
        ListFooterComponent={isFetchingNextPage ? <ActivityIndicator style={styles.footerSpinner} /> : null}
        renderItem={({ item }) => {
          const Icon = TASK_ICON[item.task_type] ?? TASK_ICON.irrigation_inspection;
          const tone = item.final_response ? RESPONSE_TONE[item.final_response] : "muted";
          return (
            <View style={[styles.row, { borderBottomColor: colors.border }]}>
              <Icon size={22} color={colors.textMuted} />
              <View style={styles.rowCopy}>
                <AgText variant="body" weight="semibold" style={{ color: colors.text }}>
                  {localizedTaskText(item, isTamil, t)}
                </AgText>
                {item.field_label ? (
                  <AgText variant="bodySmall" style={{ color: colors.textMuted }}>
                    {item.field_label}
                  </AgText>
                ) : null}
                <AgText variant="caption" style={{ color: colors.textDisabled, marginTop: 2 }}>
                  {dayjs(item.created_at).format("DD MMM YYYY")}
                </AgText>
              </View>
              <View style={[styles.responsePill, { backgroundColor: `${toneColor[tone]}18` }]}>
                <AgText variant="caption" weight="semibold" style={{ color: toneColor[tone] }}>
                  {item.final_response ? t(RESPONSE_LABEL_KEY[item.final_response]) : t("dailyTask.noResponse")}
                </AgText>
              </View>
            </View>
          );
        }}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  centered: { flex: 1, alignItems: "center", justifyContent: "center" },
  content: { padding: 20, flexGrow: 1 },
  footerSpinner: { marginVertical: 16 },
  row: { flexDirection: "row", alignItems: "flex-start", gap: 12, paddingVertical: 14, borderBottomWidth: StyleSheet.hairlineWidth },
  rowCopy: { flex: 1, minWidth: 0 },
  responsePill: { borderRadius: 12, paddingHorizontal: 10, paddingVertical: 4, alignSelf: "flex-start" },
});
