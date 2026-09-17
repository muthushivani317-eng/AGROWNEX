import { buildProfile, isBackendConfigured } from "@/config/env";
import { mayUseLocalFeatureMocks } from "@/config/providerSafety";
import { logger } from "@/lib/logger";

import type {
  Consultation,
  ConsultationDetail,
  ConsultationInput,
  ConsultationListParams,
  ConsultationStatus,
  Expert,
  ExpertDetail,
  ExpertListParams,
  Paginated,
  ReplyInput,
  AttachmentInput,
} from "../types";

/**
 * Expert Connect data source contract. Backed by the AgrowAI expert/consultation
 * API + assignment engine when a backend is configured, otherwise a local offline
 * provider that runs a faithful client-side mirror over MMKV. Designed so future
 * channels (live chat, video, email, AI-assisted replies) can replace
 * the backend with no frontend change (docs: provider abstraction).
 */
export interface ExpertProvider {
  listExperts(params: ExpertListParams): Promise<Paginated<Expert>>;
  getExpert(id: string): Promise<ExpertDetail>;
  listConsultations(
    params: ConsultationListParams,
  ): Promise<Paginated<Consultation>>;
  pending(page?: number, pageSize?: number): Promise<Paginated<Consultation>>;
  history(page?: number, pageSize?: number): Promise<Paginated<Consultation>>;
  getConsultation(id: string): Promise<ConsultationDetail>;
  createConsultation(input: ConsultationInput): Promise<ConsultationDetail>;
  reply(id: string, input: ReplyInput): Promise<ConsultationDetail>;
  addAttachment(
    id: string,
    attachment: AttachmentInput,
  ): Promise<ConsultationDetail>;
  updateStatus(
    id: string,
    status: ConsultationStatus,
    note?: string,
  ): Promise<ConsultationDetail>;
}

export class ExpertError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "ExpertError";
  }
}

let provider: ExpertProvider | null = null;
const unavailable = async (): Promise<never> => {
  throw new ExpertError(
    "expert_network_unavailable",
    "experts.providerUnavailable",
  );
};
const unavailableExpertProvider: ExpertProvider = {
  listExperts: unavailable,
  getExpert: unavailable,
  listConsultations: unavailable,
  pending: unavailable,
  history: unavailable,
  getConsultation: unavailable,
  createConsultation: unavailable,
  reply: unavailable,
  addAttachment: unavailable,
  updateStatus: unavailable,
};

export function getExpertProvider(): ExpertProvider {
  if (provider) return provider;
  if (isBackendConfigured) {
    provider = require("./apiExpertProvider")
      .apiExpertProvider as ExpertProvider;
    logger.info("experts", "using api provider");
  } else if (mayUseLocalFeatureMocks(buildProfile, isBackendConfigured)) {
    provider = require("./localExpertProvider")
      .localExpertProvider as ExpertProvider;
    logger.info("experts", "using local provider");
  } else {
    provider = unavailableExpertProvider;
    logger.warn("experts", "backend unavailable; feature is fail-closed");
  }
  return provider;
}

/** Test seam: force a provider (used to reset between tests). */
export function _setExpertProvider(next: ExpertProvider | null): void {
  provider = next;
}
