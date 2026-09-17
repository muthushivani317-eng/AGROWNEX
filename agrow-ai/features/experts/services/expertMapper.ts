import type {
  ApiConsultationAttachment,
  ApiConsultationDetail,
  ApiConsultationMessage,
  ApiConsultationSummary,
  ApiExpertDetail,
  ApiExpertSummary,
  ApiStatusHistory,
  AttachmentInput,
  Consultation,
  ConsultationAttachment,
  ConsultationDetail,
  ConsultationInput,
  ConsultationMessage,
  Expert,
  ExpertDetail,
  Paginated,
  ReplyInput,
  StatusHistory,
} from '../types';

/** Pure API-envelope → domain conversions (snake_case → camelCase). */

export function apiToExpert(dto: ApiExpertSummary): Expert {
  return {
    id: dto.id,
    fullName: dto.full_name,
    expertType: dto.expert_type,
    organization: dto.organization,
    title: dto.title,
    photoUrl: dto.photo_url,
    districts: dto.districts ?? [],
    languages: dto.languages ?? [],
    yearsExperience: dto.years_experience,
    rating: dto.rating,
    ratingCount: dto.rating_count,
    verified: dto.verified,
    categories: dto.categories ?? [],
  };
}

export function apiToExpertDetail(dto: ApiExpertDetail): ExpertDetail {
  return {
    ...apiToExpert(dto),
    bio: dto.bio,
    source: dto.source,
    contact: dto.contact,
    specializations: (dto.specializations ?? []).map((s) => ({
      category: s.category,
      crop: s.crop,
    })),
    availability: (dto.availability ?? []).map((a) => ({
      dayOfWeek: a.day_of_week,
      startTime: a.start_time,
      endTime: a.end_time,
      timezone: a.timezone,
      isAvailable: a.is_available,
    })),
  };
}

export function apiToAttachment(dto: ApiConsultationAttachment): ConsultationAttachment {
  return {
    id: dto.id,
    messageId: dto.message_id,
    kind: dto.kind,
    fileUrl: dto.file_url,
    thumbnailUrl: dto.thumbnail_url,
    mimeType: dto.mime_type,
    caption: dto.caption,
    createdAt: dto.created_at,
  };
}

export function apiToMessage(dto: ApiConsultationMessage): ConsultationMessage {
  return {
    id: dto.id,
    senderType: dto.sender_type,
    senderExpertId: dto.sender_expert_id,
    body: dto.body,
    language: dto.language,
    isSystem: dto.is_system,
    createdAt: dto.created_at,
    attachments: (dto.attachments ?? []).map(apiToAttachment),
  };
}

export function apiToStatusHistory(dto: ApiStatusHistory): StatusHistory {
  return {
    oldStatus: dto.old_status,
    newStatus: dto.new_status,
    changedByType: dto.changed_by_type,
    note: dto.note,
    createdAt: dto.created_at,
  };
}

export function apiToConsultation(dto: ApiConsultationSummary): Consultation {
  return {
    id: dto.id,
    farmId: dto.farm_id,
    category: dto.category,
    crop: dto.crop,
    subject: dto.subject,
    priority: dto.priority,
    status: dto.status,
    channel: dto.channel,
    assignedExpertId: dto.assigned_expert_id,
    expert: dto.expert ? apiToExpert(dto.expert) : null,
    attachmentCount: dto.attachment_count,
    messageCount: dto.message_count,
    lastMessageAt: dto.last_message_at,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    syncStatus: 'synced',
  };
}

export function apiToConsultationDetail(dto: ApiConsultationDetail): ConsultationDetail {
  return {
    ...apiToConsultation(dto),
    description: dto.description,
    language: dto.language,
    resolutionNote: dto.resolution_note,
    assignedAt: dto.assigned_at,
    resolvedAt: dto.resolved_at,
    messages: (dto.messages ?? []).map(apiToMessage),
    attachments: (dto.attachments ?? []).map(apiToAttachment),
    statusHistory: (dto.status_history ?? []).map(apiToStatusHistory),
  };
}

interface ApiPage<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export function apiToExpertList(dto: ApiPage<ApiExpertSummary>): Paginated<Expert> {
  return mapPage(dto, apiToExpert);
}

export function apiToConsultationList(
  dto: ApiPage<ApiConsultationSummary>,
): Paginated<Consultation> {
  return mapPage(dto, apiToConsultation);
}

/** Generic snake_case paginated envelope → domain page. */
function mapPage<A, D>(
  dto: { items: A[]; page: number; page_size: number; total: number; total_pages: number },
  map: (a: A) => D,
): Paginated<D> {
  return {
    items: dto.items.map(map),
    page: dto.page,
    pageSize: dto.page_size,
    total: dto.total,
    totalPages: dto.total_pages,
  };
}

// --------------------------------------------------------------------------- //
// Domain input → backend request body (camelCase → snake_case).
// --------------------------------------------------------------------------- //
export function attachmentToApi(a: AttachmentInput): Record<string, unknown> {
  return {
    file_url: a.fileUrl,
    thumbnail_url: a.thumbnailUrl ?? null,
    mime_type: a.mimeType ?? null,
    file_size: a.fileSize ?? null,
    caption: a.caption ?? null,
    kind: a.kind ?? 'image',
  };
}

export function consultationInputToApi(input: ConsultationInput): Record<string, unknown> {
  return {
    farm_id: input.farmId ?? null,
    category: input.category,
    crop: input.crop ?? null,
    subject: input.subject,
    description: input.description,
    priority: input.priority ?? 'medium',
    language: input.language ?? null,
    preferred_expert_id: input.preferredExpertId ?? null,
    attachments: (input.attachments ?? []).map(attachmentToApi),
  };
}

export function replyInputToApi(input: ReplyInput): Record<string, unknown> {
  return {
    body: input.body,
    attachments: (input.attachments ?? []).map(attachmentToApi),
  };
}
