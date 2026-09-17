/**
 * Expert Connect — a structured farmer↔verified-expert consultation platform
 * (NOT a public chat room). Client-side camelCase mirror of the backend schemas.
 * Future-ready for live chat / video / AI-assisted replies.
 */

export type ExpertType =
  | 'tnau'
  | 'kvk'
  | 'govt_officer'
  | 'kisan_call_centre'
  | 'agronomist'
  | 'private';

export type ConsultationCategory =
  | 'crop_disease'
  | 'pest_control'
  | 'soil_health'
  | 'irrigation'
  | 'fertilizer'
  | 'weather'
  | 'market'
  | 'scheme'
  | 'seed'
  | 'organic'
  | 'general';

export type ConsultationPriority = 'low' | 'medium' | 'high' | 'urgent';

export type ConsultationStatus =
  | 'submitted'
  | 'assigned'
  | 'in_progress'
  | 'awaiting_farmer'
  | 'awaiting_expert'
  | 'resolved'
  | 'closed'
  | 'cancelled';

export type SenderType = 'farmer' | 'expert' | 'system';

export type AttachmentKind = 'image' | 'voice' | 'document';

export type ConsultationView = 'all' | 'pending' | 'history';

export type SyncStatus = 'synced' | 'pending';

export interface ExpertSpecialization {
  category: ConsultationCategory | string;
  crop: string | null;
}

export interface ExpertAvailability {
  dayOfWeek: number | null;
  startTime: string | null;
  endTime: string | null;
  timezone: string;
  isAvailable: boolean;
}

export interface Expert {
  id: string;
  fullName: string;
  expertType: ExpertType | string;
  organization: string | null;
  title: string | null;
  photoUrl: string | null;
  districts: string[];
  languages: string[];
  yearsExperience: number | null;
  rating: number | null;
  ratingCount: number;
  verified: boolean;
  categories: string[];
}

export interface ExpertDetail extends Expert {
  bio: string | null;
  source: string | null;
  contact: string | null;
  specializations: ExpertSpecialization[];
  availability: ExpertAvailability[];
}

export interface ConsultationAttachment {
  id: string;
  messageId: string | null;
  kind: AttachmentKind | string;
  fileUrl: string;
  thumbnailUrl: string | null;
  mimeType: string | null;
  caption: string | null;
  createdAt: string;
}

export interface ConsultationMessage {
  id: string;
  senderType: SenderType;
  senderExpertId: string | null;
  body: string;
  language: string;
  isSystem: boolean;
  createdAt: string;
  attachments: ConsultationAttachment[];
}

export interface StatusHistory {
  oldStatus: string | null;
  newStatus: string;
  changedByType: string;
  note: string | null;
  createdAt: string;
}

export interface Consultation {
  id: string;
  farmId: string | null;
  category: ConsultationCategory | string;
  crop: string | null;
  subject: string;
  priority: ConsultationPriority;
  status: ConsultationStatus;
  channel: string;
  assignedExpertId: string | null;
  expert: Expert | null;
  attachmentCount: number;
  messageCount: number;
  lastMessageAt: string | null;
  createdAt: string;
  updatedAt: string;
  syncStatus?: SyncStatus;
}

export interface ConsultationDetail extends Consultation {
  description: string;
  language: string;
  resolutionNote: string | null;
  assignedAt: string | null;
  resolvedAt: string | null;
  messages: ConsultationMessage[];
  attachments: ConsultationAttachment[];
  statusHistory: StatusHistory[];
}

export interface AttachmentInput {
  fileUrl: string;
  thumbnailUrl?: string | null;
  mimeType?: string | null;
  fileSize?: number | null;
  caption?: string | null;
  kind?: AttachmentKind;
}

export interface ConsultationInput {
  farmId?: string | null;
  category: ConsultationCategory;
  crop?: string | null;
  subject: string;
  description: string;
  priority?: ConsultationPriority;
  language?: string | null;
  preferredExpertId?: string | null;
  attachments?: AttachmentInput[];
}

export interface ReplyInput {
  body: string;
  attachments?: AttachmentInput[];
}

export interface ExpertListParams {
  category?: ConsultationCategory | null;
  crop?: string | null;
  district?: string | null;
  language?: string | null;
  expertType?: ExpertType | null;
  search?: string | null;
  page?: number;
  pageSize?: number;
}

export interface ConsultationListParams {
  status?: ConsultationStatus | null;
  category?: ConsultationCategory | null;
  page?: number;
  pageSize?: number;
}

export interface Paginated<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

// --------------------------------------------------------------------------- //
// Backend envelope shapes (snake_case).
// --------------------------------------------------------------------------- //
export interface ApiExpertSpecialization {
  category: string;
  crop: string | null;
}

export interface ApiExpertAvailability {
  day_of_week: number | null;
  start_time: string | null;
  end_time: string | null;
  timezone: string;
  is_available: boolean;
}

export interface ApiExpertSummary {
  id: string;
  full_name: string;
  expert_type: string;
  organization: string | null;
  title: string | null;
  photo_url: string | null;
  districts: string[];
  languages: string[];
  years_experience: number | null;
  rating: number | null;
  rating_count: number;
  verified: boolean;
  categories: string[];
}

export interface ApiExpertDetail extends ApiExpertSummary {
  bio: string | null;
  source: string | null;
  contact: string | null;
  specializations: ApiExpertSpecialization[];
  availability: ApiExpertAvailability[];
}

export interface ApiConsultationAttachment {
  id: string;
  message_id: string | null;
  kind: string;
  file_url: string;
  thumbnail_url: string | null;
  mime_type: string | null;
  caption: string | null;
  created_at: string;
}

export interface ApiConsultationMessage {
  id: string;
  sender_type: SenderType;
  sender_expert_id: string | null;
  body: string;
  language: string;
  is_system: boolean;
  created_at: string;
  attachments: ApiConsultationAttachment[];
}

export interface ApiStatusHistory {
  old_status: string | null;
  new_status: string;
  changed_by_type: string;
  note: string | null;
  created_at: string;
}

export interface ApiConsultationSummary {
  id: string;
  farm_id: string | null;
  category: string;
  crop: string | null;
  subject: string;
  priority: ConsultationPriority;
  status: ConsultationStatus;
  channel: string;
  assigned_expert_id: string | null;
  expert: ApiExpertSummary | null;
  attachment_count: number;
  message_count: number;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApiConsultationDetail extends ApiConsultationSummary {
  description: string;
  language: string;
  resolution_note: string | null;
  assigned_at: string | null;
  resolved_at: string | null;
  messages: ApiConsultationMessage[];
  attachments: ApiConsultationAttachment[];
  status_history: ApiStatusHistory[];
}
