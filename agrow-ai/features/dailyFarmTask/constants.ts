// Query keys + small lookup tables for the Today's Farm Task feature.
import { Droplets, FileText, Sprout, Waves, type LucideIcon } from "lucide-react-native";

import type { TaskType } from "./types";

export const dailyTaskKeys = {
  all: ["dailyTask"] as const,
  today: () => [...dailyTaskKeys.all, "today"] as const,
  history: () => [...dailyTaskKeys.all, "history"] as const,
  detail: (taskId: string) => [...dailyTaskKeys.all, "detail", taskId] as const,
  evidencePack: (packId: string) =>
    [...dailyTaskKeys.all, "evidencePack", packId] as const,
};

// Reuses the same icon family as features/home/components/TodaysTasks.tsx and
// features/calendar/components/TaskCard.tsx (lucide-react-native) so a task
// card looks consistent with the rest of the app, not like a bolted-on
// feature.
export const TASK_ICON: Record<TaskType, LucideIcon> = {
  irrigation_inspection: Droplets,
  uneven_growth_inspection: Sprout,
  drainage_inspection: Waves,
  sowing_germination_check: Sprout,
  evidence_pack_trigger: FileText,
};

export const URGENCY_LABEL_KEY: Record<string, string> = {
  today: "dailyTask.urgencyToday",
  within_48h: "dailyTask.urgencyWithin48h",
  before_rain: "dailyTask.urgencyBeforeRain",
  this_week: "dailyTask.urgencyThisWeek",
};

export const RESPONSE_LABEL_KEY: Record<string, string> = {
  done: "dailyTask.buttonDone",
  problem_found: "dailyTask.buttonProblemFound",
  no_issue: "dailyTask.buttonNoIssue",
  need_help: "dailyTask.buttonNeedHelp",
  not_relevant: "dailyTask.notRelevant",
};

export const MAX_VOICE_NOTE_SECONDS = 10;
