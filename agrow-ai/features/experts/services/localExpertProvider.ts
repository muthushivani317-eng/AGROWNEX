import { uuid } from '@/utils/id';

import { DEFAULT_PAGE_SIZE, HISTORY_STATUSES } from '../constants';
import type {
  AttachmentInput,
  Consultation,
  ConsultationDetail,
  ConsultationInput,
  ConsultationListParams,
  ConsultationMessage,
  ConsultationStatus,
  Expert,
  ExpertDetail,
  ExpertListParams,
  Paginated,
  ReplyInput,
  StatusHistory,
} from '../types';
import { assignExpert } from './assignment';
import { ExpertError, type ExpertProvider } from './expertProvider';
import { expertSeeds } from './expertSeeds';
import { expertStorage } from './expertStorage';

/**
 * Local, offline Expert Connect provider. Seeds the same verified desks and runs
 * the same deterministic assignment + consultation lifecycle as the backend over
 * MMKV, so the module is fully usable in dev / without a backend. The conversation
 * is immutable (messages only appended) and no expert opinion is ever fabricated
 * (docs/PRODUCT_RULES.md) — the only auto-message is a system acknowledgement.
 */
const FARMER_REPLY_STATUS: Partial<Record<ConsultationStatus, ConsultationStatus>> = {
  awaiting_farmer: 'awaiting_expert',
  assigned: 'awaiting_expert',
};
const CLOSED: ConsultationStatus[] = ['cancelled', 'closed'];
const FARMER_SETTABLE: ConsultationStatus[] = ['resolved', 'cancelled'];

function ensureSeeded(): void {
  if (!expertStorage.hasLocalExperts()) {
    expertStorage.seedLocalExperts(expertSeeds());
  }
}

function toSummaryExpert(e: ExpertDetail): Expert {
  const { bio, source, contact, specializations, availability, ...rest } = e;
  void bio;
  void source;
  void contact;
  void specializations;
  void availability;
  return rest;
}

function paginate<T>(items: T[], page: number, pageSize: number): Paginated<T> {
  const start = (page - 1) * pageSize;
  return {
    items: items.slice(start, start + pageSize),
    page,
    pageSize,
    total: items.length,
    totalPages: Math.max(1, Math.ceil(items.length / pageSize)),
  };
}

function toSummary(detail: ConsultationDetail): Consultation {
  const { description, messages, attachments, statusHistory, ...rest } = detail;
  void description;
  void messages;
  void attachments;
  void statusHistory;
  return rest;
}

function requireConsultation(id: string): ConsultationDetail {
  const found = expertStorage.getLocalConsultation(id);
  if (!found) throw new ExpertError('consultation_not_found', 'Consultation not found.');
  return found;
}

export const localExpertProvider: ExpertProvider = {
  async listExperts(params: ExpertListParams): Promise<Paginated<Expert>> {
    ensureSeeded();
    const rows = expertStorage
      .localExperts()
      .filter((e) => {
        if (params.category && !e.categories.includes(params.category)) return false;
        if (params.expertType && e.expertType !== params.expertType) return false;
        if (
          params.search &&
          !`${e.fullName} ${e.organization ?? ''}`
            .toLowerCase()
            .includes(params.search.toLowerCase())
        )
          return false;
        if (
          params.district &&
          e.districts.length > 0 &&
          !e.districts.map((d) => d.toLowerCase()).includes(params.district.toLowerCase())
        )
          return false;
        return true;
      })
      .map(toSummaryExpert)
      .sort((a, b) => a.fullName.localeCompare(b.fullName));
    return paginate(rows, params.page ?? 1, params.pageSize ?? DEFAULT_PAGE_SIZE);
  },

  async getExpert(id: string): Promise<ExpertDetail> {
    ensureSeeded();
    const expert = expertStorage.getLocalExpert(id);
    if (!expert) throw new ExpertError('expert_not_found', 'Expert not found.');
    return expert;
  },

  async listConsultations(
    params: ConsultationListParams,
  ): Promise<Paginated<Consultation>> {
    const rows = expertStorage
      .localConsultations()
      .filter((c) => {
        if (params.status && c.status !== params.status) return false;
        if (params.category && c.category !== params.category) return false;
        return true;
      })
      .map(toSummary);
    return paginate(rows, params.page ?? 1, params.pageSize ?? DEFAULT_PAGE_SIZE);
  },

  async pending(page = 1, pageSize = DEFAULT_PAGE_SIZE): Promise<Paginated<Consultation>> {
    const rows = expertStorage
      .localConsultations()
      .filter((c) => !HISTORY_STATUSES.includes(c.status))
      .map(toSummary);
    return paginate(rows, page, pageSize);
  },

  async history(page = 1, pageSize = DEFAULT_PAGE_SIZE): Promise<Paginated<Consultation>> {
    const rows = expertStorage
      .localConsultations()
      .filter((c) => HISTORY_STATUSES.includes(c.status))
      .map(toSummary);
    return paginate(rows, page, pageSize);
  },

  async getConsultation(id: string): Promise<ConsultationDetail> {
    return requireConsultation(id);
  },

  async createConsultation(input: ConsultationInput): Promise<ConsultationDetail> {
    ensureSeeded();
    const now = new Date().toISOString();
    const id = uuid();
    const language = input.language ?? 'ta';
    const experts = expertStorage.localExperts();
    const expert =
      (input.preferredExpertId
        ? experts.find((e) => e.id === input.preferredExpertId)
        : null) ??
      assignExpert(experts, {
        category: input.category,
        crop: input.crop,
        language,
      });

    const openingId = uuid();
    const messages: ConsultationMessage[] = [
      {
        id: openingId,
        senderType: 'farmer',
        senderExpertId: null,
        body: input.description,
        language,
        isSystem: false,
        createdAt: now,
        attachments: (input.attachments ?? []).map((a) => ({
          id: uuid(),
          messageId: openingId,
          kind: a.kind ?? 'image',
          fileUrl: a.fileUrl,
          thumbnailUrl: a.thumbnailUrl ?? null,
          mimeType: a.mimeType ?? null,
          caption: a.caption ?? null,
          createdAt: now,
        })),
      },
    ];
    const statusHistory: StatusHistory[] = [
      {
        oldStatus: null,
        newStatus: 'submitted',
        changedByType: 'farmer',
        note: 'Consultation created',
        createdAt: now,
      },
    ];

    if (expert) {
      messages.push({
        id: uuid(),
        senderType: 'system',
        senderExpertId: expert.id,
        body: `Your question has been received by ${expert.fullName}. A verified expert will review it and reply here.`,
        language,
        isSystem: true,
        createdAt: now,
        attachments: [],
      });
      statusHistory.push({
        oldStatus: 'submitted',
        newStatus: 'assigned',
        changedByType: 'system',
        note: `Assigned to ${expert.fullName}`,
        createdAt: now,
      });
    }

    const attachments = messages.flatMap((m) => m.attachments);
    const consultation: ConsultationDetail = {
      id,
      farmId: input.farmId ?? null,
      category: input.category,
      crop: input.crop ?? null,
      subject: input.subject,
      priority: input.priority ?? 'medium',
      status: expert ? 'assigned' : 'submitted',
      channel: 'in_app',
      assignedExpertId: expert?.id ?? null,
      expert: expert ? toSummaryExpert(expert) : null,
      attachmentCount: attachments.length,
      messageCount: messages.length,
      lastMessageAt: now,
      createdAt: now,
      updatedAt: now,
      syncStatus: 'synced',
      description: input.description,
      language,
      resolutionNote: null,
      assignedAt: expert ? now : null,
      resolvedAt: null,
      messages,
      attachments,
      statusHistory,
    };
    expertStorage.upsertLocalConsultation(consultation);
    return consultation;
  },

  async reply(id: string, input: ReplyInput): Promise<ConsultationDetail> {
    const existing = requireConsultation(id);
    if (CLOSED.includes(existing.status)) {
      throw new ExpertError('consultation_closed', 'This consultation is closed.');
    }
    const now = new Date().toISOString();
    const messageId = uuid();
    const message: ConsultationMessage = {
      id: messageId,
      senderType: 'farmer',
      senderExpertId: null,
      body: input.body,
      language: existing.language,
      isSystem: false,
      createdAt: now,
      attachments: (input.attachments ?? []).map((a) => ({
        id: uuid(),
        messageId,
        kind: a.kind ?? 'image',
        fileUrl: a.fileUrl,
        thumbnailUrl: a.thumbnailUrl ?? null,
        mimeType: a.mimeType ?? null,
        caption: a.caption ?? null,
        createdAt: now,
      })),
    };

    let status = existing.status;
    const statusHistory = [...existing.statusHistory];
    if (existing.status === 'resolved') {
      status = 'in_progress';
      statusHistory.push({
        oldStatus: 'resolved',
        newStatus: 'in_progress',
        changedByType: 'farmer',
        note: 'Reopened by farmer',
        createdAt: now,
      });
    } else {
      const mapped = FARMER_REPLY_STATUS[existing.status];
      if (mapped) {
        statusHistory.push({
          oldStatus: existing.status,
          newStatus: mapped,
          changedByType: 'farmer',
          note: null,
          createdAt: now,
        });
        status = mapped;
      }
    }

    const messages = [...existing.messages, message];
    const attachments = [...existing.attachments, ...message.attachments];
    const next: ConsultationDetail = {
      ...existing,
      status,
      messages,
      attachments,
      statusHistory,
      messageCount: messages.length,
      attachmentCount: attachments.length,
      lastMessageAt: now,
      updatedAt: now,
    };
    expertStorage.upsertLocalConsultation(next);
    return next;
  },

  async addAttachment(id: string, attachment: AttachmentInput): Promise<ConsultationDetail> {
    const existing = requireConsultation(id);
    if (CLOSED.includes(existing.status)) {
      throw new ExpertError('consultation_closed', 'This consultation is closed.');
    }
    const now = new Date().toISOString();
    const attachments = [
      ...existing.attachments,
      {
        id: uuid(),
        messageId: null,
        kind: attachment.kind ?? 'image',
        fileUrl: attachment.fileUrl,
        thumbnailUrl: attachment.thumbnailUrl ?? null,
        mimeType: attachment.mimeType ?? null,
        caption: attachment.caption ?? null,
        createdAt: now,
      },
    ];
    const next: ConsultationDetail = {
      ...existing,
      attachments,
      attachmentCount: attachments.length,
      updatedAt: now,
    };
    expertStorage.upsertLocalConsultation(next);
    return next;
  },

  async updateStatus(
    id: string,
    status: ConsultationStatus,
    note?: string,
  ): Promise<ConsultationDetail> {
    const existing = requireConsultation(id);
    if (status === existing.status) return existing;
    if (!FARMER_SETTABLE.includes(status)) {
      throw new ExpertError(
        'invalid_consultation_status',
        'A farmer can only resolve or cancel a consultation.',
      );
    }
    const now = new Date().toISOString();
    const next: ConsultationDetail = {
      ...existing,
      status,
      resolvedAt: status === 'resolved' ? now : existing.resolvedAt,
      resolutionNote: status === 'resolved' && note ? note : existing.resolutionNote,
      updatedAt: now,
      statusHistory: [
        ...existing.statusHistory,
        {
          oldStatus: existing.status,
          newStatus: status,
          changedByType: 'farmer',
          note: note ?? null,
          createdAt: now,
        },
      ],
    };
    expertStorage.upsertLocalConsultation(next);
    return next;
  },
};
