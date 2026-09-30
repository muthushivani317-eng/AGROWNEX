// Home-dashboard entry point for the Today's Farm Task feature (integration
// brief: "this IS the unified farmer notification surface, not an
// additional feature to discover"). Mounted as its own HomeScreen section,
// separate from the existing local/ephemeral `TodaysTasks` weather
// checklist (features/home/components/TodaysTasks.tsx) -- that widget is a
// simple client-side rule-based reminder list with no backend behind it, so
// it was left in place rather than merged, to avoid touching an already
// -tested, working part of the home screen for this integration. The two
// can be reconciled into a single "tasks" surface later if desired.
import { useRouter } from "expo-router";
import { ChevronRight, Volume2 } from "lucide-react-native";
import * as Speech from "expo-speech";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Pressable, StyleSheet, View } from "react-native";

import { AgCard, AgErrorState, AgSkeleton, AgText } from "@/components/ui";
import { useAppTheme } from "@/hooks/useAppTheme";
import { useLanguage } from "@/hooks/useLanguage";

import { TASK_ICON, URGENCY_LABEL_KEY } from "../constants";
import { localizedTaskReason, localizedTaskText, localizedTaskTitle } from "../copy";
import { useTodayTasks } from "../hooks/useDailyTask";
import type { TaskCard as TaskCardModel } from "../types";
import { TaskResponseSheet } from "./TaskResponseSheet";

function TaskRow({
  task,
  onPress,
  isLast,
}: {
  task: TaskCardModel;
  onPress: () => void;
  isLast: boolean;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const { isTamil } = useLanguage();
  const Icon = TASK_ICON[task.task_type] ?? TASK_ICON.irrigation_inspection;
  const isUrgent = task.urgency === "today" || task.urgency === "before_rain";
  const taskText = localizedTaskText(task, isTamil, t);

  const playAudio = () => {
    const script = [
      localizedTaskTitle(task, isTamil, t),
      taskText,
      localizedTaskReason(task, isTamil, t),
    ].join(". ");
    Speech.speak(script, { language: isTamil ? "ta-IN" : "en-IN" });
  };

  return (
    <Pressable
      onPress={onPress}
      style={[styles.row, !isLast && { borderBottomColor: colors.border, borderBottomWidth: StyleSheet.hairlineWidth }]}
      accessibilityRole="button"
      accessibilityLabel={`${localizedTaskTitle(task, isTamil, t)}. ${taskText}`}
    >
      <View style={[styles.iconTile, { backgroundColor: `${colors.primary}12` }]}>
        <Icon size={20} color={isUrgent ? colors.danger : colors.primary} />
      </View>
      <View style={styles.rowCopy}>
        <AgText variant="body" weight="semibold" style={[styles.taskText, { color: colors.text }]}>
          {taskText}
        </AgText>
        {task.field_label ? (
          <AgText variant="bodySmall" style={{ color: colors.textMuted }}>
            {task.field_label}
          </AgText>
        ) : null}
        <View style={[styles.urgencyPill, { backgroundColor: `${colors.warning}18` }]}>
          <AgText variant="caption" weight="semibold" style={{ color: colors.warning }}>
            {t(URGENCY_LABEL_KEY[task.urgency] ?? "dailyTask.urgencyToday")}
          </AgText>
        </View>
      </View>
      <Pressable
        onPress={(event) => {
          event.stopPropagation();
          playAudio();
        }}
        style={styles.audioButton}
        hitSlop={10}
        accessibilityRole="button"
        accessibilityLabel={t("dailyTask.playAudio")}
      >
        <Volume2 size={20} color={colors.primary} />
      </Pressable>
      <ChevronRight size={18} color={colors.textMuted} />
    </Pressable>
  );
}

export function DailyFarmTaskCard() {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const router = useRouter();
  const { data, isLoading, isError, refetch } = useTodayTasks();
  const [activeTask, setActiveTask] = useState<TaskCardModel | null>(null);

  const tasks = data?.tasks ?? [];
  const hasUrgent = tasks.some((task) => task.urgency === "today" || task.urgency === "before_rain");

  return (
    <View>
      <View style={styles.headingRow}>
        <AgText variant="bodyLarge" weight="bold" color="inherit" style={{ color: colors.text }}>
          {hasUrgent ? t("dailyTask.headerUrgent") : t("dailyTask.header")}
        </AgText>
        <Pressable onPress={() => router.push("/daily-task" as never)} accessibilityRole="button">
          <AgText variant="bodySmall" weight="semibold" color="inherit" style={{ color: colors.primary }}>
            {t("dailyTask.viewHistory")}
          </AgText>
        </Pressable>
      </View>

      {isLoading ? (
        <AgSkeleton style={styles.skeleton} />
      ) : isError ? (
        <AgErrorState onRetry={refetch} />
      ) : tasks.length === 0 ? (
        <AgCard variant="elevated" style={styles.emptyCard}>
          <AgText variant="body" center color="inherit" style={styles.emptyText}>
            {t("dailyTask.emptyState")}
          </AgText>
        </AgCard>
      ) : (
        <AgCard variant="elevated" style={styles.card}>
          {tasks.map((task, index) => (
            <TaskRow
              key={task.id}
              task={task}
              isLast={index === tasks.length - 1}
              onPress={() => setActiveTask(task)}
            />
          ))}
        </AgCard>
      )}

      {activeTask ? (
        <TaskResponseSheet
          visible={Boolean(activeTask)}
          task={activeTask}
          onClose={() => setActiveTask(null)}
          onResponded={() => setActiveTask(null)}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  headingRow: { marginBottom: 9, flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  skeleton: { width: "100%", height: 110, borderRadius: 17 },
  emptyCard: {
    paddingVertical: 22,
    paddingHorizontal: 20,
    borderRadius: 17,
    backgroundColor: '#FFFDF8',
    borderColor: '#DED9CA',
  },
  emptyText: {
    color: '#4F6057',
    backgroundColor: 'transparent',
    flexShrink: 1,
  },
  card: {
    paddingVertical: 4,
    paddingHorizontal: 13,
    borderRadius: 17,
    borderColor: '#DED9CA',
    backgroundColor: '#FFFDF8',
  },
  row: { flexDirection: "row", alignItems: "center", gap: 11, paddingVertical: 12 },
  iconTile: { width: 38, height: 38, borderRadius: 13, alignItems: "center", justifyContent: "center" },
  rowCopy: { flex: 1, minWidth: 0, gap: 3 },
  taskText: { flexShrink: 1, lineHeight: 22 },
  audioButton: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  urgencyPill: { alignSelf: "flex-start", borderRadius: 10, paddingHorizontal: 8, paddingVertical: 2, marginTop: 2 },
});
