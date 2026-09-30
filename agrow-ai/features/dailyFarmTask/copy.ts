import type { TFunction } from "i18next";

import {
  TASK_REASON_LABEL_KEY,
  TASK_TEXT_LABEL_KEY,
  TASK_WHY_LABEL_KEY,
} from "./constants";
import type { TaskCard, TaskHistoryItem } from "./types";

type TaskTextSource = Pick<TaskCard | TaskHistoryItem, "task_type" | "task_text_ta">;
type TaskDetailSource = Pick<
  TaskCard,
  | "task_type"
  | "title_ta"
  | "task_text_ta"
  | "reason_text_ta"
  | "why_am_i_seeing_this_ta"
  | "urgency"
>;

export function localizedTaskText(
  task: TaskTextSource,
  isTamil: boolean,
  t: TFunction,
): string {
  return isTamil ? task.task_text_ta : t(TASK_TEXT_LABEL_KEY[task.task_type]);
}

export function localizedTaskReason(
  task: TaskDetailSource,
  isTamil: boolean,
  t: TFunction,
): string {
  return isTamil ? task.reason_text_ta : t(TASK_REASON_LABEL_KEY[task.task_type]);
}

export function localizedTaskWhy(
  task: TaskDetailSource,
  isTamil: boolean,
  t: TFunction,
): string {
  return isTamil
    ? task.why_am_i_seeing_this_ta
    : t(TASK_WHY_LABEL_KEY[task.task_type]);
}

export function localizedTaskTitle(
  task: TaskDetailSource,
  isTamil: boolean,
  t: TFunction,
): string {
  if (isTamil) return task.title_ta;
  const isUrgent = task.urgency === "today" || task.urgency === "before_rain";
  return t(isUrgent ? "dailyTask.headerUrgent" : "dailyTask.header");
}
