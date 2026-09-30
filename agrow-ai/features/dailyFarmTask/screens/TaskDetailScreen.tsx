// Task detail screen. Reached from the home DailyFarmTaskCard, from
// TaskHistoryScreen, or (later) a push-notification deep link -- all
// resolve to this same route (`/daily-task/[taskId]`) so copy/behavior
// never forks per entry channel.
import { useLocalSearchParams, useRouter } from "expo-router";
import * as Speech from "expo-speech";
import { Info, Volume2 } from "lucide-react-native";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { AgButton, AgErrorState, AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";
import { useLanguage } from "@/hooks/useLanguage";

import { TASK_ICON, URGENCY_LABEL_KEY } from "../constants";
import { localizedTaskReason, localizedTaskText, localizedTaskTitle, localizedTaskWhy } from "../copy";
import { useSnoozeTask, useTask } from "../hooks/useDailyTask";
import { TaskResponseSheet } from "../components/TaskResponseSheet";
import type { TaskRespondResponse } from "../types";

export function TaskDetailScreen() {
  const { taskId } = useLocalSearchParams<{ taskId: string }>();
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const { isTamil } = useLanguage();
  const router = useRouter();
  const { data: task, isLoading, isError, refetch } = useTask(taskId);
  const snooze = useSnoozeTask(taskId ?? "");
  const [showWhy, setShowWhy] = useState(false);
  const [showResponseSheet, setShowResponseSheet] = useState(false);

  const playAudio = () => {
    if (!task) return;
    Speech.speak(`${localizedTaskTitle(task, isTamil, t)}. ${localizedTaskText(task, isTamil, t)}. ${localizedTaskReason(task, isTamil, t)}`, {
      language: isTamil ? "ta-IN" : "en-IN",
    });
  };

  const handleSnooze = async (until: "later_today" | "tomorrow_morning") => {
    await snooze.mutateAsync(until);
    router.back();
  };

  const handleResponded = (_result: TaskRespondResponse) => {
    void refetch();
  };

  if (isLoading || !task) {
    return (
      <SafeAreaView style={[styles.screen, { backgroundColor: colors.bg }]}>
        <View style={styles.centered}>
          {isError ? <AgErrorState onRetry={refetch} /> : <ActivityIndicator size="large" />}
        </View>
      </SafeAreaView>
    );
  }

  const Icon = TASK_ICON[task.task_type] ?? TASK_ICON.irrigation_inspection;
  const isUrgent = task.urgency === "today" || task.urgency === "before_rain";
  const isClosed = task.status !== "active" && task.status !== "snoozed";

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: colors.bg }]}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.headerRow}>
          <AgText
            variant="body"
            weight="bold"
            style={{ color: isUrgent ? colors.danger : colors.primary }}
          >
            {isUrgent ? t("dailyTask.headerUrgent") : t("dailyTask.header")}
          </AgText>
          <Pressable onPress={playAudio} hitSlop={12} accessibilityLabel={t("dailyTask.playAudio")}>
            <Volume2 size={26} color={isUrgent ? colors.danger : colors.primary} />
          </Pressable>
        </View>

        <Icon size={44} color={isUrgent ? colors.danger : colors.primary} style={styles.icon} />

        {task.field_label ? (
          <AgText variant="body" style={{ color: colors.textMuted, marginBottom: 4 }}>
            {task.field_label}
          </AgText>
        ) : null}
        <AgText variant="headingS" weight="bold" style={{ color: colors.text, marginBottom: 8 }}>
          {localizedTaskText(task, isTamil, t)}
        </AgText>
        <AgText variant="body" style={{ color: colors.text, marginBottom: 16 }}>
          {localizedTaskReason(task, isTamil, t)}
        </AgText>

        <View style={[styles.urgencyPill, { backgroundColor: `${colors.warning}18` }]}>
          <AgText variant="body" weight="semibold" style={{ color: colors.warning }}>
            {t(URGENCY_LABEL_KEY[task.urgency] ?? "dailyTask.urgencyToday")}
          </AgText>
        </View>

        <Pressable onPress={() => setShowWhy((v) => !v)} style={styles.whyRow} accessibilityRole="button">
          <Info size={18} color={colors.textMuted} />
          <AgText variant="body" style={{ color: colors.textMuted, textDecorationLine: "underline" }}>
            {t("dailyTask.whyAmISeeingThis")}
          </AgText>
        </Pressable>
        {showWhy ? (
          <View style={[styles.whyBox, { backgroundColor: colors.card, borderColor: colors.border }]}>
            <AgText variant="body" style={{ color: colors.text }}>
              {localizedTaskWhy(task, isTamil, t)}
            </AgText>
          </View>
        ) : null}

        {!isClosed ? (
          <>
            <AgButton
              title={t("dailyTask.buttonDone")}
              onPress={() => setShowResponseSheet(true)}
              fullWidth
              size="lg"
            />
            <View style={styles.snoozeRow}>
              <Pressable onPress={() => handleSnooze("later_today")} disabled={snooze.isPending}>
                <AgText variant="body" style={{ color: colors.textMuted, textDecorationLine: "underline" }}>
                  {t("dailyTask.snoozeLaterToday")}
                </AgText>
              </Pressable>
              <Pressable onPress={() => handleSnooze("tomorrow_morning")} disabled={snooze.isPending}>
                <AgText variant="body" style={{ color: colors.textMuted, textDecorationLine: "underline" }}>
                  {t("dailyTask.snoozeTomorrowMorning")}
                </AgText>
              </Pressable>
            </View>
          </>
        ) : (
          <View style={[styles.closedBanner, { backgroundColor: `${colors.primary}12` }]}>
            <AgText variant="body" style={{ color: colors.primary }}>
              {t("dailyTask.responseRecorded")}
            </AgText>
          </View>
        )}
      </ScrollView>

      <TaskResponseSheet
        visible={showResponseSheet}
        task={task}
        onClose={() => setShowResponseSheet(false)}
        onResponded={handleResponded}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  centered: { flex: 1, alignItems: "center", justifyContent: "center" },
  content: { padding: 20 },
  headerRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 20 },
  icon: { marginBottom: 16 },
  urgencyPill: { alignSelf: "flex-start", borderRadius: 14, paddingHorizontal: 14, paddingVertical: 8, marginBottom: 20 },
  whyRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 16 },
  whyBox: { borderRadius: 14, borderWidth: 1, padding: 14, marginBottom: 20 },
  snoozeRow: { flexDirection: "row", justifyContent: "center", gap: 28, marginTop: 16 },
  closedBanner: { borderRadius: 14, padding: 16, alignItems: "center" },
});
