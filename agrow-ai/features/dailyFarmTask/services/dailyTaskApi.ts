// Thin API layer -- one function per backend endpoint, no business logic.
// Uses the app's shared `api` helper (services/apiClient.ts), which already
// unwraps the standard {success, data} envelope and attaches auth/language
// headers -- matching every other feature's service module (see
// features/calendar/services/apiCalendarProvider.ts). No offline-cache
// mirror here (unlike calendar's calendarStorage): daily tasks are generated
// fresh server-side once a day and are inherently a "what does the server
// say right now" surface, so there's nothing meaningful to serve offline.
import { api } from "@/services/apiClient";
import { endpoints } from "@/services/endpoints";

import type {
  EvidencePack,
  EvidencePackShareTarget,
  TaskCard,
  TaskHistoryResponse,
  TaskRespondRequest,
  TaskRespondResponse,
  TodayTasksResponse,
  TriggerEvidencePackInput,
} from "../types";

export async function fetchTodayTasks(): Promise<TodayTasksResponse> {
  return api.get<TodayTasksResponse>(endpoints.tasks.today);
}

export async function fetchTaskHistory(
  cursor?: string,
): Promise<TaskHistoryResponse> {
  return api.get<TaskHistoryResponse>(endpoints.tasks.history, {
    params: cursor ? { cursor } : undefined,
  });
}

export async function fetchTask(taskId: string): Promise<TaskCard> {
  return api.get<TaskCard>(endpoints.tasks.byId(taskId));
}

export async function respondToTask(
  taskId: string,
  body: TaskRespondRequest,
): Promise<TaskRespondResponse> {
  return api.post<TaskRespondResponse>(endpoints.tasks.respond(taskId), body);
}

export async function snoozeTask(
  taskId: string,
  snoozeUntil: "later_today" | "tomorrow_morning",
): Promise<void> {
  await api.post(endpoints.tasks.snooze(taskId), { snooze_until: snoozeUntil });
}

export async function uploadTaskPhoto(
  taskId: string,
  fileUri: string,
): Promise<{ photo_object_id: string }> {
  const form = new FormData();
  form.append("file", {
    uri: fileUri,
    name: "task-photo.jpg",
    type: "image/jpeg",
  } as unknown as Blob);
  return api.post(endpoints.tasks.photo(taskId), form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}

export async function uploadTaskVoiceNote(
  taskId: string,
  fileUri: string,
  durationSeconds: number,
): Promise<{ voice_note_object_id: string }> {
  const form = new FormData();
  form.append("file", {
    uri: fileUri,
    name: "voice-note.m4a",
    type: "audio/m4a",
  } as unknown as Blob);
  return api.post(endpoints.tasks.voiceNote(taskId), form, {
    params: { duration_seconds: durationSeconds },
    headers: { "Content-Type": "multipart/form-data" },
  });
}

export async function fetchEvidencePack(packId: string): Promise<EvidencePack> {
  return api.get<EvidencePack>(endpoints.evidencePacks.byId(packId));
}

export async function triggerEvidencePack(
  input: TriggerEvidencePackInput,
): Promise<EvidencePack> {
  return api.post<EvidencePack>(endpoints.evidencePacks.root, {
    field_id: input.fieldId,
    event_type: input.eventType,
    event_date_start: input.eventDateStart,
    farmer_note: input.farmerNote,
  });
}

export async function shareEvidencePack(
  packId: string,
  shareWith: EvidencePackShareTarget,
  fpoContactId?: string,
): Promise<void> {
  await api.post(endpoints.evidencePacks.share(packId), {
    share_with: shareWith,
    fpo_contact_id: fpoContactId,
  });
}
