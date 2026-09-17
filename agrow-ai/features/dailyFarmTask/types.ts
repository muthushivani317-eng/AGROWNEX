// Shared TypeScript types for the Today's Farm Task feature. Mirrors the
// backend Pydantic schemas in `app/modules/daily_task/schemas.py` field for
// field. Real backend MVP scope covers exactly these 5 task types -- broader
// Phase-2 types (postpone_irrigation, harvest_preparation,
// sudden_change_escalation, ...) were intentionally left out of both the
// backend and this mobile integration; see backend `constants.py`.
export type TaskType =
  | "irrigation_inspection"
  | "uneven_growth_inspection"
  | "drainage_inspection"
  | "sowing_germination_check"
  | "evidence_pack_trigger";

export type Urgency = "today" | "within_48h" | "before_rain" | "this_week";

export type TaskStatus =
  | "active"
  | "responded"
  | "snoozed"
  | "expired"
  | "suppressed";

export type ResponseType =
  | "done"
  | "problem_found"
  | "no_issue"
  | "need_help"
  | "not_relevant";

export interface TaskCard {
  id: string;
  task_type: TaskType;
  rank_position: 1 | 2;
  title_ta: string;
  task_text_ta: string;
  reason_text_ta: string;
  why_am_i_seeing_this_ta: string;
  field_label: string | null;
  urgency: Urgency;
  status: TaskStatus;
  valid_until: string; // ISO 8601
  created_at: string;
  can_upload_photo: boolean;
  can_record_voice_note: boolean;
  response_options: ResponseType[];
}

export interface TodayTasksResponse {
  tasks: TaskCard[]; // length 0, 1, or 2 -- server-enforced hard cap
  generated_at: string;
}

export interface TaskHistoryItem {
  id: string;
  task_type: TaskType;
  title_ta: string;
  task_text_ta: string;
  field_label: string | null;
  status: TaskStatus;
  created_at: string;
  final_response: ResponseType | null;
}

export interface TaskHistoryResponse {
  items: TaskHistoryItem[];
  next_cursor: string | null;
}

export interface TaskRespondRequest {
  response_type: ResponseType;
  note_text?: string | null;
}

export interface TaskRespondResponse {
  task_id: string;
  status: TaskStatus;
  follow_up_prompt: "photo_voice_optional" | "photo_voice_encouraged" | "none";
  escalated: boolean;
}

export type EvidencePackStatus = "pending_post_event_data" | "ready" | "shared";
export type EvidencePackConfidence = "high" | "medium" | "limited";
export type EvidencePackEventType =
  | "heavy_rain"
  | "cyclone"
  | "drought"
  | "farmer_reported";
export type EvidencePackShareTarget = "fpo" | "self_download" | "external";

export interface EvidencePackContent {
  farmer_name: string;
  farm_id: string;
  event_type: string;
  event_date_start: string;
  event_date_end: string | null;
  pre_event_scan_date: string | null;
  post_event_scan_date: string | null;
  pre_event_trend_summary_ta: string;
  post_event_trend_summary_ta: string;
  standing_water_note_ta: string | null;
  weather_context_ta: string;
  farmer_photo_object_ids: string[];
  farmer_voice_note_object_ids: string[];
  confidence_level: EvidencePackConfidence;
  disclaimer_ta: string;
  disclaimer_en: string;
}

export interface EvidencePack {
  id: string;
  farm_id: string;
  event_type: string;
  status: EvidencePackStatus;
  confidence_level: EvidencePackConfidence;
  has_pre_event_imagery: boolean;
  has_post_event_imagery: boolean;
  imagery_degraded_reason: string | null;
  content: EvidencePackContent;
  pdf_download_url: string | null;
  version: number;
  created_at: string;
}

export interface TriggerEvidencePackInput {
  fieldId: string;
  eventType: EvidencePackEventType;
  eventDateStart: string;
  farmerNote?: string;
}
